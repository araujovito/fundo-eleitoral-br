"""Concentracao do FEFC entre candidaturas de um mesmo partido.

O calculo parte do cadastro de candidaturas, nao apenas das receitas. Assim,
quem nao recebeu FEFC entra com valor zero e afeta corretamente a cobertura e
o Gini. As receitas sao primeiro somadas por ``sq_candidato`` para que varios
repasses a uma mesma candidatura nao sejam confundidos com varios destinos.

Uso:
    python -m fundo_eleitoral.concentracao --ano 2022
    python -m fundo_eleitoral.concentracao --ano 2022 --por uf cargo
"""

from __future__ import annotations

import argparse
import math
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import duckdb

from .analise import HF

_VALOR = "CAST(replace(vr_receita, ',', '.') AS DOUBLE)"
_DIMENSOES = {"uf": "uf", "cargo": "cargo"}


@dataclass(frozen=True)
class MetricasConcentracao:
    """Medidas de distribuicao calculadas sobre valores nao negativos."""

    total: float
    n_candidaturas: int
    n_financiadas: int
    cobertura_pct: float
    gini: float
    hhi: float
    hhi_normalizado: float
    numero_efetivo: float
    top_1_pct: float
    top_10pct_pct: float


@dataclass(frozen=True)
class LinhaConcentracao:
    ano: int
    partido: str
    uf: str | None
    cargo: str | None
    metricas: MetricasConcentracao


def calcular_metricas(valores: Iterable[float]) -> MetricasConcentracao:
    """Calcula cobertura, Gini, HHI e participacao do topo.

    O HHI e a soma dos quadrados das participacoes e varia de ``1/n``
    (distribuicao igual) a 1 (uma candidatura recebe tudo). A versao
    normalizada remove a dependencia mecanica do numero de candidaturas e
    varia de 0 a 1. ``numero_efetivo`` e o inverso do HHI: quantos recebedores
    iguais produziriam a mesma concentracao observada.
    """
    xs = sorted(float(v) for v in valores)
    if any(not math.isfinite(v) or v < 0 for v in xs):
        raise ValueError("valores devem ser finitos e nao negativos")

    n = len(xs)
    total = sum(xs)
    financiadas = sum(v > 0 for v in xs)
    if n == 0 or total == 0:
        return MetricasConcentracao(
            total=total,
            n_candidaturas=n,
            n_financiadas=financiadas,
            cobertura_pct=0.0,
            gini=0.0,
            hhi=0.0,
            hhi_normalizado=0.0,
            numero_efetivo=0.0,
            top_1_pct=0.0,
            top_10pct_pct=0.0,
        )

    # Forma fechada para uma amostra ordenada, incluindo os zeros.
    soma_ponderada = sum((i + 1) * valor for i, valor in enumerate(xs))
    gini = (2 * soma_ponderada) / (n * total) - (n + 1) / n

    participacoes = [valor / total for valor in xs]
    hhi = sum(p * p for p in participacoes)
    hhi_minimo = 1 / n
    hhi_normalizado = (hhi - hhi_minimo) / (1 - hhi_minimo) if n > 1 else 1.0
    tamanho_topo = max(1, math.ceil(n * 0.10))

    return MetricasConcentracao(
        total=total,
        n_candidaturas=n,
        n_financiadas=financiadas,
        cobertura_pct=100 * financiadas / n,
        gini=max(0.0, min(1.0, gini)),
        hhi=hhi,
        hhi_normalizado=max(0.0, min(1.0, hhi_normalizado)),
        numero_efetivo=1 / hhi,
        top_1_pct=100 * xs[-1] / total,
        top_10pct_pct=100 * sum(xs[-tamanho_topo:]) / total,
    )


def _base(raiz: str | Path, ano: int, tabela: str) -> str:
    return f"{raiz}/{ano}/{tabela}.parquet"


def _tem_candidaturas_aptas(caminho: str) -> bool:
    return duckdb.sql(
        f"SELECT count(*) > 0 FROM '{caminho}' "
        "WHERE ds_situacao_candidatura ILIKE 'APTO%'"
    ).fetchone()[0]


def concentracao_fefc(
    ano: int,
    raiz: str | Path = HF,
    por: tuple[str, ...] = (),
    minimo_reais: float = 20e6,
    apenas_aptas: bool = False,
) -> list[LinhaConcentracao]:
    """Mede a concentracao do FEFC dentro de cada partido.

    ``por`` aceita ``"uf"`` e ``"cargo"``. Por padrao entram todas as
    candidaturas registradas, inclusive as que terminaram inaptas: a pergunta
    e onde o partido alocou dinheiro, e exclui-las faria o total analisado nao
    reconciliar com o FEFC efetivamente repassado. ``apenas_aptas`` oferece o
    recorte alternativo para perguntas sobre a disputa eleitoral final; em
    2026 ele nao e aplicado enquanto a situacao ainda nao tiver sido publicada.
    """
    invalidas = set(por) - _DIMENSOES.keys()
    if invalidas:
        raise ValueError(f"dimensoes invalidas: {', '.join(sorted(invalidas))}")
    if len(set(por)) != len(por):
        raise ValueError("dimensoes repetidas")

    cand = _base(raiz, ano, "consulta_cand")
    rec = _base(raiz, ano, "receitas_candidatos")
    filtro = ""
    if apenas_aptas and _tem_candidaturas_aptas(cand):
        filtro = "WHERE ds_situacao_candidatura ILIKE 'APTO%'"

    # O GROUP BY elimina duplicatas reais do cadastro: em 2018 e 2022 alguns
    # sq_candidato aparecem duas vezes, sem divergencia de partido/UF/cargo.
    rows = duckdb.sql(f"""
        WITH candidaturas AS (
          SELECT sq_candidato,
                 any_value(upper(trim(sg_partido))) AS partido,
                 any_value(sg_uf) AS uf,
                 any_value(ds_cargo) AS cargo
          FROM '{cand}'
          {filtro}
          GROUP BY 1
        ),
        fefc AS (
          SELECT sq_candidato, sum({_VALOR}) AS valor
          FROM '{rec}'
          WHERE ds_fonte_receita = 'FUNDO ESPECIAL'
          GROUP BY 1
        )
        SELECT c.partido, c.uf, c.cargo, coalesce(f.valor, 0.0) AS valor
        FROM candidaturas c
        LEFT JOIN fefc f USING (sq_candidato)
        WHERE c.partido IS NOT NULL
    """).fetchall()

    indices = tuple({"uf": 1, "cargo": 2}[d] for d in por)
    grupos: dict[tuple[str, ...], list[float]] = defaultdict(list)
    atributos: dict[tuple[str, ...], tuple[str | None, str | None]] = {}
    for partido, uf, cargo, valor in rows:
        # Normalizacao minima documentada no contexto; nao tenta fundir partidos
        # que de fato mudaram por incorporacao ou federacao entre ciclos.
        partido = "PCDOB" if partido == "PC DO B" else partido
        dimensoes = (uf, cargo)
        chave = (partido, *(dimensoes[i - 1] for i in indices))
        grupos[chave].append(valor)
        atributos[chave] = (
            uf if "uf" in por else None,
            cargo if "cargo" in por else None,
        )

    resultado = []
    for chave, valores in grupos.items():
        metricas = calcular_metricas(valores)
        if metricas.total < minimo_reais:
            continue
        uf, cargo = atributos[chave]
        resultado.append(LinhaConcentracao(ano, chave[0], uf, cargo, metricas))

    return sorted(
        resultado,
        key=lambda linha: (
            -linha.metricas.gini,
            linha.partido,
            linha.uf or "",
            linha.cargo or "",
        ),
    )


def relatorio(
    ano: int,
    por: tuple[str, ...] = (),
    minimo_reais: float = 20e6,
    apenas_aptas: bool = False,
) -> None:
    linhas = concentracao_fefc(ano, por=por, minimo_reais=minimo_reais,
                               apenas_aptas=apenas_aptas)
    detalhe = " / ".join(por) if por else "nacional"
    print(f"\n=== {ano} — concentracao do FEFC por partido ({detalhe})")
    print("    partido       UF  cargo                   FEFC   cand.  cob.   Gini"
          "  HHI(10k)  n.efet.  top 10%")
    for linha in linhas:
        m = linha.metricas
        print(
            f"    {linha.partido:<13} {(linha.uf or '-'):>2}  "
            f"{(linha.cargo or '-'):22.22} R$ {m.total / 1e6:7.1f} mi "
            f"{m.n_candidaturas:6d} {m.cobertura_pct:5.1f}% {m.gini:6.3f} "
            f"{m.hhi * 10_000:9.1f} {m.numero_efetivo:8.1f} {m.top_10pct_pct:7.1f}%"
        )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Concentracao do FEFC entre candidaturas")
    p.add_argument("--ano", type=int, action="append", help="ano eleitoral (repetivel)")
    p.add_argument("--por", choices=tuple(_DIMENSOES), nargs="*", default=())
    p.add_argument("--minimo-milhoes", type=float, default=20.0)
    p.add_argument("--apenas-aptas", action="store_true")
    args = p.parse_args(argv)

    for ano in args.ano or [2018, 2022, 2026]:
        relatorio(
            ano,
            por=tuple(args.por),
            minimo_reais=args.minimo_milhoes * 1e6,
            apenas_aptas=args.apenas_aptas,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
