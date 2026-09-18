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


def test_prefixos_carregam_o_ano():
    for f in fontes_do_ano(2018):
        assert all("2018" in p for p in f.prefixos_csv)
