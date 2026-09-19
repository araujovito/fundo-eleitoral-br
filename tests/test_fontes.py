from fundo_eleitoral.fontes import ANOS_ELEICAO, fontes_do_ano, todas_fontes


def test_cada_ano_tem_as_tres_fontes():
    fontes = fontes_do_ano(2022)
    assert len(fontes) == 3
    assert all(f.ano == 2022 for f in fontes)


def test_chaves_sao_unicas_entre_anos():
    chaves = [f.chave for f in todas_fontes()]
    assert len(chaves) == len(set(chaves))


def test_urls_sao_https_do_tse():
    for f in todas_fontes(ANOS_ELEICAO):
        assert f.url.startswith("https://cdn.tse.jus.br/")
        assert f.url.endswith(".zip")


def test_contas_de_partido_usam_orgaos_partidarios():
    # O TSE nao publica "partidos": o nome e "orgaos_partidarios". Errar isso
    # rende 404, que e facil de confundir com bloqueio do CDN (403).
    partidos = next(f for f in fontes_do_ano(2022) if "orgaos" in f.chave)
    assert "orgaos_partidarios" in partidos.url


def test_despesas_sao_sempre_qualificadas():
    # Nao existe "despesas_x" solto: contratada != paga.
    for f in todas_fontes():
        for t in f.tabelas:
            if t.startswith("despesas"):
                assert t.startswith(("despesas_contratadas", "despesas_pagas")), t


def test_arquivo_de_monta_nome_brasil():
    f = next(f for f in fontes_do_ano(2018) if f.chave.startswith("contas_candidatos"))
    assert f.arquivo_de("receitas_candidatos") == "receitas_candidatos_2018_BRASIL.csv"


def test_cartao_do_dataset_menciona_as_armadilhas():
    from fundo_eleitoral.publicacao import montar_cartao

    cartao = montar_cartao((2018, 2022))
    # O cartao e a unica documentacao que acompanha o dado fora deste repo;
    # se estas ressalvas sairem dele, quem consumir soma errado.
    assert "despesas_pagas" in cartao
    assert "dupla contagem" in cartao
    assert "2018, 2022" in cartao


def test_piso_e_o_maior_entre_30_e_a_proporcao():
    from fundo_eleitoral.analise import piso_do_partido

    # A regra nao e um 30% fixo: quem lanca mais mulheres deve repassar mais.
    assert piso_do_partido(22.0) == 30.0
    assert piso_do_partido(37.1) == 37.1


def test_partido_acima_de_30_pode_estar_irregular():
    from fundo_eleitoral.analise import LinhaPartido

    # Caso real do PT em 2022: 27,2% repassado com 37,1% de candidaturas.
    pt = LinhaPartido("PT", 546.7, 27.2, 37.1)
    assert not pt.cumpre
    # E o caso que o piso fixo de 30% esconderia:
    mdb = LinhaPartido("MDB", 378.0, 31.7, 34.2)
    assert mdb.pct_repassado > 30 and not mdb.cumpre
