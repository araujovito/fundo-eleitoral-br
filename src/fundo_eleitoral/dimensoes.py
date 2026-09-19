"""Etapa 1b: deriva as dimensoes de votos e eleitorado a partir do TSE.

Existe porque `geografia.py` e `eficiencia.py` precisam de resultados e de
tamanho do eleitorado, que nao estao na prestacao de contas. Estes dois Parquet
chegaram ao projeto versionados no git, sem nenhum codigo que os produzisse:
nao davam para conferir nem para atualizar (ADR-011).

Os pacotes de origem sao grandes -- 595 MB de votacao em 2022, 408 MB de perfil
do eleitorado em 2026 -- e o que as analises consomem sao dezenas de KB. Por
isso a agregacao acontece aqui, na ingestao, e so o agregado e publicado.

Ao contrario da prestacao de contas, estes pacotes nao tem arquivo _BRASIL: ha
um CSV por UF e concatenar e o caminho correto.

Uso:
    python -m fundo_eleitoral.dimensoes --ano 2022
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

import duckdb

from .fontes import DIALETO_TSE, Fonte, fontes_auxiliares
from .ingestao import DIR_BRUTO, baixar

RAIZ = Path(__file__).resolve().parents[2]
DIR_DIMENSOES = RAIZ / "dados" / "dimensoes"

# all_varchar: o schema do TSE nao e estavel entre ciclos (ADR-004). A conversao
# de tipo acontece na agregacao, onde e explicita.
_LER = ("read_csv('{csv}', delim=';', header=true, quote='\"', "
        "all_varchar=true, ignore_errors=true)")


def _transcrever(origem, destino, bloco: int = 1 << 20) -> None:
    """latin-1 -> utf-8 em blocos; ver ADR-008."""
    while pedaco := origem.read(bloco):
        destino.write(pedaco.decode(DIALETO_TSE["encoding"]).encode("utf-8"))


def _colunas(leitor: str) -> set[str]:
    return {c[0].lower() for c in duckdb.sql(f"DESCRIBE SELECT * FROM {leitor}").fetchall()}


def _primeira_existente(colunas: set[str], candidatas: tuple[str, ...], onde: str) -> str:
    """Escolhe o nome de coluna que este ciclo usa.

    O TSE renomeia colunas entre ciclos sem aviso: o eleitorado e
    `qt_eleitores_perfil` em 2018 e `qt_eleitores` em 2022 e 2026. Presumir um
    nome so quebra a ingestao de um ano inteiro.
    """
    for nome in candidatas:
        if nome in colunas:
            return nome
    raise RuntimeError(f"{onde}: nenhuma de {candidatas} existe. Ha: {sorted(colunas)[:12]}")


def _agregar_por_uf(fonte: Fonte, prefixo: str, selecao, trabalho: Path) -> Path | None:
    """Roda `selecao` em cada CSV de UF e grava um Parquet parcial por arquivo.

    Devolve o diretorio das parciais, ou None se o pacote vier vazio -- que e o
    caso de `votacao_candidato_munzona_2026`: o arquivo existe, a eleicao ainda
    nao aconteceu.
    """
    zip_path = baixar(fonte, DIR_BRUTO)
    partes = trabalho / f"_partes_{fonte.chave}"
    partes.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path) as z:
            # Atencao ao _BRASIL: aqui ele e a UNIAO das UFs, e somado junto
            # duplica o total exatamente (312,9 mi de eleitores em vez de
            # 156,5 mi). Na prestacao de contas o arquivo de mesmo sufixo e um
            # SUPERCONJUNTO e usa-lo sozinho e o correto (ADR-006). Mesmo nome,
            # tratamento oposto. ZZ e o exterior: fica fora da comparacao
            # territorial, que e contra as 27 UFs.
            membros = sorted(n for n in z.namelist()
                             if Path(n).name.lower().startswith(prefixo.lower())
                             and n.lower().endswith(".csv")
                             and not Path(n).stem.upper().endswith(("_BRASIL", "_ZZ")))
            if not membros:
                print(f"  {fonte.chave}: pacote sem CSV -- nada a derivar")
                return None
            for i, nome in enumerate(membros, 1):
                tmp = partes / "_uf.csv"
                with z.open(nome) as origem, tmp.open("wb") as saida:
                    _transcrever(origem, saida)
                alvo = partes / f"parte_{i:02d}.parquet"
                leitor = _LER.format(csv=tmp)
                sql = (selecao(leitor, _colunas(leitor)) if callable(selecao)
                       else selecao.format(fonte=leitor))
                duckdb.sql(f"COPY ({sql}) TO '{alvo}' (FORMAT PARQUET)")
                tmp.unlink(missing_ok=True)
                print(f"\r  {fonte.chave}: {i}/{len(membros)} UFs", end="", flush=True)
        print()
        return partes
    except zipfile.BadZipFile:
        print(f"  {fonte.chave}: pacote vazio ou invalido -- nada a derivar")
        return None
    finally:
        zip_path.unlink(missing_ok=True)


def _consolidar(partes: Path, selecao_final: str, alvo: Path) -> Path:
    alvo.parent.mkdir(parents=True, exist_ok=True)
    duckdb.sql(f"COPY ({selecao_final.format(partes=partes / '*.parquet')}) "
               f"TO '{alvo}' (FORMAT PARQUET)")
    for p in partes.glob("*.parquet"):
        p.unlink()
    partes.rmdir()
    return alvo


def construir_votos(ano: int, destino: Path = DIR_DIMENSOES,
                    trabalho: Path = DIR_BRUTO) -> Path | None:
    """Votos nominais por candidatura e turno."""
    fonte = next(f for f in fontes_auxiliares(ano) if f.chave.startswith("votacao"))
    def selecao(leitor: str, colunas: set[str]) -> str:
        col = _primeira_existente(
            colunas, ("qt_votos_nominais", "qt_votos"), f"votacao_{ano}")
        return (f"SELECT sq_candidato, nr_turno, sum(CAST({col} AS BIGINT)) AS qt_votos "
                f"FROM {leitor} GROUP BY 1, 2")

    partes = _agregar_por_uf(fonte, f"votacao_candidato_munzona_{ano}", selecao, trabalho)
    if partes is None:
        return None
    return _consolidar(
        partes,
        f"SELECT {ano} AS ano, sq_candidato, CAST(nr_turno AS INTEGER) AS nr_turno, "
        "sum(qt_votos) AS qt_votos FROM '{partes}' GROUP BY 1, 2, 3",
        destino / f"votos_candidatos_{ano}.parquet",
    )


def construir_eleitorado(ano: int, destino: Path = DIR_DIMENSOES,
                         trabalho: Path = DIR_BRUTO) -> Path | None:
    """Eleitorado por UF.

    O perfil vem cruzado por municipio, zona, genero, faixa etaria e outras
    dimensoes: somar todas as celulas devolve o total da UF.
    """
    fonte = next(f for f in fontes_auxiliares(ano) if f.chave.startswith("eleitorado"))
    def selecao(leitor: str, colunas: set[str]) -> str:
        col = _primeira_existente(
            colunas, ("qt_eleitores", "qt_eleitores_perfil"), f"perfil_eleitorado_{ano}")
        # Em 2018 o pacote e um CSV unico, entao excluir ZZ por nome de
        # arquivo nao alcanca: o exterior precisa sair por linha tambem.
        return (f"SELECT sg_uf, sum(CAST({col} AS BIGINT)) AS qt_eleitores "
                f"FROM {leitor} WHERE sg_uf <> 'ZZ' GROUP BY 1")

    partes = _agregar_por_uf(fonte, f"perfil_eleitorado_{ano}", selecao, trabalho)
    if partes is None:
        return None
    return _consolidar(
        partes,
        f"SELECT {ano} AS ano, sg_uf, sum(qt_eleitores) AS qt_eleitores "
        "FROM '{partes}' WHERE sg_uf IS NOT NULL AND length(sg_uf) = 2 "
        "GROUP BY 1, 2 HAVING sum(qt_eleitores) > 0",
        destino / f"eleitorado_{ano}.parquet",
    )


def consolidar_ciclos(anos: tuple[int, ...], destino: Path = DIR_DIMENSOES) -> list[Path]:
    """Junta os Parquet por ciclo nos dois arquivos que as analises consomem."""
    alvos = []
    for base, coluna in (("eleitorado", "qt_eleitores"), ("votos_candidatos", "qt_votos")):
        partes = [destino / f"{base}_{ano}.parquet" for ano in anos]
        partes = [p for p in partes if p.exists()]
        if not partes:
            continue
        lista = ", ".join(f"'{p}'" for p in partes)
        alvo = destino / f"{base}.parquet"
        duckdb.sql(f"COPY (SELECT * FROM read_parquet([{lista}])) TO '{alvo}' (FORMAT PARQUET)")
        alvos.append(alvo)
        print(f"  {alvo.name}: {len(partes)} ciclos")
    return alvos


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Deriva as dimensoes auxiliares do TSE")
    p.add_argument("--ano", type=int, action="append", required=True)
    args = p.parse_args(argv)
    for ano in args.ano:
        print(f"[{ano}]")
        construir_eleitorado(ano)
        construir_votos(ano)
    consolidar_ciclos(tuple(args.ano))
    return 0


if __name__ == "__main__":
    sys.exit(main())
