"""Catalogo de fontes do TSE.

ATENCAO: os nomes de arquivo abaixo seguem o padrao publicado pelo portal de
dados abertos do TSE, mas NAO foram verificados contra o servidor -- o dominio
tse.jus.br responde 403 a partir de algumas faixas de IP residenciais. Rode
`python -m fundo_eleitoral.ingestao --verificar` num ambiente com saida liberada
(Codespaces, Colab) antes de confiar neste catalogo.
"""

from __future__ import annotations

from dataclasses import dataclass

BASE = "https://cdn.tse.jus.br/estatistica/sead/odsele"

ANOS_ELEICAO = (2018, 2022, 2026)


@dataclass(frozen=True)
class Fonte:
    """Um ZIP do TSE e o que esperamos encontrar dentro dele."""

    chave: str
    url: str
    ano: int
    # Prefixo dos CSVs de interesse dentro do ZIP. O TSE quebra por UF
    # (ex.: receitas_candidatos_2022_SP.csv), entao casamos por prefixo.
    prefixos_csv: tuple[str, ...]


def fontes_do_ano(ano: int) -> list[Fonte]:
    pc = f"{BASE}/prestacao_contas"
    return [
        Fonte(
            chave=f"contas_candidatos_{ano}",
            url=f"{pc}/prestacao_de_contas_eleitorais_candidatos_{ano}.zip",
            ano=ano,
            prefixos_csv=(f"receitas_candidatos_{ano}", f"despesas_candidatos_{ano}"),
        ),
        Fonte(
            chave=f"contas_partidos_{ano}",
            url=f"{pc}/prestacao_de_contas_eleitorais_partidos_{ano}.zip",
            ano=ano,
            prefixos_csv=(f"receitas_partidos_{ano}", f"despesas_partidos_{ano}"),
        ),
        Fonte(
            chave=f"candidatos_{ano}",
            url=f"{BASE}/consulta_cand/consulta_cand_{ano}.zip",
            ano=ano,
            prefixos_csv=(f"consulta_cand_{ano}",),
        ),
    ]


def todas_fontes(anos: tuple[int, ...] = ANOS_ELEICAO) -> list[Fonte]:
    return [f for ano in anos for f in fontes_do_ano(ano)]


# Dialeto dos CSVs do TSE: latin-1, ponto-e-virgula, decimal com virgula,
# aspas em todo campo e "#NULO#" como sentinela de nulo.
DIALETO_TSE = {
    "encoding": "latin-1",
    "separator": ";",
    "decimal_comma": True,
    "null_values": ["#NULO#", "#NE#", "-1", ""],
}
