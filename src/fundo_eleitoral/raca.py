"""Proporcionalidade racial na distribuicao do FEFC.

Desde as eleicoes gerais de 2022, o TSE exige que os recursos sejam
distribuidos na proporcao das candidaturas negras apresentadas pelo partido.
Pessoas pretas e pardas compoem, juntas, a categoria negra.

Uso:
    python -m fundo_eleitoral.raca
    python -m fundo_eleitoral.raca --ano 2022 --minimo-milhoes 20
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import duckdb

from .consulta import HF, caminho, clausula_aptidao, cte_fefc

RACAS_NEGRAS = ("PRETA", "PARDA")


@dataclass(frozen=True)
class LinhaRaca:
    ano: int
    partido: str
    fefc_milhoes: float
    pct_repassado_negras: float
    pct_candidaturas_negras: float
    pct_candidaturas_sem_raca: float

    @property
    def diferenca(self) -> float:
        """Pontos percentuais acima ou abaixo da proporcao de candidaturas."""
        return self.pct_repassado_negras - self.pct_candidaturas_negras

    @property
    def proporcional(self) -> bool:
        return self.diferenca >= 0

    @property
    def deficit_milhoes(self) -> float:
        """FEFC direto adicional para igualar a proporcao, limitado a zero."""
        return max(0.0, -self.diferenca * self.fefc_milhoes / 100)






def proporcionalidade_racial(
    ano: int,
    raiz: str | Path = HF,
    minimo_reais: float = 20e6,
    apenas_aptas: bool = False,
) -> list[LinhaRaca]:
    """Compara a fatia negra nas candidaturas e nos repasses de FEFC.

    A raça vem de ``consulta_cand`` e os repasses são agregados por
    ``sq_candidato`` antes da junção. Assim, múltiplos repasses não duplicam a
    candidatura e quem não recebeu FEFC permanece no denominador com zero.

    Em 2026, ``apenas_aptas`` não é aplicado enquanto a situação das
    candidaturas não tiver sido publicada. Eleições suplementares presentes no
    arquivo anual são sempre excluídas.
    """
    cand = caminho(raiz, ano, "consulta_cand")
    rec = caminho(raiz, ano, "receitas_candidatos")
    aptidao = clausula_aptidao(cand, apenas_aptas, "AND")
    _cte_fefc = cte_fefc(rec)

    negras = ", ".join(f"'{raca}'" for raca in RACAS_NEGRAS)
    rows = duckdb.sql(f"""
        WITH candidaturas AS (
          SELECT sq_candidato,
                 any_value(upper(trim(sg_partido))) AS partido,
                 any_value(upper(trim(ds_cor_raca))) AS raca
          FROM '{cand}'
          WHERE nm_tipo_eleicao ILIKE '%ORDINÁRIA%'
          {aptidao}
          GROUP BY 1
        ),
        {_cte_fefc},
        base AS (
          SELECT c.partido, c.raca, coalesce(f.valor, 0.0) AS valor
          FROM candidaturas c
          LEFT JOIN fefc f USING (sq_candidato)
          WHERE c.partido IS NOT NULL
        )
        SELECT partido,
               sum(valor) / 1e6 AS total_milhoes,
               100 * coalesce(sum(valor) FILTER (WHERE raca IN ({negras})), 0)
                   / nullif(sum(valor), 0) AS pct_fefc_negras,
               100.0 * count(*) FILTER (WHERE raca IN ({negras})) / count(*) AS pct_cand_negras,
               100.0 * count(*) FILTER (
                   WHERE raca IS NULL OR raca IN ('NÃO INFORMADO', 'NÃO DIVULGÁVEL')
               ) / count(*) AS pct_sem_raca
        FROM base
        GROUP BY 1
        HAVING sum(valor) >= {minimo_reais}
        ORDER BY pct_fefc_negras - pct_cand_negras
    """).fetchall()

    resultado = []
    for partido, total, pct_fefc, pct_cand, pct_sem_raca in rows:
        partido = "PCDOB" if partido == "PC DO B" else partido
        resultado.append(LinhaRaca(
            ano=ano,
            partido=partido,
            fefc_milhoes=total,
            pct_repassado_negras=pct_fefc,
            pct_candidaturas_negras=pct_cand,
            pct_candidaturas_sem_raca=pct_sem_raca,
        ))
    return resultado


def total_nacional(
    ano: int,
    raiz: str | Path = HF,
    apenas_aptas: bool = False,
) -> LinhaRaca:
    """Agregado nacional, usando as mesmas regras da analise partidaria."""
    cand = caminho(raiz, ano, "consulta_cand")
    rec = caminho(raiz, ano, "receitas_candidatos")
    aptidao = clausula_aptidao(cand, apenas_aptas, "AND")
    _cte_fefc = cte_fefc(rec)
    negras = ", ".join(f"'{raca}'" for raca in RACAS_NEGRAS)
    total, pct_fefc, pct_cand, pct_sem_raca = duckdb.sql(f"""
        WITH candidaturas AS (
          SELECT sq_candidato, any_value(upper(trim(ds_cor_raca))) AS raca
          FROM '{cand}'
          WHERE nm_tipo_eleicao ILIKE '%ORDINÁRIA%'
          {aptidao}
          GROUP BY 1
        ),
        {_cte_fefc}
        SELECT sum(coalesce(f.valor, 0)) / 1e6,
               100 * coalesce(sum(f.valor) FILTER (WHERE c.raca IN ({negras})), 0)
                   / nullif(sum(f.valor), 0),
               100.0 * count(*) FILTER (WHERE c.raca IN ({negras})) / count(*),
               100.0 * count(*) FILTER (
                   WHERE c.raca IS NULL OR c.raca IN ('NÃO INFORMADO', 'NÃO DIVULGÁVEL')
               ) / count(*)
        FROM candidaturas c LEFT JOIN fefc f USING (sq_candidato)
    """).fetchone()
    return LinhaRaca(ano, "BRASIL", total, pct_fefc, pct_cand, pct_sem_raca)


def relatorio(
    anos: tuple[int, ...] = (2018, 2022, 2026),
    minimo_reais: float = 20e6,
    apenas_aptas: bool = False,
) -> None:
    for ano in anos:
        nacional = total_nacional(ano, apenas_aptas=apenas_aptas)
        vigencia = "linha de base" if ano < 2022 else "regra vigente"
        print(
            f"\n=== {ano} — {vigencia} — FEFC R$ {nacional.fefc_milhoes / 1e3:.2f} bi"
            f" — negras: {nacional.pct_candidaturas_negras:.1f}% das candidaturas,"
            f" {nacional.pct_repassado_negras:.1f}% do fundo"
        )
        linhas = proporcionalidade_racial(
            ano,
            minimo_reais=minimo_reais,
            apenas_aptas=apenas_aptas,
        )
        abaixo = [linha for linha in linhas if not linha.proporcional]
        print(f"    {len(abaixo)} de {len(linhas)} partidos abaixo da proporção")
        print("    partido          FEFC   candid.  repasse   diferença   déficit  sem raça")
        for linha in linhas:
            marca = "  ABAIXO" if not linha.proporcional else ""
            print(
                f"    {linha.partido:<13} R$ {linha.fefc_milhoes:7.1f} mi "
                f"{linha.pct_candidaturas_negras:7.1f}% "
                f"{linha.pct_repassado_negras:7.1f}% {linha.diferenca:+9.1f} pp "
                f"R$ {linha.deficit_milhoes:6.1f} mi "
                f"{linha.pct_candidaturas_sem_raca:7.1f}%{marca}"
            )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Proporcionalidade racial do FEFC")
    p.add_argument("--ano", type=int, action="append", help="ano eleitoral (repetível)")
    p.add_argument("--minimo-milhoes", type=float, default=20.0)
    p.add_argument("--apenas-aptas", action="store_true")
    args = p.parse_args(argv)
    relatorio(
        anos=tuple(args.ano) if args.ano else (2018, 2022, 2026),
        minimo_reais=args.minimo_milhoes * 1e6,
        apenas_aptas=args.apenas_aptas,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
