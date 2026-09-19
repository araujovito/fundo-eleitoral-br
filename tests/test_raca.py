import duckdb
import pytest

from fundo_eleitoral.raca import proporcionalidade_racial, total_nacional


def _gravar_base_sintetica(raiz):
    pasta = raiz / "2022"
    pasta.mkdir()
    con = duckdb.connect()
    con.sql("""
        CREATE TABLE cand AS SELECT * FROM (VALUES
          ('1', 'P', 'PRETA', 'APTO', 'ELEIÇÃO ORDINÁRIA'),
          ('1', 'P', 'PRETA', 'APTO', 'ELEIÇÃO ORDINÁRIA'),
          ('2', 'P', 'PARDA', 'APTO', 'ELEIÇÃO ORDINÁRIA'),
          ('3', 'P', 'BRANCA', 'APTO', 'ELEIÇÃO ORDINÁRIA'),
          ('4', 'P', 'NÃO INFORMADO', 'APTO', 'ELEIÇÃO ORDINÁRIA'),
          ('5', 'P', 'PRETA', 'APTO', 'ELEIÇÃO SUPLEMENTAR'),
          ('6', 'P', 'PRETA', 'INAPTO', 'ELEIÇÃO ORDINÁRIA'),
          ('7', 'Q', 'Preta', 'APTO', 'ELEIÇÃO ORDINÁRIA'),
          ('8', 'Q', 'Branca', 'APTO', 'ELEIÇÃO ORDINÁRIA')
        ) t(sq_candidato, sg_partido, ds_cor_raca, ds_situacao_candidatura,
            nm_tipo_eleicao)
    """)
    con.sql("""
        CREATE TABLE rec AS SELECT * FROM (VALUES
          ('1', 'FUNDO ESPECIAL', '20,00'),
          ('1', 'FUNDO ESPECIAL', '20,00'),
          ('2', 'FUNDO ESPECIAL', '10,00'),
          ('3', 'FUNDO ESPECIAL', '50,00'),
          ('5', 'FUNDO ESPECIAL', '999,00'),
          ('6', 'FUNDO ESPECIAL', '100,00'),
          ('7', 'FUNDO ESPECIAL', '20,00'),
          ('8', 'FUNDO ESPECIAL', '80,00'),
          ('2', 'OUTROS RECURSOS', '500,00')
        ) t(sq_candidato, ds_fonte_receita, vr_receita)
    """)
    con.execute(f"COPY cand TO '{pasta / 'consulta_cand.parquet'}' (FORMAT PARQUET)")
    con.execute(f"COPY rec TO '{pasta / 'receitas_candidatos.parquet'}' (FORMAT PARQUET)")
    con.close()


def test_pretas_e_pardas_formam_categoria_negra(tmp_path):
    _gravar_base_sintetica(tmp_path)

    linhas = proporcionalidade_racial(
        2022,
        raiz=tmp_path,
        minimo_reais=1,
        apenas_aptas=True,
    )
    p = next(linha for linha in linhas if linha.partido == "P")

    assert p.fefc_milhoes == pytest.approx(0.0001)
    assert p.pct_candidaturas_negras == 50
    assert p.pct_repassado_negras == 50
    assert p.pct_candidaturas_sem_raca == 25
    assert p.diferenca == 0
    assert p.proporcional


def test_detecta_partido_abaixo_da_proporcao(tmp_path):
    _gravar_base_sintetica(tmp_path)

    q = next(
        linha for linha in proporcionalidade_racial(
            2022,
            raiz=tmp_path,
            minimo_reais=1,
            apenas_aptas=True,
        )
        if linha.partido == "Q"
    )

    assert q.pct_candidaturas_negras == 50
    assert q.pct_repassado_negras == 20
    assert q.diferenca == -30
    assert q.deficit_milhoes == pytest.approx(0.00003)
    assert not q.proporcional


def test_deduplica_cadastro_agrega_repasses_e_exclui_suplementar(tmp_path):
    _gravar_base_sintetica(tmp_path)

    nacional = total_nacional(2022, raiz=tmp_path, apenas_aptas=True)

    assert nacional.fefc_milhoes == pytest.approx(0.0002)
    assert nacional.pct_candidaturas_negras == 50
    assert nacional.pct_repassado_negras == 35
    assert nacional.pct_candidaturas_sem_raca == pytest.approx(100 / 6)


def test_padrao_inclui_inaptas_e_filtro_pode_ser_ligado(tmp_path):
    _gravar_base_sintetica(tmp_path)

    p = next(
        linha for linha in proporcionalidade_racial(
            2022,
            raiz=tmp_path,
            minimo_reais=1,
        )
        if linha.partido == "P"
    )

    assert p.fefc_milhoes == pytest.approx(0.0002)
    assert p.pct_candidaturas_negras == 60
    assert p.pct_repassado_negras == 75

    filtrado = next(
        linha for linha in proporcionalidade_racial(
            2022,
            raiz=tmp_path,
            minimo_reais=1,
            apenas_aptas=True,
        )
        if linha.partido == "P"
    )
    assert filtrado.fefc_milhoes == pytest.approx(0.0001)
