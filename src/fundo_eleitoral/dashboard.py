"""Exporta agregados públicos e reproduzíveis para o dashboard estático.

Execute: python -m fundo_eleitoral.dashboard --destino dashboard/public/data.json
Não exporta nomes, CPFs, CNPJs nem identificadores individuais.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from .consulta import HF, caminho, cte_fefc


def exportar(destino: Path, raiz: str = HF, anos: tuple[int, ...] = (2018, 2022, 2026)):
    resultado = {"generatedAt": datetime.now(UTC).isoformat(), "source": raiz,
                 "years": {}}
    dimensoes = Path(__file__).resolve().parents[2] / "dados" / "dimensoes"
    for ano in anos:
        cand = caminho(raiz, ano, "consulta_cand")
        rec = caminho(raiz, ano, "receitas_candidatos")
        query = f"""
            WITH c AS (
                SELECT sq_candidato,
                    any_value(upper(trim(sg_partido))) partido,
                    any_value(upper(trim(sg_uf))) uf,
                    any_value(upper(trim(ds_cargo))) cargo,
                    any_value(upper(trim(ds_genero))) genero,
                    any_value(upper(trim(ds_cor_raca))) raca
                FROM '{cand}' GROUP BY 1
            ), {cte_fefc(rec)}
            SELECT partido, uf, cargo, genero, raca,
                count(*) AS candidaturas,
                count(*) FILTER (WHERE coalesce(valor, 0) > 0) financiadas,
                sum(coalesce(valor, 0)) total
            FROM c LEFT JOIN fefc USING (sq_candidato)
            WHERE partido IS NOT NULL GROUP BY 1, 2, 3, 4, 5
        """
        cols = ("party", "uf", "office", "gender", "race", "candidates", "funded", "value")
        cells = [dict(zip(cols, row, strict=True)) for row in duckdb.sql(query).fetchall()]
        for cell in cells:
            if cell["party"] == "PC DO B":
                cell["party"] = "PCDOB"
            cell["value"] = round(cell["value"], 2)
        electorate = dict(duckdb.sql(f"SELECT sg_uf, qt_eleitores FROM "
                                    f"'{dimensoes / 'eleitorado.parquet'}' WHERE ano={ano}").fetchall())
        # Eficiência restrita a cargos proporcionais, comparáveis em turno único.
        efficiency = []
        if ano in (2018, 2022):
            from .eficiencia import eficiencia_eleitoral
            for row in eficiencia_eleitoral(ano, raiz=raiz, por=("partido", "uf", "cargo"),
                                           cargos=("DEPUTADO FEDERAL", "DEPUTADO ESTADUAL",
                                                   "DEPUTADO DISTRITAL")):
                efficiency.append({"party": row.partido, "uf": row.uf, "office": row.cargo,
                                   "value": round(row.metricas.total_fefc, 2),
                                   "votes": row.metricas.total_votos,
                                   "candidates": row.metricas.n_candidaturas})
        # Canais declarados, sem inferir que auto-receitas são dinheiro novo.
        flows = defaultdict(float)
        for tabela, tipo in (("receitas_orgaos_partidarios", "Diretório"),
                             ("receitas_candidatos", "Candidaturas")):
            dest = "ds_esfera_partidaria" if tipo == "Diretório" else "'Candidaturas'"
            path = caminho(raiz, ano, tabela)
            rows = duckdb.sql(f"""
                SELECT sg_partido, sg_partido_doador, ds_esfera_partidaria_doador,
                       {dest}, sum(CAST(replace(vr_receita, ',', '.') AS DOUBLE))
                FROM '{path}' WHERE upper(trim(ds_fonte_receita))='FUNDO ESPECIAL'
                GROUP BY 1, 2, 3, 4
            """).fetchall()
            for party, donor_party, source, target, value in rows:
                def normalizar(x):
                    x = (x or "").upper()
                    if "ESTADUAL" in x or "DISTRITAL" in x:
                        return "Estadual / distrital"
                    return {"NACIONAL": "Nacional", "MUNICIPAL": "Municipal",
                            "CANDIDATURAS": "Candidaturas"}.get(x, "Não identificada")
                key = ("PCDOB" if party == "PC DO B" else party,
                       "PCDOB" if donor_party == "PC DO B" else donor_party,
                       normalizar(source), normalizar(target))
                flows[key] += value
        resultado["years"][str(ano)] = {
            "cells": sorted(cells, key=lambda x: (x["party"], x["uf"] or "", x["office"] or "")),
            "electorate": electorate, "efficiency": efficiency,
            "flows": [{"party": p, "donorParty": dp, "source": s, "target": t,
                       "value": round(v, 2)} for (p, dp, s, t), v in flows.items()],
        }
        print(f"{ano}: {len(cells)} células; R$ {sum(c['value'] for c in cells):,.2f}", flush=True)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(".tmp")
    temporario.write_text(json.dumps(resultado, ensure_ascii=False, allow_nan=False,
                                     separators=(",", ":")), encoding="utf-8")
    temporario.replace(destino)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destino", type=Path, default=Path("dashboard/public/data.json"))
    parser.add_argument("--raiz", default=HF)
    args = parser.parse_args()
    exportar(args.destino, args.raiz)
