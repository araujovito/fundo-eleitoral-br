import pytest

from fundo_eleitoral.metodologia import FEFC_OFICIAL, resumo_ciclo


def test_2026_expoe_cobertura_sem_chamar_a_dotacao_de_receita():
    resumo = resumo_ciclo(
        2026,
        4_610_565_650.36,
        resultados_disponiveis=False,
        anos_referencia_cadeiras={2022},
    )

    assert resumo.partial
    assert resumo.status == "partial"
    assert resumo.officialAllocation == FEFC_OFICIAL[2026]
    assert resumo.coveragePercent == pytest.approx(92.93)
    assert resumo.coverageBasis == "direct-candidate-receipts / official-allocation"
    assert not resumo.resultsAvailable
    assert resumo.seatReferenceYears == (2022,)


def test_ciclo_encerrado_nao_inventa_referencia_oficial_ausente():
    resumo = resumo_ciclo(2022, 100.0, resultados_disponiveis=True)

    assert not resumo.partial
    assert resumo.status == "final"
    assert resumo.officialAllocation is None
    assert resumo.coveragePercent is None
