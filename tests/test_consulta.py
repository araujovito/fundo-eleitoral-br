"""O ponto unico de verdade das consultas precisa ser testado como tal."""

from pathlib import Path

import duckdb

from fundo_eleitoral import analise, concentracao, raca, renovacao
from fundo_eleitoral.consulta import ORIGEM_REPASSE, caminho, clausula_aptidao, cte_fefc


def test_cte_exclui_repasse_por_padrao():
    assert ORIGEM_REPASSE in cte_fefc("r.parquet")
    assert "ds_origem_receita IS DISTINCT FROM" in cte_fefc("r.parquet")


def test_cte_com_repasse_nao_filtra_origem():
    assert "ds_origem_receita" not in cte_fefc("r.parquet", True)


def test_cte_preserva_origem_nula_sem_contar_repasse(tmp_path):
    arquivo = tmp_path / "receitas.parquet"
    con = duckdb.connect()
    con.sql("""
        CREATE TABLE rec AS SELECT * FROM (VALUES
          ('1', 'FUNDO ESPECIAL', 'Recursos de partido político', '10,00'),
          ('2', 'FUNDO ESPECIAL', NULL, '20,00'),
          ('3', 'FUNDO ESPECIAL', 'Recursos de outros candidatos', '30,00')
        ) t(sq_candidato, ds_fonte_receita, ds_origem_receita, vr_receita)
    """)
    con.execute(f"COPY rec TO '{arquivo}' (FORMAT PARQUET)")
    con.close()

    total = duckdb.sql(f"WITH {cte_fefc(arquivo)} SELECT sum(valor) FROM fefc").fetchone()[0]
    assert total == 30


def test_clausula_vazia_quando_nao_se_aplica():
    assert clausula_aptidao("qualquer.parquet", apenas_aptas=False) == ""


def test_conector_acompanha_a_consulta():
    # Ha os dois casos no projeto: consulta sem clausula e consulta que ja tem.
    assert cte_fefc("r.parquet").count("WHERE") == 1


def test_caminho_monta_o_parquet_do_ciclo():
    assert caminho("base", 2022, "receitas_candidatos") == \
        "base/2022/receitas_candidatos.parquet"


def test_todos_os_recortes_leem_a_mesma_definicao():
    # O defeito do ADR-009 se espalhou porque cada recorte copiou a consulta do
    # vizinho. Se um modulo voltar a definir a sua propria, este teste avisa.
    for modulo in (analise, concentracao, raca, renovacao):
        fonte = Path(modulo.__file__).read_text(encoding="utf-8")
        assert "_VALOR = " not in fonte, modulo.__name__
        assert "def _base(" not in fonte, modulo.__name__
        assert "ds_fonte_receita = 'FUNDO ESPECIAL'" not in fonte, modulo.__name__
