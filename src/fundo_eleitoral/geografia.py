"""Compara a distribuicao territorial do FEFC ao tamanho do eleitorado.

Uso:
    python -m fundo_eleitoral.geografia --ano 2022
    python -m fundo_eleitoral.geografia --ano 2022 --por-partido
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import duckdb

from .consulta import DIMENSOES, HF, caminho, clausula_aptidao, cte_fefc

RAIZ = Path(__file__).resolve().parents[2]
# Derivada do TSE por dimensoes.py e publicada junto com o resto dos
# dados (ADR-011). Antes vinha versionada no git, sem codigo que a
# gerasse -- nao dava para conferir nem para atualizar.
DIMENSAO_ELEITORADO = f"{DIMENSOES}/eleitorado.parquet"
UFS_BRASIL = frozenset((
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT",
    "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
))


@dataclass(frozen=True)
class MetricasGeograficas:
    eleitorado: int
    pct_eleitorado: float
    total_fefc: float
    pct_fefc: float
    diferenca_pp: float
    indice_prioridade: float
    n_candidaturas: int
    n_financiadas: int
    # Cadeiras em disputa na UF para o cargo analisado, e o indice medido
    # contra elas em vez do eleitorado. None quando a analise mistura cargos:
    # cadeira de deputado federal e de governador nao se somam.
    cadeiras: int | None = None
    pct_cadeiras: float | None = None
    indice_por_cadeira: float | None = None


@dataclass(frozen=True)
class LinhaGeografica:
    ano: int
    partido: str | None
    uf: str
    metricas: MetricasGeograficas


def _eleitorado_por_uf(ano: int, dimensao: str | Path) -> dict[str, int]:
    """Le a dimensao local, que contem apenas os totais oficiais por UF."""
    caminho_dimensao = Path(dimensao)
    if not caminho_dimensao.exists():
        raise FileNotFoundError(
            f"dimensao de eleitorado ausente: {caminho_dimensao}. "
            "Gere com: python -m fundo_eleitoral.dimensoes --ano <ano>"
        )
    rows = duckdb.sql(f"""
        SELECT upper(trim(sg_uf)), cast(qt_eleitores AS BIGINT)
        FROM '{caminho_dimensao}'
        WHERE ano = {ano} AND upper(trim(sg_uf)) <> 'ZZ'
    """).fetchall()
    if {uf for uf, _ in rows} != UFS_BRASIL:
        raise ValueError(
            f"eleitorado de {ano} deveria conter exatamente as 27 UFs brasileiras"
        )
    return {uf: eleitorado for uf, eleitorado in rows}


def _cadeiras_por_uf(ano: int, raiz: str | Path, cargo: str) -> tuple[dict[str, int], int]:
    """Cadeiras em disputa por UF, derivadas de quem foi eleito.

    Conferido contra referencia externa: da 513 deputados federais em 2018 e em
    2022, que e o tamanho da Camara.

    Devolve tambem o ciclo de onde os numeros vieram. Em 2026 os resultados
    ainda nao existem (`ds_sit_tot_turno` = '#NULO'), entao a funcao recua para
    o ciclo anterior -- e quem chama precisa dizer isso ao leitor, porque a
    redistribuicao de cadeiras de 2023 alterou a bancada de varios estados.
    """
    for candidato_ano in (ano, ano - 4, ano - 8):
        cand = caminho(raiz, candidato_ano, "consulta_cand")
        try:
            rows = duckdb.sql(f"""
                SELECT upper(trim(sg_uf)) AS uf, count(*) AS n
                FROM (SELECT DISTINCT sq_candidato, sg_uf FROM '{cand}'
                      WHERE upper(trim(ds_cargo)) = '{cargo.upper()}'
                        AND ds_sit_tot_turno ILIKE 'ELEITO%')
                GROUP BY 1
            """).fetchall()
        except duckdb.Error:
            continue
        cadeiras = {uf: n for uf, n in rows if uf in UFS_BRASIL}
        if cadeiras:
            return cadeiras, candidato_ano
    return {}, ano


def prioridade_geografica(
    ano: int,
    raiz: str | Path = HF,
    dimensao: str | Path = DIMENSAO_ELEITORADO,
    por_partido: bool = False,
    apenas_aptas: bool = False,
    cargos: tuple[str, ...] = (),
    ufs: tuple[str, ...] = (),
    minimo_reais: float = 0.0,
) -> list[LinhaGeografica]:
    """Mede quais UFs recebem FEFC acima do seu peso no eleitorado.

    A comparacao usa o eleitorado domiciliado nas 27 UFs brasileiras. O TSE
    identifica eleitores no exterior como ``ZZ``; eles nao pertencem a uma UF
    e ficam fora desse denominador. Pelas mesmas razoes, receitas de
    candidaturas nacionais (``SG_UF = BR``) nao entram no indice: distribui-las
    arbitrariamente entre estados faria a medida parecer precisa sem ser.

    Com ``por_partido=True``, cada partido tem seu proprio total de FEFC como
    denominador; sem a flag, o resultado mostra a prioridade territorial do
    conjunto dos partidos.
    """
    eleitorado = _eleitorado_por_uf(ano, dimensao)
    # Cadeiras so fazem sentido com um cargo unico: a comparacao com o
    # eleitorado mede malapportionment (RR elege 8 deputados com 366 mil
    # eleitores, por piso constitucional), nao escolha do partido. Ver ADR-012.
    cadeiras = {}
    if len(cargos) == 1:
        cadeiras, _ = _cadeiras_por_uf(ano, raiz, cargos[0])
    total_cadeiras = sum(cadeiras.values())
    cand = caminho(raiz, ano, "consulta_cand")
    receitas = caminho(raiz, ano, "receitas_candidatos")
    aptidao = clausula_aptidao(cand, apenas_aptas, "AND")
    _cte_fefc = cte_fefc(receitas)

    rows = duckdb.sql(f"""
        WITH candidaturas AS (
          SELECT sq_candidato,
                 any_value(upper(trim(sg_partido))) AS partido,
                 any_value(upper(trim(sg_uf))) AS uf,
                 any_value(upper(trim(ds_cargo))) AS cargo
          FROM '{cand}'
          WHERE nm_tipo_eleicao ILIKE '%ORDINÁRIA%'
          {aptidao}
          GROUP BY 1
        ),
        {_cte_fefc}
        SELECT c.partido, c.uf, c.cargo, coalesce(f.valor, 0.0) AS valor
        FROM candidaturas c
        LEFT JOIN fefc f USING (sq_candidato)
        WHERE c.partido IS NOT NULL
          AND c.uf IS NOT NULL
          AND c.uf <> 'BR'
    """).fetchall()

    filtro_cargos = {cargo.upper() for cargo in cargos}
    filtro_ufs = {uf.upper() for uf in ufs}
    grupos: dict[str | None, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for partido, uf, cargo, valor in rows:
        if uf not in eleitorado:
            continue
        if filtro_cargos and cargo not in filtro_cargos:
            continue
        partido = "PCDOB" if partido == "PC DO B" else partido
        grupo = partido if por_partido else None
        grupos[grupo][uf].append(valor)

    # A visao agregada inclui UFs sem repasse para expor prioridade zero.
    if not por_partido:
        grupos[None]

    total_eleitorado = sum(eleitorado.values())
    resultado = []
    for partido, valores_por_uf in grupos.items():
        total_fefc = sum(sum(valores) for valores in valores_por_uf.values())
        if total_fefc < minimo_reais:
            continue
        # ``--uf`` escolhe o que exibir, nao o denominador. Caso contrario,
        # pedir somente SP faria SP parecer ter 100% do FEFC nacional.
        ufs_resultado = sorted(filtro_ufs or (valores_por_uf if por_partido else eleitorado))
        for uf in ufs_resultado:
            valores = valores_por_uf.get(uf, [])
            valor = sum(valores)
            pct_eleitorado = 100 * eleitorado[uf] / total_eleitorado
            pct_fefc = 100 * valor / total_fefc if total_fefc else 0.0
            resultado.append(LinhaGeografica(
                ano=ano,
                partido=partido,
                uf=uf,
                metricas=MetricasGeograficas(
                    eleitorado=eleitorado[uf],
                    pct_eleitorado=pct_eleitorado,
                    total_fefc=valor,
                    pct_fefc=pct_fefc,
                    diferenca_pp=pct_fefc - pct_eleitorado,
                    indice_prioridade=pct_fefc / pct_eleitorado if pct_eleitorado else 0.0,
                    cadeiras=cadeiras.get(uf) if cadeiras else None,
                    pct_cadeiras=(100 * cadeiras[uf] / total_cadeiras
                                  if cadeiras.get(uf) and total_cadeiras else None),
                    indice_por_cadeira=(
                        pct_fefc / (100 * cadeiras[uf] / total_cadeiras)
                        if cadeiras.get(uf) and total_cadeiras else None),
                    n_candidaturas=len(valores),
                    n_financiadas=sum(v > 0 for v in valores),
                ),
            ))
    return sorted(resultado, key=lambda linha: (-linha.metricas.diferenca_pp, linha.partido or "", linha.uf))


def relatorio(
    ano: int,
    por_partido: bool = False,
    apenas_aptas: bool = False,
    cargos: tuple[str, ...] = (),
    ufs: tuple[str, ...] = (),
    minimo_reais: float = 0.0,
) -> None:
    linhas = prioridade_geografica(
        ano, por_partido=por_partido, apenas_aptas=apenas_aptas, cargos=cargos,
        ufs=ufs, minimo_reais=minimo_reais,
    )
    detalhe = "por partido" if por_partido else "conjunto dos partidos"
    tem_cadeira = any(l.metricas.indice_por_cadeira is not None for l in linhas)
    print(f"\n=== {ano} — prioridade geografica ({detalhe})")
    if tem_cadeira:
        print("    Indice por cadeira isola a escolha do partido; o indice por eleitorado")
        print("    mede sobretudo o piso constitucional de bancada (ADR-012).")
    print("    partido       UF  eleitorado  eleitorado%       FEFC  FEFC%   dif.  indice"
          + ("  cadeiras  x cadeira" if tem_cadeira else ""))
    for linha in linhas:
        m = linha.metricas
        print(
            f"    {(linha.partido or '-'):13.13} {linha.uf:>2}  "
            f"{m.eleitorado:10,d} {m.pct_eleitorado:10.2f}% "
            f"R$ {m.total_fefc / 1e6:7.1f} mi {m.pct_fefc:5.2f}% "
            f"{m.diferenca_pp:+5.2f} {m.indice_prioridade:6.2f}x".replace(",", ".")
            + (f" {m.cadeiras or 0:9d} {m.indice_por_cadeira:9.2f}x"
               if m.indice_por_cadeira is not None else "")
        )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Prioridade geografica do FEFC")
    p.add_argument("--ano", type=int, action="append", help="ano eleitoral (repetivel)")
    p.add_argument("--por-partido", action="store_true", help="calcula o indice dentro de cada partido")
    p.add_argument("--apenas-aptas", action="store_true")
    p.add_argument("--cargo", action="append", default=[])
    p.add_argument("--uf", action="append", default=[])
    p.add_argument("--minimo-milhoes", type=float, default=0.0)
    args = p.parse_args(argv)
    for ano in args.ano or (2022,):
        relatorio(ano, por_partido=args.por_partido, apenas_aptas=args.apenas_aptas,
                  cargos=tuple(args.cargo), ufs=tuple(args.uf),
                  minimo_reais=args.minimo_milhoes * 1e6)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
