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
