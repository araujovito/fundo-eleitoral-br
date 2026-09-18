# fundo-eleitoral-br

Como os partidos brasileiros **alocam** o Fundo Especial de Financiamento de
Campanha (FEFC) e o Fundo Partidário — ciclos de 2018, 2022 e 2026, a partir dos
dados abertos do TSE.

## A pergunta

Quanto cada partido gastou é dado público e pouco informativo. A pergunta que
este projeto persegue é *onde* cada partido apostou o dinheiro:

- **Concentração x pulverização** — poucos puxadores de voto ou muitos
  candidatos para maximizar o quociente eleitoral?
- **Incumbentes x estreantes** — o fundo financia renovação ou reeleição?
- **Prioridade geográfica** — quais UFs recebem acima do seu peso no eleitorado?
- **Cotas de gênero e raça** — o mínimo de 30% para candidaturas femininas e a
  proporcionalidade racial são cumpridos no repasse ou apenas no registro?
- **Eficiência** — reais por voto obtido, por partido e por perfil de candidato.

## Estado atual

Etapa de ingestão implementada; análise ainda não. Ver
[docs/decisoes.md](docs/decisoes.md) para as decisões de arquitetura e as
pendências conhecidas.

## Arquitetura em uma frase

Ingestão baixa os ZIPs do TSE e escreve Parquet; a análise só lê Parquet, via
DuckDB, sem banco servidor. As duas etapas são deliberadamente separadas —
o porquê está em [ADR-001](docs/decisoes.md#adr-001--ingestão-e-análise-são-etapas-separadas).

```
fontes.py     catálogo de URLs e dialeto dos CSVs do TSE
ingestao.py   baixa → extrai → converte para Parquet  (roda raro)
dados/        ignorado pelo git; Parquet publicado no Hugging Face (ADR-002)
```

## Rodando

O projeto foi desenhado para rodar em ambiente efêmero na nuvem (Codespaces ou
Colab), sem ocupar disco local. Há um `.devcontainer` pronto.

```bash
pip install -e '.[dev]'

# 1. confirmar que as URLs do catálogo respondem neste ambiente
python -m fundo_eleitoral.ingestao --verificar --ano 2022

# 2. baixar e converter um ciclo
python -m fundo_eleitoral.ingestao --ano 2022
```

> O CDN do TSE responde **403 a partir de algumas faixas de IP residenciais** —
> o domínio inteiro, não só o arquivo. Se `--verificar` falhar em tudo, o
> problema é a rede de saída, não o catálogo. De dentro do Codespaces costuma
> passar.

## Fontes

Todas do [portal de dados abertos do TSE](https://dadosabertos.tse.jus.br):
prestação de contas eleitorais de candidatos e de partidos, consulta de
candidaturas e resultados por município e zona.

## Licença

MIT para o código. Os dados são públicos e pertencem ao TSE.
