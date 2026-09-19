"""Compara o FEFC de incumbentes, candidaturas recorrentes e novos nomes.

O pareamento entre ciclos usa CPF valido. O resultado eleitoral do ciclo
anterior separa quem de fato foi eleito de quem apenas ja havia concorrido.

Uso:
    python -m fundo_eleitoral.renovacao --ano 2022 --cargo "DEPUTADO FEDERAL"
    python -m fundo_eleitoral.renovacao --ano 2026 --por partido uf
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import duckdb
from .consulta import HF, VALOR, caminho, cte_fefc, clausula_aptidao


_DIMENSOES = {"partido": 0, "uf": 1, "cargo": 2}
_ANTERIOR = {2022: 2018, 2026: 2022}

INCUMBENTE_MESMO_CARGO = "incumbente_mesmo_cargo"
ELEITO_OUTRO_CARGO = "eleito_outro_cargo"
CANDIDATO_RECORRENTE = "candidato_recorrente"
NOVO_NO_RECORTE = "novo_no_recorte"
CPF_INVALIDO = "cpf_invalido"

ORDEM_PERFIS = (
    INCUMBENTE_MESMO_CARGO,
    ELEITO_OUTRO_CARGO,
    CANDIDATO_RECORRENTE,
    NOVO_NO_RECORTE,
    CPF_INVALIDO,
)


@dataclass(frozen=True)
class MetricasPerfil:
    total_fefc: float
    pct_fefc: float
    n_candidaturas: int
    pct_candidaturas: float
    n_financiadas: int
    cobertura_pct: float
    media_por_candidatura: float
    media_por_financiada: float
    indice_alocacao: float


@dataclass(frozen=True)
class LinhaRenovacao:
    ano: int
    ano_anterior: int
    partido: str | None
    uf: str | None
    cargo: str | None
    perfil: str
    metricas: MetricasPerfil






def _perfil(cpf_valido: bool, ja_concorreu: bool, eleito: bool, mesmo_cargo: bool) -> str:
    if not cpf_valido:
        return CPF_INVALIDO
    if not ja_concorreu:
        return NOVO_NO_RECORTE
    if mesmo_cargo:
        return INCUMBENTE_MESMO_CARGO
    if eleito:
        return ELEITO_OUTRO_CARGO
    return CANDIDATO_RECORRENTE


def distribuicao_renovacao(
    ano: int,
    ano_anterior: int | None = None,
    raiz: str | Path = HF,
    por: tuple[str, ...] = ("partido",),
    apenas_aptas: bool = False,
    cargos: tuple[str, ...] = (),
    ufs: tuple[str, ...] = (),
    minimo_reais: float = 0.0,
    minimo_candidaturas: int = 1,
) -> list[LinhaRenovacao]:
    """Distribui candidaturas e FEFC conforme o histórico no ciclo anterior.

    ``novo_no_recorte`` significa ausente do ciclo imediatamente anterior, nao
    necessariamente estreante absoluto na politica. ``incumbente_mesmo_cargo``
    exige resultado ``ELEITO%`` no mesmo cargo; apenas ter concorrido antes
    produz ``candidato_recorrente``.

    A comparacao deve se limitar a cargos com mandato de quatro anos. Senadores
    eleitos oito anos antes nao aparecem no ciclo imediatamente anterior e
    seriam classificados incorretamente como novos.
    """
    ano_anterior = ano_anterior or _ANTERIOR.get(ano)
    if ano_anterior is None:
        raise ValueError(f"nao ha ciclo anterior configurado para {ano}")
    invalidas = set(por) - _DIMENSOES.keys()
    if invalidas:
        raise ValueError(f"dimensoes invalidas: {', '.join(sorted(invalidas))}")
    if len(set(por)) != len(por):
        raise ValueError("dimensoes repetidas")

    atual = caminho(raiz, ano, "consulta_cand")
    anterior = caminho(raiz, ano_anterior, "consulta_cand")
    receitas = caminho(raiz, ano, "receitas_candidatos")
    aptidao = clausula_aptidao(atual, apenas_aptas, "AND")
    _cte_fefc = cte_fefc(receitas)

    # O filtro de eleicao ordinaria impede que pleitos suplementares presentes
    # no mesmo arquivo anual criem falsos historicos ou candidaturas duplicadas.
    rows = duckdb.sql(f"""
        WITH atuais AS (
          SELECT sq_candidato,
                 any_value(upper(trim(sg_partido))) AS partido,
                 any_value(upper(trim(sg_uf))) AS uf,
                 any_value(upper(trim(ds_cargo))) AS cargo,
                 any_value(trim(nr_cpf_candidato)) AS cpf
          FROM '{atual}'
          WHERE nm_tipo_eleicao ILIKE '%ORDINÁRIA%'
          {aptidao}
          GROUP BY 1
        ),
        historico_cargo AS (
          SELECT trim(nr_cpf_candidato) AS cpf,
                 upper(trim(ds_cargo)) AS cargo,
                 bool_or(ds_sit_tot_turno ILIKE 'ELEITO%') AS eleito
          FROM '{anterior}'
          WHERE nm_tipo_eleicao ILIKE '%ORDINÁRIA%'
            AND regexp_matches(trim(nr_cpf_candidato), '^[0-9]{{11}}$')
          GROUP BY 1, 2
        ),
        {_cte_fefc}
        SELECT a.partido, a.uf, a.cargo, coalesce(f.valor, 0.0) AS valor,
               regexp_matches(a.cpf, '^[0-9]{{11}}$') AS cpf_valido,
               count(h.cpf) > 0 AS ja_concorreu,
               coalesce(bool_or(h.eleito), false) AS eleito,
               coalesce(bool_or(h.eleito AND h.cargo = a.cargo), false) AS mesmo_cargo
        FROM atuais a
        LEFT JOIN historico_cargo h USING (cpf)
        LEFT JOIN fefc f USING (sq_candidato)
        WHERE a.partido IS NOT NULL
        GROUP BY a.sq_candidato, a.partido, a.uf, a.cargo, f.valor, a.cpf
    """).fetchall()

    filtro_cargos = {cargo.upper() for cargo in cargos}
    filtro_ufs = {uf.upper() for uf in ufs}
    grupos: dict[tuple[str | None, ...], list[float]] = defaultdict(list)
    for partido, uf, cargo, valor, cpf_valido, ja_concorreu, eleito, mesmo_cargo in rows:
        if filtro_cargos and cargo not in filtro_cargos:
            continue
        if filtro_ufs and uf not in filtro_ufs:
            continue
        partido = "PCDOB" if partido == "PC DO B" else partido
        dimensoes = (partido, uf, cargo)
        chave_grupo = tuple(dimensoes[_DIMENSOES[d]] for d in por)
        perfil = _perfil(cpf_valido, ja_concorreu, eleito, mesmo_cargo)
        grupos[(*chave_grupo, perfil)].append(valor)

    totais_grupo: dict[tuple[str | None, ...], float] = defaultdict(float)
    candidaturas_grupo: dict[tuple[str | None, ...], int] = defaultdict(int)
    for chave, valores in grupos.items():
        grupo = chave[:-1]
        totais_grupo[grupo] += sum(valores)
        candidaturas_grupo[grupo] += len(valores)

    resultado = []
    for chave, valores in grupos.items():
        grupo, perfil = chave[:-1], chave[-1]
        total_grupo = totais_grupo[grupo]
        if total_grupo < minimo_reais or candidaturas_grupo[grupo] < minimo_candidaturas:
            continue
        total = sum(valores)
        financiadas = sum(v > 0 for v in valores)
        n = len(valores)
        total_candidaturas = candidaturas_grupo[grupo]
        pct_fefc = 100 * total / total_grupo if total_grupo else 0.0
        pct_candidaturas = 100 * n / total_candidaturas
        atributos = {dimensao: grupo[i] for i, dimensao in enumerate(por)}
        resultado.append(LinhaRenovacao(
            ano=ano,
            ano_anterior=ano_anterior,
            partido=atributos.get("partido"),
            uf=atributos.get("uf"),
            cargo=atributos.get("cargo"),
            perfil=perfil,
            metricas=MetricasPerfil(
                total_fefc=total,
                pct_fefc=pct_fefc,
                n_candidaturas=n,
                pct_candidaturas=pct_candidaturas,
                n_financiadas=financiadas,
                cobertura_pct=100 * financiadas / n,
                media_por_candidatura=total / n,
                media_por_financiada=total / financiadas if financiadas else 0.0,
                indice_alocacao=pct_fefc / pct_candidaturas,
            ),
        ))

    ordem = {perfil: i for i, perfil in enumerate(ORDEM_PERFIS)}
    return sorted(
        resultado,
        key=lambda linha: (
            linha.partido or "",
            linha.uf or "",
            linha.cargo or "",
            ordem[linha.perfil],
        ),
    )


def relatorio(
    ano: int,
    ano_anterior: int | None = None,
    por: tuple[str, ...] = ("partido",),
    apenas_aptas: bool = False,
    cargos: tuple[str, ...] = (),
    ufs: tuple[str, ...] = (),
    minimo_reais: float = 0.0,
    minimo_candidaturas: int = 1,
) -> None:
    linhas = distribuicao_renovacao(
        ano,
        ano_anterior=ano_anterior,
        por=por,
        apenas_aptas=apenas_aptas,
        cargos=cargos,
        ufs=ufs,
        minimo_reais=minimo_reais,
        minimo_candidaturas=minimo_candidaturas,
    )
    anterior_real = linhas[0].ano_anterior if linhas else ano_anterior or _ANTERIOR.get(ano)
    print(f"\n=== {ano} versus {anterior_real} — FEFC por histórico eleitoral")
    print("    partido       UF  cargo                perfil                    cand%"
          "  cob.       FEFC  FEFC% índice   média")
    for linha in linhas:
        m = linha.metricas
        print(
            f"    {(linha.partido or '-'):13.13} {(linha.uf or '-'):>2}  "
            f"{(linha.cargo or '-'):20.20} {linha.perfil:25.25} "
            f"{m.pct_candidaturas:5.1f}% "
            f"{m.cobertura_pct:5.1f}% R$ {m.total_fefc / 1e6:7.1f} mi "
            f"{m.pct_fefc:5.1f}% {m.indice_alocacao:5.2f}x "
            f"R$ {m.media_por_candidatura / 1e3:6.1f} mil"
        )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="FEFC de incumbentes e novos nomes")
    p.add_argument("--ano", type=int, action="append", help="ano atual (repetivel)")
    p.add_argument("--ano-anterior", type=int, help="sobrescreve o ciclo de comparacao")
    p.add_argument("--por", choices=tuple(_DIMENSOES), nargs="*", default=("partido",))
    p.add_argument("--apenas-aptas", action="store_true")
    p.add_argument("--cargo", action="append", default=[], help="cargo atual exato (repetivel)")
    p.add_argument("--uf", action="append", default=[], help="sigla da UF atual (repetivel)")
    p.add_argument("--minimo-milhoes", type=float, default=0.0)
    p.add_argument("--minimo-candidaturas", type=int, default=1)
    args = p.parse_args(argv)

    for ano in args.ano or [2022, 2026]:
        relatorio(
            ano,
            ano_anterior=args.ano_anterior,
            por=tuple(args.por),
            apenas_aptas=args.apenas_aptas,
            cargos=tuple(args.cargo),
            ufs=tuple(args.uf),
            minimo_reais=args.minimo_milhoes * 1e6,
            minimo_candidaturas=args.minimo_candidaturas,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
