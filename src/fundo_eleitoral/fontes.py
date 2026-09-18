"""Catalogo de fontes do TSE.

Nomes verificados contra o CDN em 2026-09-18 para 2018, 2022 e 2026.

Duas armadilhas de nomenclatura, ambas custaram um diagnostico errado antes de
serem descobertas (ver docs/decisoes.md, ADR-005 e ADR-006):

1. As contas de partido ficam sob "orgaos_partidarios", nao "partidos".
2. Nao existe "despesas_<x>": existe "despesas_contratadas" e "despesas_pagas",
   que sao coisas diferentes -- contratado e compromisso assumido, pago e
   desembolso efetivo, e os dois divergem.
"""

from __future__ import annotations

from dataclasses import dataclass

BASE = "https://cdn.tse.jus.br/estatistica/sead/odsele"

ANOS_ELEICAO = (2018, 2022, 2026)


@dataclass(frozen=True)
class Fonte:
    """Um ZIP do TSE e as tabelas de interesse dentro dele.

    `tabelas` guarda o nome-base de cada CSV, sem o ano e sem o sufixo de
    abrangencia -- a montagem final vira `<tabela>_<ano>_BRASIL.csv`.
    """

    chave: str
    url: str
    ano: int
    tabelas: tuple[str, ...]

    def arquivo_de(self, tabela: str) -> str:
        return f"{tabela}_{self.ano}_BRASIL.csv"


def fontes_do_ano(ano: int) -> list[Fonte]:
    pc = f"{BASE}/prestacao_contas"
    return [
        Fonte(
            chave=f"contas_candidatos_{ano}",
            url=f"{pc}/prestacao_de_contas_eleitorais_candidatos_{ano}.zip",
            ano=ano,
            tabelas=(
                "receitas_candidatos",
                "receitas_candidatos_doador_originario",
                "despesas_contratadas_candidatos",
                "despesas_pagas_candidatos",
            ),
        ),
        Fonte(
            chave=f"contas_orgaos_partidarios_{ano}",
            url=f"{pc}/prestacao_de_contas_eleitorais_orgaos_partidarios_{ano}.zip",
            ano=ano,
            tabelas=(
                "receitas_orgaos_partidarios",
                "receitas_orgaos_partidarios_doador_originario",
                "despesas_contratadas_orgaos_partidarios",
                "despesas_pagas_orgaos_partidarios",
            ),
        ),
        Fonte(
            chave=f"candidatos_{ano}",
            url=f"{BASE}/consulta_cand/consulta_cand_{ano}.zip",
            ano=ano,
            tabelas=("consulta_cand",),
        ),
    ]


def todas_fontes(anos: tuple[int, ...] = ANOS_ELEICAO) -> list[Fonte]:
    return [f for ano in anos for f in fontes_do_ano(ano)]


# Dialeto dos CSVs do TSE: latin-1, ponto-e-virgula, decimal com virgula,
# aspas em todo campo e "#NULO#" como sentinela de nulo.
DIALETO_TSE = {
    "encoding": "latin-1",
    "separator": ";",
    "null_values": ["#NULO#", "#NE#", "-1", ""],
}
