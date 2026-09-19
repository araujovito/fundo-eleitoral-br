"""Peças de SQL compartilhadas pelos recortes de análise.

Existe porque cada recorte novo nasceu copiando a consulta do anterior, e o
mesmo defeito acabou em quatro arquivos: nenhum deles excluía o repasse entre
candidaturas, e a correção precisou ser feita e testada quatro vezes (ADR-010).

Quem escrever um recorte novo monta a CTE de FEFC daqui e herda a definição
correta -- em vez de herdar a consulta de um vizinho, com o defeito que ela
tiver naquele dia.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

# Dataset publico gerado por este projeto; a analise roda sem ingestao local.
HF = "hf://datasets/buscafe/fundo-eleitoral-br/parquet"

# Tudo e string no Parquet por decisao explicita (ADR-004): vr_receita vem como
# texto com virgula decimal.
VALOR = "CAST(replace(vr_receita, ',', '.') AS DOUBLE)"

FONTE_FEFC = "FUNDO ESPECIAL"

# FEFC que chega a uma candidatura vindo de outra ja foi contado quando o
# partido o repassou. O fluxo e enviesado -- 75% dele vai para homens, contra
# 69% do fundo como um todo em 2022 -- entao inclui-lo nao e so inflar o total:
# desloca a composicao medida, sempre no sentido de suavizar a desigualdade que
# a analise quer estimar. Ver ADR-009.
ORIGEM_REPASSE = "Recursos de outros candidatos"


def caminho(raiz: str | Path, ano: int, tabela: str) -> str:
    return f"{raiz}/{ano}/{tabela}.parquet"


def tem_candidaturas_aptas(caminho_cadastro: str) -> bool:
    """Se o ciclo ja teve a situacao da candidatura publicada.

    Em 2026 a coluna vem como '#NE', com os registros ainda sob julgamento:
    filtrar por aptidao ali devolveria vazio em vez de avisar.
    """
    return duckdb.sql(
        f"SELECT count(*) > 0 FROM '{caminho_cadastro}' "
        "WHERE ds_situacao_candidatura ILIKE 'APTO%'"
    ).fetchone()[0]


def clausula_aptidao(caminho_cadastro: str, apenas_aptas: bool, conector: str = "WHERE") -> str:
    """Restricao a candidaturas aptas, vazia quando o filtro nao se aplica.

    `conector` e "WHERE" quando a consulta ainda nao tem clausula e "AND"
    quando ela se soma a uma existente -- os dois casos aparecem no projeto.
    """
    if apenas_aptas and tem_candidaturas_aptas(caminho_cadastro):
        return f"{conector} ds_situacao_candidatura ILIKE 'APTO%'"
    return ""


def cte_fefc(caminho_receitas: str, incluir_repasse_entre_candidatos: bool = False) -> str:
    """CTE `fefc`: uma linha por candidatura, com o FEFC que ela recebeu.

    Soma por `sq_candidato` antes de qualquer outra coisa, para que varios
    repasses a mesma candidatura nao sejam confundidos com varios destinos.
    """
    repasse = (
        "" if incluir_repasse_entre_candidatos
        # IS DISTINCT FROM, ao contrario de <>, tambem preserva linhas cujo
        # campo de origem esteja nulo. Elas nao sao repasse entre candidaturas.
        else f"AND ds_origem_receita IS DISTINCT FROM '{ORIGEM_REPASSE}'"
    )
    return f"""fefc AS (
          SELECT sq_candidato, sum({VALOR}) AS valor
          FROM '{caminho_receitas}'
          WHERE ds_fonte_receita = '{FONTE_FEFC}' {repasse}
          GROUP BY 1
        )"""
