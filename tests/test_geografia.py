import duckdb
import pytest

from fundo_eleitoral.geografia import prioridade_geografica


def _gravar_base_sintetica(raiz):
    ano = raiz / "2022"
    ano.mkdir()
    dimensoes = raiz / "dimensoes"
    dimensoes.mkdir()
    con = duckdb.connect()
    con.sql("""
        CREATE TABLE candidaturas AS SELECT * FROM (VALUES
          ('sp', 'P', 'SP', 'DEPUTADO FEDERAL', 'APTO', 'ELEIÇÃO ORDINÁRIA'),
          ('rj', 'P', 'RJ', 'DEPUTADO FEDERAL', 'APTO', 'ELEIÇÃO ORDINÁRIA'),
          ('df', 'P', 'DF', 'DEPUTADO FEDERAL', 'APTO', 'ELEIÇÃO ORDINÁRIA'),
          ('br', 'P', 'BR', 'PRESIDENTE', 'APTO', 'ELEIÇÃO ORDINÁRIA'),
          ('inapta', 'P', 'SP', 'DEPUTADO FEDERAL', 'INAPTO', 'ELEIÇÃO ORDINÁRIA')
        ) t(sq_candidato, sg_partido, sg_uf, ds_cargo, ds_situacao_candidatura,
            nm_tipo_eleicao)
    """)
    con.sql("""
        CREATE TABLE receitas AS SELECT * FROM (VALUES
          ('sp', 'FUNDO ESPECIAL', 'Recursos de partido político', '100,00'),
          ('rj', 'FUNDO ESPECIAL', 'Recursos de partido político', '100,00'),
          ('df', 'FUNDO ESPECIAL', 'Recursos de partido político', '200,00'),
          ('br', 'FUNDO ESPECIAL', 'Recursos de partido político', '50,00'),
          ('sp', 'FUNDO ESPECIAL', 'Recursos de outros candidatos', '999,00'),
          ('inapta', 'FUNDO ESPECIAL', 'Recursos de partido político', '50,00')
        ) t(sq_candidato, ds_fonte_receita, ds_origem_receita, vr_receita)
    """)
    outras_ufs = (
        "AC", "AL", "AM", "AP", "BA", "CE", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB",
        "PE", "PI", "PR", "RN", "RO", "RR", "RS", "SC", "SE", "TO",
    )
    eleitorado = {uf: 0 for uf in outras_ufs}
    eleitorado.update({"SP": 1000, "RJ": 500, "DF": 500})
    valores = ", ".join(f"(2022, '{uf}', {n})" for uf, n in eleitorado.items())
    con.sql(f"CREATE TABLE eleitorado AS SELECT * FROM (VALUES {valores}) t(ano, sg_uf, qt_eleitores)")
    con.execute(f"COPY candidaturas TO '{ano / 'consulta_cand.parquet'}' (FORMAT PARQUET)")
    con.execute(f"COPY receitas TO '{ano / 'receitas_candidatos.parquet'}' (FORMAT PARQUET)")
    con.execute(f"COPY eleitorado TO '{dimensoes / 'eleitorado.parquet'}' (FORMAT PARQUET)")
    con.close()
    return dimensoes / "eleitorado.parquet"


def test_compara_fefc_ao_eleitorado_e_exclui_br_e_repasses(tmp_path):
    dimensao = _gravar_base_sintetica(tmp_path)
    linhas = prioridade_geografica(
        2022, raiz=tmp_path, dimensao=dimensao, apenas_aptas=True
    )
    por_uf = {linha.uf: linha for linha in linhas}

    assert por_uf["DF"].metricas.total_fefc == 200
    assert por_uf["DF"].metricas.pct_fefc == pytest.approx(50)
    assert por_uf["DF"].metricas.pct_eleitorado == pytest.approx(25)
    assert por_uf["DF"].metricas.indice_prioridade == pytest.approx(2)
    assert por_uf["SP"].metricas.indice_prioridade == pytest.approx(0.5)
    assert sum(linha.metricas.total_fefc for linha in linhas) == 400
    assert "BR" not in por_uf


def test_recorte_por_partido_e_aptidao(tmp_path):
    dimensao = _gravar_base_sintetica(tmp_path)
    linhas = prioridade_geografica(2022, raiz=tmp_path, dimensao=dimensao,
                                   por_partido=True, apenas_aptas=True)
    assert {linha.partido for linha in linhas} == {"P"}
    assert sum(linha.metricas.total_fefc for linha in linhas) == 400
