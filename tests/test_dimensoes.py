import pytest

from fundo_eleitoral.dimensoes import _primeira_existente


def test_escolhe_o_nome_que_o_ciclo_usa():
    # O eleitorado e qt_eleitores_perfil em 2018 e qt_eleitores em 2022/2026.
    assert _primeira_existente({"sg_uf", "qt_eleitores"},
                               ("qt_eleitores", "qt_eleitores_perfil"), "x") == "qt_eleitores"
    assert _primeira_existente({"sg_uf", "qt_eleitores_perfil"},
                               ("qt_eleitores", "qt_eleitores_perfil"), "x") == "qt_eleitores_perfil"


def test_avisa_quando_nenhum_nome_existe():
    # Falhar dizendo quais colunas ha e melhor que devolver zero silenciosamente.
    with pytest.raises(RuntimeError, match="nenhuma de"):
        _primeira_existente({"outra"}, ("qt_eleitores",), "perfil_eleitorado_2030")
