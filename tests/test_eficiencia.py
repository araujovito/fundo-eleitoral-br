import duckdb
import pytest

from fundo_eleitoral.eficiencia import ELEITO, NAO_ELEITO, eficiencia_eleitoral


def _gravar_base_sintetica(raiz):
    ano = raiz / "2022"
    ano.mkdir()
    dimensoes = raiz / "dimensoes"
    dimensoes.mkdir()
    con = duckdb.connect()
    con.sql("""
        CREATE TABLE candidaturas AS SELECT * FROM (VALUES
          ('c1', 'P', 'SP', 'DEPUTADO FEDERAL', 'ELEITO POR QP', 'APTO', 'ELEIÇÃO ORDINÁRIA'),
          ('c2', 'P', 'SP', 'DEPUTADO FEDERAL', 'NÃO ELEITO', 'APTO', 'ELEIÇÃO ORDINÁRIA'),
          ('c3', 'P', 'SP', 'DEPUTADO FEDERAL', 'NÃO ELEITO', 'APTO', 'ELEIÇÃO ORDINÁRIA'),
          ('c4', 'Q', 'RJ', 'SENADOR', 'NÃO ELEITO', 'INAPTO', 'ELEIÇÃO ORDINÁRIA'),
          ('c5', 'P', 'SP', 'DEPUTADO FEDERAL', 'ELEITO', 'APTO', 'ELEIÇÃO SUPLEMENTAR')
        ) t(sq_candidato, sg_partido, sg_uf, ds_cargo, ds_sit_tot_turno,
            ds_situacao_candidatura, nm_tipo_eleicao)
    """)
    con.sql("""
        CREATE TABLE receitas AS SELECT * FROM (VALUES
          ('c1', 'FUNDO ESPECIAL', 'Recursos de partido político', '100,00'),
          ('c2', 'FUNDO ESPECIAL', 'Recursos de partido político', '100,00'),
          ('c3', 'FUNDO ESPECIAL', 'Recursos de partido político', '50,00'),
          ('c3', 'FUNDO ESPECIAL', 'Recursos de outros candidatos', '999,00'),
          ('c4', 'FUNDO ESPECIAL', 'Recursos de partido político', '20,00')
        ) t(sq_candidato, ds_fonte_receita, ds_origem_receita, vr_receita)
    """)
    con.sql("""
        CREATE TABLE votos AS SELECT * FROM (VALUES
          (2022, 'c1', 1, 20), (2022, 'c2', 1, 10), (2022, 'c4', 1, 5)
        ) t(ano, sq_candidato, nr_turno, qt_votos)
    """)
    con.execute(f"COPY candidaturas TO '{ano / 'consulta_cand.parquet'}' (FORMAT PARQUET)")
    con.execute(f"COPY receitas TO '{ano / 'receitas_candidatos.parquet'}' (FORMAT PARQUET)")
    con.execute(f"COPY votos TO '{dimensoes / 'votos.parquet'}' (FORMAT PARQUET)")
    con.close()
    return dimensoes / "votos.parquet"


def test_calcula_reais_por_voto_por_perfil_e_exclui_repasse(tmp_path):
    dimensao = _gravar_base_sintetica(tmp_path)
    linhas = eficiencia_eleitoral(2022, raiz=tmp_path, dimensao=dimensao)
    por_perfil = {linha.perfil: linha for linha in linhas if linha.partido == "P"}

    assert por_perfil[ELEITO].metricas.total_fefc == 100
    assert por_perfil[ELEITO].metricas.reais_por_voto == pytest.approx(5)
    assert por_perfil[NAO_ELEITO].metricas.total_fefc == 150
    assert por_perfil[NAO_ELEITO].metricas.total_votos == 10
    assert por_perfil[NAO_ELEITO].metricas.reais_por_voto == pytest.approx(15)


def test_filtros_e_grupo_sem_votos(tmp_path):
    dimensao = _gravar_base_sintetica(tmp_path)
    linhas = eficiencia_eleitoral(
        2022, raiz=tmp_path, dimensao=dimensao, por=("partido",), apenas_aptas=True,
        cargos=("DEPUTADO FEDERAL",), ufs=("SP",),
    )
    linha = linhas[0]
    assert linha.metricas.total_fefc == 250
    assert linha.metricas.total_votos == 30
    assert linha.metricas.n_candidaturas == 3
    assert linha.metricas.n_eleitas == 1


def test_rejeita_dimensao_invalida_e_ano_sem_resultado(tmp_path):
    dimensao = _gravar_base_sintetica(tmp_path)
    with pytest.raises(ValueError, match="dimensoes invalidas"):
        eficiencia_eleitoral(2022, raiz=tmp_path, dimensao=dimensao, por=("raca",))
    with pytest.raises(ValueError, match="nao ha resultados"):
        eficiencia_eleitoral(2018, raiz=tmp_path, dimensao=dimensao)
