import duckdb
import pytest

from fundo_eleitoral.renovacao import (
    CANDIDATO_RECORRENTE,
    CPF_INVALIDO,
    ELEITO_OUTRO_CARGO,
    INCUMBENTE_MESMO_CARGO,
    NOVO_NO_RECORTE,
    distribuicao_renovacao,
)


def _gravar_base_sintetica(raiz):
    anterior = raiz / "2018"
    atual = raiz / "2022"
    anterior.mkdir()
    atual.mkdir()
    con = duckdb.connect()
    con.sql("""
        CREATE TABLE cand_anterior AS SELECT * FROM (VALUES
          ('p1', '11111111111', 'DEPUTADO FEDERAL', 'ELEITO POR QP', 'ELEIÇÃO ORDINÁRIA'),
          ('p2', '22222222222', 'DEPUTADO ESTADUAL', 'ELEITO POR MÉDIA', 'ELEIÇÃO ORDINÁRIA'),
          ('p3', '33333333333', 'DEPUTADO FEDERAL', 'NÃO ELEITO', 'ELEIÇÃO ORDINÁRIA'),
          ('p4', '-4', 'DEPUTADO FEDERAL', 'ELEITO POR QP', 'ELEIÇÃO ORDINÁRIA'),
          ('p5', '44444444444', 'DEPUTADO FEDERAL', 'ELEITO', 'ELEIÇÃO SUPLEMENTAR')
        ) t(sq_candidato, nr_cpf_candidato, ds_cargo, ds_sit_tot_turno,
            nm_tipo_eleicao)
    """)
    con.sql("""
        CREATE TABLE cand_atual AS SELECT * FROM (VALUES
          ('c1', 'P', 'SP', 'DEPUTADO FEDERAL', '11111111111', 'APTO', 'ELEIÇÃO ORDINÁRIA'),
          ('c2', 'P', 'SP', 'DEPUTADO FEDERAL', '22222222222', 'APTO', 'ELEIÇÃO ORDINÁRIA'),
          ('c3', 'P', 'SP', 'DEPUTADO FEDERAL', '33333333333', 'INAPTO', 'ELEIÇÃO ORDINÁRIA'),
          ('c4', 'P', 'SP', 'DEPUTADO FEDERAL', '55555555555', 'APTO', 'ELEIÇÃO ORDINÁRIA'),
          ('c5', 'P', 'SP', 'DEPUTADO FEDERAL', '-4', 'APTO', 'ELEIÇÃO ORDINÁRIA'),
          ('c6', 'P', 'SP', 'DEPUTADO FEDERAL', '44444444444', 'APTO', 'ELEIÇÃO ORDINÁRIA'),
          ('c7', 'P', 'RJ', 'DEPUTADO FEDERAL', '66666666666', 'APTO', 'ELEIÇÃO ORDINÁRIA'),
          ('c8', 'Q', 'SP', 'DEPUTADO ESTADUAL', '77777777777', 'APTO', 'ELEIÇÃO ORDINÁRIA'),
          ('c9', 'P', 'SP', 'DEPUTADO FEDERAL', '88888888888', 'APTO', 'ELEIÇÃO SUPLEMENTAR')
        ) t(sq_candidato, sg_partido, sg_uf, ds_cargo, nr_cpf_candidato,
            ds_situacao_candidatura, nm_tipo_eleicao)
    """)
    con.sql("""
        CREATE TABLE rec AS SELECT * FROM (VALUES
          ('c1', 'FUNDO ESPECIAL', '60,00'),
          ('c1', 'FUNDO ESPECIAL', '40,00'),
          ('c2', 'FUNDO ESPECIAL', '50,00'),
          ('c3', 'FUNDO ESPECIAL', '25,00'),
          ('c4', 'FUNDO ESPECIAL', '10,00'),
          ('c5', 'FUNDO ESPECIAL', '5,00'),
          ('c6', 'FUNDO ESPECIAL', '4,00'),
          ('c8', 'FUNDO ESPECIAL', '20,00'),
          ('c4', 'OUTROS RECURSOS', '999,00')
        ) t(sq_candidato, ds_fonte_receita, vr_receita)
    """)
    con.execute(f"COPY cand_anterior TO '{anterior / 'consulta_cand.parquet'}' (FORMAT PARQUET)")
    con.execute(f"COPY cand_atual TO '{atual / 'consulta_cand.parquet'}' (FORMAT PARQUET)")
    con.execute(f"COPY rec TO '{atual / 'receitas_candidatos.parquet'}' (FORMAT PARQUET)")
    con.close()


def test_classifica_historico_e_preserva_todo_o_fefc(tmp_path):
    _gravar_base_sintetica(tmp_path)

    linhas = distribuicao_renovacao(
        2022,
        raiz=tmp_path,
        cargos=("deputado federal",),
    )
    por_perfil = {linha.perfil: linha for linha in linhas}

    assert por_perfil[INCUMBENTE_MESMO_CARGO].metricas.total_fefc == 100
    assert por_perfil[ELEITO_OUTRO_CARGO].metricas.total_fefc == 50
    assert por_perfil[CANDIDATO_RECORRENTE].metricas.total_fefc == 25
    assert por_perfil[NOVO_NO_RECORTE].metricas.total_fefc == 14
    assert por_perfil[CPF_INVALIDO].metricas.total_fefc == 5
    assert sum(x.metricas.total_fefc for x in linhas) == 194


def test_novo_no_recorte_inclui_zeros_e_ignora_suplementar_anterior(tmp_path):
    _gravar_base_sintetica(tmp_path)

    novo = next(
        linha for linha in distribuicao_renovacao(2022, raiz=tmp_path)
        if linha.partido == "P" and linha.perfil == NOVO_NO_RECORTE
    )

    assert novo.metricas.n_candidaturas == 3
    assert novo.metricas.n_financiadas == 2
    assert novo.metricas.cobertura_pct == pytest.approx(200 / 3)
    assert novo.metricas.media_por_candidatura == pytest.approx(14 / 3)
    assert novo.metricas.media_por_financiada == 7


def test_percentuais_usam_total_do_grupo(tmp_path):
    _gravar_base_sintetica(tmp_path)

    linhas = distribuicao_renovacao(2022, raiz=tmp_path, cargos=("DEPUTADO FEDERAL",))

    assert sum(x.metricas.pct_fefc for x in linhas) == pytest.approx(100)
    assert sum(x.metricas.pct_candidaturas for x in linhas) == pytest.approx(100)
    incumbente = next(x for x in linhas if x.perfil == INCUMBENTE_MESMO_CARGO)
    assert incumbente.metricas.pct_fefc == pytest.approx(100 / 194 * 100)
    assert incumbente.metricas.pct_candidaturas == pytest.approx(100 / 7)
    assert incumbente.metricas.indice_alocacao == pytest.approx((100 / 194 * 100) / (100 / 7))


def test_filtros_de_aptidao_uf_e_cargo(tmp_path):
    _gravar_base_sintetica(tmp_path)

    linhas = distribuicao_renovacao(
        2022,
        raiz=tmp_path,
        por=(),
        apenas_aptas=True,
        cargos=("DEPUTADO FEDERAL",),
        ufs=("SP",),
    )

    assert all(x.partido is None and x.uf is None and x.cargo is None for x in linhas)
    assert CANDIDATO_RECORRENTE not in {x.perfil for x in linhas}
    assert sum(x.metricas.n_candidaturas for x in linhas) == 5


def test_rejeita_ano_sem_ciclo_anterior_e_dimensao_invalida(tmp_path):
    with pytest.raises(ValueError, match="ciclo anterior"):
        distribuicao_renovacao(2018, raiz=tmp_path)
    with pytest.raises(ValueError, match="dimensoes invalidas"):
        distribuicao_renovacao(2022, raiz=tmp_path, por=("genero",))
