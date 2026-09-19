import math

import duckdb
import pytest

from fundo_eleitoral.concentracao import calcular_metricas, concentracao_fefc


def test_distribuicao_igual_tem_concentracao_minima():
    m = calcular_metricas([25, 25, 25, 25])

    assert m.total == 100
    assert m.n_candidaturas == 4
    assert m.n_financiadas == 4
    assert m.cobertura_pct == 100
    assert m.gini == pytest.approx(0)
    assert m.hhi == pytest.approx(0.25)
    assert m.hhi_normalizado == pytest.approx(0)
    assert m.numero_efetivo == pytest.approx(4)
    assert m.top_1_pct == pytest.approx(25)
    assert m.top_10pct_pct == pytest.approx(25)


def test_zeros_entram_no_gini_e_na_cobertura():
    m = calcular_metricas([0, 0, 100])

    assert m.n_candidaturas == 3
    assert m.n_financiadas == 1
    assert m.cobertura_pct == pytest.approx(100 / 3)
    assert m.gini == pytest.approx(2 / 3)
    assert m.hhi == pytest.approx(1)
    assert m.hhi_normalizado == pytest.approx(1)
    assert m.numero_efetivo == pytest.approx(1)
    assert m.top_10pct_pct == pytest.approx(100)


@pytest.mark.parametrize("valores", [[], [0, 0]])
def test_grupo_sem_fefc_tem_metricas_zeradas(valores):
    m = calcular_metricas(valores)

    assert m.total == 0
    assert m.gini == 0
    assert m.hhi == 0
    assert m.numero_efetivo == 0


@pytest.mark.parametrize("valor", [-1, math.inf, math.nan])
def test_rejeita_valor_invalido(valor):
    with pytest.raises(ValueError, match="finitos e nao negativos"):
        calcular_metricas([valor])


def _gravar_base_sintetica(raiz):
    pasta = raiz / "2022"
    pasta.mkdir()
    con = duckdb.connect()
    con.sql("""
        CREATE TABLE cand AS SELECT * FROM (VALUES
          ('1', 'P', 'SP', 'DEPUTADO FEDERAL', 'APTO'),
          ('1', 'P', 'SP', 'DEPUTADO FEDERAL', 'APTO'),
          ('2', 'P', 'SP', 'DEPUTADO FEDERAL', 'APTO'),
          ('3', 'P', 'RJ', 'DEPUTADO FEDERAL', 'INAPTO'),
          ('4', 'Q', 'SP', 'DEPUTADO FEDERAL', 'APTO')
        ) t(sq_candidato, sg_partido, sg_uf, ds_cargo, ds_situacao_candidatura)
    """)
    con.sql("""
        CREATE TABLE rec AS SELECT * FROM (VALUES
          ('1', 'FUNDO ESPECIAL', 'Recursos de partido político', '60,00'),
          ('1', 'FUNDO ESPECIAL', 'Recursos de partido político', '40,00'),
          ('2', 'FUNDO ESPECIAL', 'Recursos de partido político', '50,00'),
          -- repasse de uma candidatura para outra: os mesmos reais ja contados
          ('2', 'FUNDO ESPECIAL', 'Recursos de outros candidatos', '30,00'),
          ('2', 'OUTROS RECURSOS', 'Recursos de pessoas físicas', '999,00')
        ) t(sq_candidato, ds_fonte_receita, ds_origem_receita, vr_receita)
    """)
    con.execute(f"COPY cand TO '{pasta / 'consulta_cand.parquet'}' (FORMAT PARQUET)")
    con.execute(f"COPY rec TO '{pasta / 'receitas_candidatos.parquet'}' (FORMAT PARQUET)")
    con.close()


def test_consulta_agrega_repasses_deduplica_cadastro_e_inclui_zeros(tmp_path):
    _gravar_base_sintetica(tmp_path)

    linhas = concentracao_fefc(2022, raiz=tmp_path, minimo_reais=1)
    p = next(linha for linha in linhas if linha.partido == "P")

    assert p.metricas.total == 150
    assert p.metricas.n_candidaturas == 3
    assert p.metricas.n_financiadas == 2
    assert p.metricas.cobertura_pct == pytest.approx(200 / 3)


def test_recorte_por_uf_e_filtro_de_aptidao(tmp_path):
    _gravar_base_sintetica(tmp_path)

    linhas = concentracao_fefc(
        2022,
        raiz=tmp_path,
        por=("uf",),
        minimo_reais=1,
        apenas_aptas=True,
    )

    assert [(x.partido, x.uf, x.metricas.n_candidaturas) for x in linhas] == [
        ("P", "SP", 2)
    ]


def test_filtra_cargo_uf_e_tamanho_minimo_do_grupo(tmp_path):
    _gravar_base_sintetica(tmp_path)

    linhas = concentracao_fefc(
        2022,
        raiz=tmp_path,
        minimo_reais=1,
        minimo_candidaturas=3,
        cargos=("deputado federal",),
        ufs=("sp", "rj"),
    )

    assert [(x.partido, x.metricas.n_candidaturas) for x in linhas] == [("P", 3)]

    assert concentracao_fefc(
        2022,
        raiz=tmp_path,
        minimo_reais=1,
        cargos=("GOVERNADOR",),
    ) == []


def test_rejeita_dimensao_invalida(tmp_path):
    with pytest.raises(ValueError, match="dimensoes invalidas"):
        concentracao_fefc(2022, raiz=tmp_path, por=("genero",))


def test_exclui_repasse_entre_candidaturas_por_padrao(tmp_path):
    _gravar_base_sintetica(tmp_path)

    p = next(x for x in concentracao_fefc(2022, raiz=tmp_path, minimo_reais=1)
             if x.partido == "P")
    # Os R$ 30 que a candidatura 2 recebeu de outra candidatura ja haviam sido
    # contados quando o partido os repassou: entram uma vez so.
    assert p.metricas.total == 150


def test_flag_restaura_a_dupla_contagem_para_reconciliar(tmp_path):
    _gravar_base_sintetica(tmp_path)

    p = next(x for x in concentracao_fefc(2022, raiz=tmp_path, minimo_reais=1,
                                          incluir_repasse_entre_candidatos=True)
             if x.partido == "P")
    assert p.metricas.total == 180


def test_repasse_distorce_a_medida_de_desigualdade(tmp_path):
    _gravar_base_sintetica(tmp_path)

    sem = next(x for x in concentracao_fefc(2022, raiz=tmp_path, minimo_reais=1)
               if x.partido == "P")
    com = next(x for x in concentracao_fefc(2022, raiz=tmp_path, minimo_reais=1,
                                            incluir_repasse_entre_candidatos=True)
               if x.partido == "P")
    # A dupla contagem move o Gini, e a direcao depende de quem recebeu o
    # repasse: aqui ele vai para a candidatura menor, entao o partido parece
    # mais igualitario do que e. Se fosse para a maior, pareceria mais
    # concentrado. Nos dois casos a medida deixa de ser interpretavel.
    assert com.metricas.gini < sem.metricas.gini
