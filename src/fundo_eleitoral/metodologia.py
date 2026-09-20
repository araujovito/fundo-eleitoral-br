"""Metadados metodologicos compartilhados pelos recortes e pelo dashboard."""

from __future__ import annotations

from dataclasses import asdict, dataclass

# Valor divulgado pelo TSE para o ciclo de 2026. Nao e um total observado nas
# prestacoes: e o denominador externo que permite medir quanto ja apareceu como
# repasse direto a candidaturas.
# https://www.tse.jus.br/eleicoes/eleicoes-2026-content/prestacao-de-contas/
# fundo-especial-de-financiamento-de-campanha-fefc
FEFC_OFICIAL = {2026: 4_961_519_777.0}
CICLOS_ENCERRADOS = frozenset({2018, 2022})


@dataclass(frozen=True)
class ResumoCiclo:
    status: str
    partial: bool
    observedDirectFefc: float
    officialAllocation: float | None
    coveragePercent: float | None
    coverageBasis: str | None
    resultsAvailable: bool
    seatReferenceYears: tuple[int, ...]

    def json(self) -> dict:
        return asdict(self)


def resumo_ciclo(
    ano: int,
    observado_direto: float,
    *,
    resultados_disponiveis: bool,
    anos_referencia_cadeiras: set[int] | None = None,
) -> ResumoCiclo:
    """Descreve a maturidade do ciclo sem confundir alocacao com receita.

    A cobertura de 2026 compara o FEFC repassado diretamente por partidos a
    candidaturas com a dotacao oficial. Ela nao afirma que a diferenca esteja
    atrasada: recursos podem permanecer no partido, ser devolvidos ou aparecer
    em canais que esta metrica deliberadamente exclui.
    """
    oficial = FEFC_OFICIAL.get(ano)
    cobertura = 100 * observado_direto / oficial if oficial else None
    parcial = ano not in CICLOS_ENCERRADOS
    return ResumoCiclo(
        status="partial" if parcial else "final",
        partial=parcial,
        observedDirectFefc=round(observado_direto, 2),
        officialAllocation=oficial,
        coveragePercent=round(cobertura, 2) if cobertura is not None else None,
        coverageBasis="direct-candidate-receipts / official-allocation" if oficial else None,
        resultsAvailable=resultados_disponiveis,
        seatReferenceYears=tuple(sorted(anos_referencia_cadeiras or set())),
    )
