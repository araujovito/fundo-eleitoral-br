"""Mostra os fluxos declarados de FEFC entre diretórios e candidaturas.

Uso:
    python -m fundo_eleitoral.fluxos --ano 2022 --partido PDT
    python -m fundo_eleitoral.fluxos --ano 2022 --para-candidaturas
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import duckdb

from .consulta import HF, caminho

_VALOR = "CAST(replace(vr_receita, ',', '.') AS DOUBLE)"
_FUNDO = "FUNDO ESPECIAL"
DIRETORIO = "diretorio"
CANDIDATURAS = "candidaturas"
FONTE = "fonte"


@dataclass(frozen=True)
class NoFluxo:
    partido: str | None
    esfera: str
    uf: str | None
    cargo: str | None = None
    tipo: str = DIRETORIO


@dataclass(frozen=True)
class LinhaFluxo:
    ano: int
    origem: NoFluxo
    destino: NoFluxo
    total: float
    n_lancamentos: int


def _esfera(valor: str | None) -> str:
    """Normaliza as três escalas que o TSE usa para diretórios partidários."""
    texto = (valor or "").strip().upper()
    if texto == "NACIONAL":
        return "nacional"
    if "ESTADUAL" in texto or "DISTRITAL" in texto:
        return "estadual_distrital"
    if texto == "MUNICIPAL":
        return "municipal"
    return "nao_informada"


def _partido(valor: str | None) -> str | None:
    texto = (valor or "").strip().upper()
    if not texto or texto in {"#NULO", "#NE"}:
        return None
    return "PCDOB" if texto == "PC DO B" else texto


def _uf(valor: str | None) -> str | None:
    texto = (valor or "").strip().upper()
    return None if not texto or texto in {"#NULO", "#NE"} else texto


def fluxos_fefc(
    ano: int,
    raiz: str | Path = HF,
    partidos: tuple[str, ...] = (),
    incluir_candidaturas: bool = True,
    incluir_diretorios: bool = True,
    minimo_reais: float = 1e6,
) -> list[LinhaFluxo]:
    """Lista arestas de FEFC declaradas entre nós do sistema partidário.

    Uma aresta representa uma receita declarada pelo destino. Por isso, uma
    cadeia nacional -> estadual -> candidatura aparece em duas arestas, como
    deve acontecer num grafo. Elas **não** podem ser somadas para estimar o
    fundo disponível: seria dupla contagem do mesmo recurso em estágios
    distintos. O módulo não tenta ligar os lançamentos em uma cadeia única,
    porque os arquivos públicos não carregam um identificador transacional
    comum entre as prestações de contas de diretórios e candidaturas.

    O nó de candidaturas é agregado por partido, UF e cargo; o nó de diretório
    é agregado por partido, esfera e UF. A origem precisa estar identificada
    pelo TSE como diretório partidário. Repasses de candidatura para candidatura
    ficam fora, pois não são arestas do caminho partidário e duplicam FEFC já
    recebido do partido (ADR-009).
    """
    if not incluir_candidaturas and not incluir_diretorios:
        raise ValueError("selecione ao menos um tipo de destino")

    orgaos = caminho(raiz, ano, "receitas_orgaos_partidarios")
    candidatos = caminho(raiz, ano, "receitas_candidatos")
    consultas = []
    if incluir_diretorios:
        consultas.append(f"""
            SELECT sg_partido_doador AS partido_origem,
                   ds_esfera_partidaria_doador AS esfera_origem,
                   sg_uf_doador AS uf_origem,
                   sg_partido AS partido_destino,
                   ds_esfera_partidaria AS esfera_destino,
                   sg_uf AS uf_destino,
                   NULL AS cargo_destino,
                   '{DIRETORIO}' AS tipo_destino,
                   nr_cpf_cnpj_doador AS identificador_origem,
                   nr_cnpj_prestador_conta AS identificador_destino,
                   {_VALOR} AS valor
            FROM '{orgaos}'
            WHERE upper(trim(ds_fonte_receita)) = '{_FUNDO}'
              AND ds_esfera_partidaria_doador IS NOT NULL
              AND upper(trim(ds_esfera_partidaria_doador)) NOT IN ('#NULO', '#NE')
        """)
    if incluir_candidaturas:
        consultas.append(f"""
            SELECT sg_partido_doador AS partido_origem,
                   ds_esfera_partidaria_doador AS esfera_origem,
                   sg_uf_doador AS uf_origem,
                   sg_partido AS partido_destino,
                   NULL AS esfera_destino,
                   sg_uf AS uf_destino,
                   ds_cargo AS cargo_destino,
                   '{CANDIDATURAS}' AS tipo_destino,
                   NULL AS identificador_origem,
                   NULL AS identificador_destino,
                   {_VALOR} AS valor
            FROM '{candidatos}'
            WHERE upper(trim(ds_fonte_receita)) = '{_FUNDO}'
              AND ds_esfera_partidaria_doador IS NOT NULL
              AND upper(trim(ds_esfera_partidaria_doador)) NOT IN ('#NULO', '#NE')
        """)
    rows = duckdb.sql(" UNION ALL ".join(consultas)).fetchall()

    filtro_partidos = {_partido(partido) for partido in partidos}
    filtro_partidos.discard(None)
    grupos: dict[tuple[NoFluxo, NoFluxo], list[float]] = defaultdict(list)
    for (
        partido_origem, esfera_origem, uf_origem, partido_destino,
        esfera_destino, uf_destino, cargo_destino, tipo_destino,
        identificador_origem, identificador_destino, valor,
    ) in rows:
        origem = NoFluxo(_partido(partido_origem), _esfera(esfera_origem), _uf(uf_origem))
        destino = NoFluxo(
            _partido(partido_destino),
            _esfera(esfera_destino) if tipo_destino == DIRETORIO else CANDIDATURAS,
            _uf(uf_destino),
            (cargo_destino or "").strip().upper() if tipo_destino == CANDIDATURAS else None,
            tipo_destino,
        )
        # A direção nacional declara a entrada do FEFC como se fosse doação do
        # próprio CNPJ. Isso é uma convenção contábil de entrada, não uma
        # transferência nacional -> nacional; expô-la assim inventaria um
        # autoelo. O nó-fonte preserva o valor e deixa a semântica explícita.
        if (
            tipo_destino == DIRETORIO
            and identificador_origem
            and identificador_origem == identificador_destino
        ):
            origem = NoFluxo(None, "fundo_especial", None, tipo=FONTE)
        if filtro_partidos and not ({origem.partido, destino.partido} & filtro_partidos):
            continue
        grupos[(origem, destino)].append(valor)

    resultado = [
        LinhaFluxo(ano, origem, destino, sum(valores), len(valores))
        for (origem, destino), valores in grupos.items()
        if sum(valores) >= minimo_reais
    ]
    return sorted(
        resultado,
        key=lambda linha: (
            -linha.total,
            linha.origem.partido or "",
            linha.origem.esfera,
            linha.origem.uf or "",
            linha.destino.partido or "",
            linha.destino.esfera,
            linha.destino.uf or "",
            linha.destino.cargo or "",
        ),
    )


def _rotulo(no: NoFluxo) -> str:
    if no.tipo == FONTE:
        return "fundo_especial"
    if no.tipo == CANDIDATURAS:
        return f"candidaturas/{no.partido or '-'}/{no.uf or '-'}/{no.cargo or '-'}"
    return f"{no.esfera}/{no.partido or '-'}/{no.uf or '-'}"


def _valor_dot(valor: float) -> str:
    if valor >= 1e6:
        return f"R$ {valor / 1e6:.2f} mi"
    return f"R$ {valor:,.2f}".replace(",", ".")


def grafo_dot(linhas: list[LinhaFluxo]) -> str:
    """Renderiza as arestas em DOT, formato aberto aceito pelo Graphviz."""
    nos = sorted(
        {no for linha in linhas for no in (linha.origem, linha.destino)},
        key=lambda no: (_rotulo(no), no.tipo),
    )
    ids = {no: f"n{i}" for i, no in enumerate(nos)}
    definicoes = []
    for no in nos:
        forma = "box" if no.tipo == FONTE else ("ellipse" if no.tipo == CANDIDATURAS else "oval")
        definicoes.append(f'  {ids[no]} [label="{_rotulo(no)}", shape={forma}];')
    arestas = [
        f'  {ids[linha.origem]} -> {ids[linha.destino]} '
        f'[label="{_valor_dot(linha.total)}\\n{linha.n_lancamentos} lançamentos"];'
        for linha in linhas
    ]
    return "\n".join(["digraph fefc {", "  rankdir=LR;", *definicoes, *arestas, "}"])


def relatorio(
    ano: int,
    partidos: tuple[str, ...] = (),
    incluir_candidaturas: bool = True,
    incluir_diretorios: bool = True,
    minimo_reais: float = 1e6,
) -> None:
    linhas = fluxos_fefc(
        ano, partidos=partidos, incluir_candidaturas=incluir_candidaturas,
        incluir_diretorios=incluir_diretorios, minimo_reais=minimo_reais,
    )
    print(f"\n=== {ano} — fluxos declarados de FEFC")
    print("    origem -> destino                                              lanc.       valor")
    for linha in linhas:
        print(
            f"    {_rotulo(linha.origem):35.35} -> {_rotulo(linha.destino):45.45} "
            f"{linha.n_lancamentos:6d} R$ {linha.total / 1e6:8.2f} mi"
        )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Fluxos de FEFC entre diretórios e candidaturas")
    p.add_argument("--ano", type=int, action="append", help="ano eleitoral (repetivel)")
    p.add_argument("--partido", action="append", default=[])
    p.add_argument("--minimo-milhoes", type=float, default=1.0)
    p.add_argument("--somente-diretorios", action="store_true")
    p.add_argument("--somente-candidaturas", action="store_true")
    p.add_argument("--formato", choices=("tabela", "dot"), default="tabela")
    args = p.parse_args(argv)
    if args.somente_diretorios and args.somente_candidaturas:
        p.error("--somente-diretorios e --somente-candidaturas nao podem ser usados juntos")
    for ano in args.ano or (2022,):
        opcoes = {
            "partidos": tuple(args.partido),
            "incluir_candidaturas": not args.somente_diretorios,
            "incluir_diretorios": not args.somente_candidaturas,
            "minimo_reais": args.minimo_milhoes * 1e6,
        }
        if args.formato == "dot":
            print(grafo_dot(fluxos_fefc(ano, **opcoes)))
        else:
            relatorio(ano, **opcoes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
