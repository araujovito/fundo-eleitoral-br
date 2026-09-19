"""Mede quantos reais de FEFC direto foram aplicados por voto nominal.

Uso:
    python -m fundo_eleitoral.eficiencia --ano 2022
    python -m fundo_eleitoral.eficiencia --ano 2022 --por partido cargo
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import duckdb

from .consulta import HF, caminho, clausula_aptidao, cte_fefc

RAIZ = Path(__file__).resolve().parents[2]
DIMENSAO_VOTOS = RAIZ / "dados" / "dimensoes" / "votos_candidatos.parquet"
_DIMENSOES = {"partido": 0, "uf": 1, "cargo": 2, "perfil": 3}

ELEITO = "eleito"
NAO_ELEITO = "nao_eleito"


@dataclass(frozen=True)
class MetricasEficiencia:
    total_fefc: float
    total_votos: int
    reais_por_voto: float | None
    n_candidaturas: int
    n_com_votos: int
    n_eleitas: int
    cobertura_votos_pct: float


@dataclass(frozen=True)
class LinhaEficiencia:
    ano: int
    partido: str | None
    uf: str | None
    cargo: str | None
    perfil: str | None
    metricas: MetricasEficiencia


def _tem_votos(ano: int, dimensao: str | Path) -> bool:
    caminho_dimensao = Path(dimensao)
    if not caminho_dimensao.exists():
        raise FileNotFoundError(
            f"dimensao de votos ausente: {caminho_dimensao}. "
            "O repositorio deve conter dados/dimensoes/votos_candidatos.parquet."
        )
    return bool(duckdb.sql(
        f"SELECT count(*) > 0 FROM '{caminho_dimensao}' WHERE ano = {ano}"
    ).fetchone()[0])


def _perfil(situacao: str | None) -> str:
    return ELEITO if (situacao or "").upper().startswith("ELEITO") else NAO_ELEITO


def eficiencia_eleitoral(
    ano: int,
    raiz: str | Path = HF,
    dimensao: str | Path = DIMENSAO_VOTOS,
    por: tuple[str, ...] = ("partido", "perfil"),
    apenas_aptas: bool = False,
    cargos: tuple[str, ...] = (),
    ufs: tuple[str, ...] = (),
    minimo_reais: float = 0.0,
    minimo_candidaturas: int = 1,
) -> list[LinhaEficiencia]:
    """Calcula FEFC direto por voto nominal, por grupo de candidaturas.

    O denominador são somente votos nominais associados a uma candidatura. Em
    eleições proporcionais, voto de legenda não é atribuído a pessoa alguma e
    fica deliberadamente fora: somá-lo aos votos das candidaturas reduziria o
    custo por voto do partido sem revelar qual campanha recebeu o benefício.

    Para candidaturas que disputaram dois turnos, a dimensão preserva apenas o
    último turno. Assim, votos de presidente e governador não são somados duas
    vezes. Ainda não há resultado eleitoral para 2026, portanto o módulo
    recusa esse ano em vez de produzir um indicador parcial enganoso.
    """
    invalidas = set(por) - _DIMENSOES.keys()
    if invalidas:
        raise ValueError(f"dimensoes invalidas: {', '.join(sorted(invalidas))}")
    if len(set(por)) != len(por):
        raise ValueError("dimensoes repetidas")
    if not _tem_votos(ano, dimensao):
        raise ValueError(f"nao ha resultados eleitorais consolidados para {ano}")

    cand = caminho(raiz, ano, "consulta_cand")
    receitas = caminho(raiz, ano, "receitas_candidatos")
    aptidao = clausula_aptidao(cand, apenas_aptas, "AND")
    _cte_fefc = cte_fefc(receitas)

    rows = duckdb.sql(f"""
        WITH candidaturas AS (
          SELECT sq_candidato,
                 any_value(upper(trim(sg_partido))) AS partido,
                 any_value(upper(trim(sg_uf))) AS uf,
                 any_value(upper(trim(ds_cargo))) AS cargo,
                 any_value(upper(trim(ds_sit_tot_turno))) AS situacao
          FROM '{cand}'
          WHERE nm_tipo_eleicao ILIKE '%ORDINÁRIA%'
          {aptidao}
          GROUP BY 1
        ),
        {_cte_fefc},
        votos AS (
          SELECT sq_candidato, qt_votos
          FROM '{dimensao}'
          WHERE ano = {ano}
        )
        SELECT c.partido, c.uf, c.cargo, c.situacao,
               coalesce(f.valor, 0.0) AS fefc,
               coalesce(v.qt_votos, 0) AS votos
        FROM candidaturas c
        LEFT JOIN fefc f USING (sq_candidato)
        LEFT JOIN votos v USING (sq_candidato)
        WHERE c.partido IS NOT NULL
    """).fetchall()

    filtro_cargos = {cargo.upper() for cargo in cargos}
    filtro_ufs = {uf.upper() for uf in ufs}
    grupos: dict[tuple[str | None, ...], list[tuple[float, int, bool]]] = defaultdict(list)
    for partido, uf, cargo, situacao, fefc, votos in rows:
        if filtro_cargos and cargo not in filtro_cargos:
            continue
        if filtro_ufs and uf not in filtro_ufs:
            continue
        partido = "PCDOB" if partido == "PC DO B" else partido
        perfil = _perfil(situacao)
        dimensoes = (partido, uf, cargo, perfil)
        chave = tuple(dimensoes[_DIMENSOES[d]] for d in por)
        grupos[chave].append((fefc, votos, perfil == ELEITO))

    resultado = []
    for chave, valores in grupos.items():
        total_fefc = sum(valor[0] for valor in valores)
        if total_fefc < minimo_reais or len(valores) < minimo_candidaturas:
            continue
        total_votos = sum(valor[1] for valor in valores)
        atributos = {dimensao: chave[i] for i, dimensao in enumerate(por)}
        n_com_votos = sum(valor[1] > 0 for valor in valores)
        resultado.append(LinhaEficiencia(
            ano=ano,
            partido=atributos.get("partido"),
            uf=atributos.get("uf"),
            cargo=atributos.get("cargo"),
            perfil=atributos.get("perfil"),
            metricas=MetricasEficiencia(
                total_fefc=total_fefc,
                total_votos=total_votos,
                reais_por_voto=total_fefc / total_votos if total_votos else None,
                n_candidaturas=len(valores),
                n_com_votos=n_com_votos,
                n_eleitas=sum(valor[2] for valor in valores),
                cobertura_votos_pct=100 * n_com_votos / len(valores),
            ),
        ))
    return sorted(
        resultado,
        key=lambda linha: (
            linha.metricas.reais_por_voto is None,
            -(linha.metricas.reais_por_voto or 0),
            linha.partido or "",
            linha.uf or "",
            linha.cargo or "",
            linha.perfil or "",
        ),
    )


def relatorio(
    ano: int,
    por: tuple[str, ...] = ("partido", "perfil"),
    apenas_aptas: bool = False,
    cargos: tuple[str, ...] = (),
    ufs: tuple[str, ...] = (),
    minimo_reais: float = 0.0,
    minimo_candidaturas: int = 1,
) -> None:
    linhas = eficiencia_eleitoral(
        ano, por=por, apenas_aptas=apenas_aptas, cargos=cargos, ufs=ufs,
        minimo_reais=minimo_reais, minimo_candidaturas=minimo_candidaturas,
    )
    print(f"\n=== {ano} — FEFC direto por voto nominal ({' / '.join(por) or 'nacional'})")
    print("    partido       UF  cargo                perfil       cand. eleitas      votos"
          "       FEFC    R$/voto")
    for linha in linhas:
        m = linha.metricas
        custo = f"R$ {m.reais_por_voto:8.2f}" if m.reais_por_voto is not None else "sem votos"
        print(
            f"    {(linha.partido or '-'):13.13} {(linha.uf or '-'):>2}  "
            f"{(linha.cargo or '-'):20.20} {(linha.perfil or '-'):11.11} "
            f"{m.n_candidaturas:5d} {m.n_eleitas:7d} {m.total_votos:10,d} "
            f"R$ {m.total_fefc / 1e6:7.1f} mi {custo}".replace(",", ".")
        )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Eficiencia eleitoral do FEFC")
    p.add_argument("--ano", type=int, action="append", help="ano eleitoral (repetivel)")
    p.add_argument("--por", choices=tuple(_DIMENSOES), nargs="*", default=("partido", "perfil"))
    p.add_argument("--apenas-aptas", action="store_true")
    p.add_argument("--cargo", action="append", default=[])
    p.add_argument("--uf", action="append", default=[])
    p.add_argument("--minimo-milhoes", type=float, default=0.0)
    p.add_argument("--minimo-candidaturas", type=int, default=1)
    args = p.parse_args(argv)
    for ano in args.ano or (2022,):
        relatorio(
            ano, por=tuple(args.por), apenas_aptas=args.apenas_aptas,
            cargos=tuple(args.cargo), ufs=tuple(args.uf),
            minimo_reais=args.minimo_milhoes * 1e6,
            minimo_candidaturas=args.minimo_candidaturas,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
