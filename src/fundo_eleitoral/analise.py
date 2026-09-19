"""Etapa 4: analise. Le apenas Parquet -- nunca baixa nem converte (ADR-001).

Recorte atual: cumprimento da cota de genero na distribuicao do FEFC.

A regra nao e "30%". Pelo ADI 5617 e pela jurisprudencia do TSE, o repasse
deve ser *proporcional* as candidaturas femininas do partido, com 30% como
piso. Um partido com 37% de mulheres candidatas que repassa 31% cumpre o piso
e ainda assim descumpre a regra -- e essa diferenca muda quem aparece na lista
de irregulares. Ver `piso_do_partido`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb

from .consulta import FONTE_FEFC, HF, ORIGEM_REPASSE, VALOR, caminho

# Dataset publico gerado por este projeto; a analise roda sem ingestao local.

PISO_LEGAL = 30.0

# A cota regula a distribuicao feita PELO PARTIDO: FEFC vindo de outra
# candidatura ja foi contado no repasse original (ADR-009).
_so_direto = f"AND ds_origem_receita <> '{ORIGEM_REPASSE}'"




@dataclass(frozen=True)
class LinhaPartido:
    partido: str
    fefc_milhoes: float
    pct_repassado: float
    pct_candidaturas: float

    @property
    def piso(self) -> float:
        return piso_do_partido(self.pct_candidaturas)

    @property
    def folga(self) -> float:
        """Pontos percentuais acima (ou abaixo) do que a regra exige."""
        return self.pct_repassado - self.piso

    @property
    def cumpre(self) -> bool:
        return self.folga >= 0


def piso_do_partido(pct_candidaturas: float) -> float:
    """O minimo exigido: proporcional as candidaturas, nunca menos que 30%."""
    return max(PISO_LEGAL, pct_candidaturas)




def cota_genero(ano: int, raiz: str | Path = HF, minimo_reais: float = 20e6) -> list[LinhaPartido]:
    """Repasse do FEFC a candidaturas femininas, por partido.

    `minimo_reais` corta partidos pequenos, onde poucas candidaturas fazem o
    percentual oscilar demais para significar alguma coisa.

    Em 2026 a situacao da candidatura ainda nao foi publicada
    (`ds_situacao_candidatura` = '#NE', registros sob julgamento), entao o
    filtro de aptidao so e aplicado quando existe -- do contrario o resultado
    viria vazio.
    """
    rec = caminho(raiz, ano, "receitas_candidatos")
    cand = caminho(raiz, ano, "consulta_cand")

    tem_situacao = duckdb.sql(
        f"SELECT count(*) FROM '{cand}' WHERE ds_situacao_candidatura ILIKE 'APTO%'"
    ).fetchone()[0] > 0
    filtro = "WHERE ds_situacao_candidatura ILIKE 'APTO%'" if tem_situacao else ""

    rows = duckdb.sql(f"""
        WITH fefc AS (
          SELECT sg_partido,
                 sum({VALOR}) AS total,
                 sum(CASE WHEN ds_genero = 'Feminino' THEN {VALOR} END) AS fem
          FROM '{rec}'
          WHERE ds_fonte_receita = '{FONTE_FEFC}' {_so_direto}
          GROUP BY 1
        ),
        cands AS (
          SELECT sg_partido,
                 count(*) AS n,
                 count(*) FILTER (WHERE ds_genero = 'FEMININO') AS nf
          FROM '{cand}' {filtro}
          GROUP BY 1
        )
        SELECT f.sg_partido, f.total / 1e6, 100 * f.fem / f.total, 100.0 * c.nf / c.n
        FROM fefc f JOIN cands c USING (sg_partido)
        WHERE f.total > {minimo_reais}
        ORDER BY 3 - greatest({PISO_LEGAL}, 100.0 * c.nf / c.n)
    """).fetchall()
    return [LinhaPartido(*r) for r in rows]


def total_nacional(ano: int, raiz: str | Path = HF) -> tuple[float, float]:
    """(FEFC total em bilhoes, % que foi para candidaturas femininas)."""
    rec = caminho(raiz, ano, "receitas_candidatos")
    total, fem = duckdb.sql(f"""
        SELECT sum({VALOR}), sum(CASE WHEN ds_genero = 'Feminino' THEN {VALOR} END)
        FROM '{rec}'
        WHERE ds_fonte_receita = '{FONTE_FEFC}' {_so_direto}
    """).fetchone()
    return total / 1e9, 100 * fem / total


def relatorio(anos: tuple[int, ...] = (2018, 2022, 2026), raiz: str | Path = HF) -> None:
    for ano in anos:
        bi, pct = total_nacional(ano, raiz)
        print(f"\n=== {ano} — FEFC R$ {bi:.2f} bi — {pct:.1f}% a candidaturas femininas")
        linhas = cota_genero(ano, raiz)
        abaixo = [x for x in linhas if not x.cumpre]
        print(f"    {len(abaixo)} de {len(linhas)} partidos abaixo do exigido")
        print(f"    {'partido':<14} {'repasse':>8} {'candidat.':>10} {'piso':>7} {'folga':>7}")
        for x in linhas:
            marca = "  ABAIXO" if not x.cumpre else ""
            print(f"    {x.partido:<14} {x.pct_repassado:7.1f}% {x.pct_candidaturas:9.1f}%"
                  f" {x.piso:6.1f}% {x.folga:+6.1f}{marca}")


if __name__ == "__main__":
    relatorio()
