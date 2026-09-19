import duckdb
import pytest

from fundo_eleitoral.fluxos import CANDIDATURAS, DIRETORIO, FONTE, fluxos_fefc, grafo_dot


def _gravar_base_sintetica(raiz):
    ano = raiz / "2022"
    ano.mkdir()
    con = duckdb.connect()
    con.sql("""
        CREATE TABLE orgaos AS SELECT * FROM (VALUES
          ('P', 'Nacional', 'BR', '001', 'P', 'Federal (Estadual/Distrital)', 'SP', '002', 'FUNDO ESPECIAL', '100,00'),
          ('P', 'Nacional', 'BR', '001', 'P', 'Federal (Estadual/Distrital)', 'SP', '002', 'FUNDO ESPECIAL', '50,00'),
          ('Q', 'Nacional', 'BR', '003', 'Q', 'Municipal', 'RJ', '004', 'FUNDO ESPECIAL', '70,00'),
          ('P', '#NULO', 'SP', '001', 'P', 'Municipal', 'SP', '005', 'FUNDO ESPECIAL', '999,00'),
          ('P', 'Nacional', 'BR', '001', 'P', 'Municipal', 'SP', '005', 'OUTROS RECURSOS', '999,00')
        ) t(sg_partido_doador, ds_esfera_partidaria_doador, sg_uf_doador,
            nr_cpf_cnpj_doador, sg_partido, ds_esfera_partidaria, sg_uf,
            nr_cnpj_prestador_conta, ds_fonte_receita, vr_receita)
    """)
    con.sql("""
        CREATE TABLE candidatos AS SELECT * FROM (VALUES
          ('P', 'Federal (Estadual/Distrital)', 'SP', 'P', 'SP', 'DEPUTADO FEDERAL', 'FUNDO ESPECIAL', '200,00'),
          ('P', 'Federal (Estadual/Distrital)', 'SP', 'P', 'SP', 'DEPUTADO FEDERAL', 'FUNDO ESPECIAL', '50,00'),
          ('Q', 'Nacional', 'BR', 'Q', 'RJ', 'SENADOR', 'FUNDO ESPECIAL', '80,00'),
          ('P', '#NULO', 'SP', 'P', 'SP', 'DEPUTADO FEDERAL', 'FUNDO ESPECIAL', '999,00')
        ) t(sg_partido_doador, ds_esfera_partidaria_doador, sg_uf_doador,
            sg_partido, sg_uf, ds_cargo, ds_fonte_receita, vr_receita)
    """)
    con.execute(f"COPY orgaos TO '{ano / 'receitas_orgaos_partidarios.parquet'}' (FORMAT PARQUET)")
    con.execute(f"COPY candidatos TO '{ano / 'receitas_candidatos.parquet'}' (FORMAT PARQUET)")
    con.close()


def test_monta_arestas_sem_somar_cadeia_como_recurso_novo(tmp_path):
    _gravar_base_sintetica(tmp_path)
    linhas = fluxos_fefc(2022, raiz=tmp_path, minimo_reais=0)

    assert len(linhas) == 4
    nacional_para_sp = next(
        linha for linha in linhas
        if linha.origem.partido == "P" and linha.destino.tipo == DIRETORIO
    )
    estadual_para_candidaturas = next(
        linha for linha in linhas
        if linha.origem.partido == "P" and linha.destino.tipo == CANDIDATURAS
    )
    assert nacional_para_sp.total == 150
    assert nacional_para_sp.n_lancamentos == 2
    assert estadual_para_candidaturas.total == 250
    assert estadual_para_candidaturas.destino.cargo == "DEPUTADO FEDERAL"


def test_filtra_partido_e_tipo_de_destino(tmp_path):
    _gravar_base_sintetica(tmp_path)
    linhas = fluxos_fefc(
        2022, raiz=tmp_path, partidos=("p",), incluir_candidaturas=False, minimo_reais=0
    )

    assert len(linhas) == 1
    assert linhas[0].origem.partido == "P"
    assert linhas[0].destino.tipo == DIRETORIO


def test_entrada_do_fundo_no_mesmo_cnpj_nao_vira_autoelo(tmp_path):
    _gravar_base_sintetica(tmp_path)
    caminho = tmp_path / "2022" / "receitas_orgaos_partidarios.parquet"
    con = duckdb.connect()
    con.sql("""
        CREATE TABLE entrada AS SELECT * FROM (VALUES
          ('P', 'Nacional', 'BR', '001', 'P', 'Nacional', 'BR', '001', 'FUNDO ESPECIAL', '300,00')
        ) t(sg_partido_doador, ds_esfera_partidaria_doador, sg_uf_doador,
            nr_cpf_cnpj_doador, sg_partido, ds_esfera_partidaria, sg_uf,
            nr_cnpj_prestador_conta, ds_fonte_receita, vr_receita)
    """)
    # DuckDB nao permite inserir diretamente num Parquet; recriamos o arquivo
    # com a linha adicional para testar a convenção contábil do TSE.
    con.execute(f"CREATE TABLE orgaos AS SELECT * FROM read_parquet('{caminho}')")
    con.execute("INSERT INTO orgaos SELECT * FROM entrada")
    novo = caminho.with_name("orgaos_com_entrada.parquet")
    con.execute(f"COPY orgaos TO '{novo}' (FORMAT PARQUET)")
    con.close()
    novo.replace(caminho)

    entrada = next(
        linha for linha in fluxos_fefc(2022, raiz=tmp_path, minimo_reais=0)
        if linha.origem.tipo == FONTE
    )
    assert entrada.total == 300
    assert entrada.destino.esfera == "nacional"


def test_exige_algum_destino(tmp_path):
    _gravar_base_sintetica(tmp_path)
    with pytest.raises(ValueError, match="ao menos um"):
        fluxos_fefc(2022, raiz=tmp_path, incluir_candidaturas=False, incluir_diretorios=False)


def test_saida_dot_preserva_nos_e_valor_da_aresta(tmp_path):
    _gravar_base_sintetica(tmp_path)
    dot = grafo_dot(fluxos_fefc(2022, raiz=tmp_path, minimo_reais=100))
    assert dot.startswith("digraph fefc {")
    assert "nacional/P/BR" in dot
    assert "R$ 150.00" in dot
