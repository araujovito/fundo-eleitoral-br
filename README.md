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

Ingestão implementada e com as 9 fontes dos três ciclos verificadas
(2018, 2022 e 2026 — este último ainda em prestação parcial). Análise
ainda não. Ver
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
make verificar   # testa as 9 URLs sem baixar nada
make ingerir     # baixa e converte o ciclo de 2022 (~400 MB de download)
make teste
```

> O CDN do TSE fica atrás de um bot manager que recusa clientes programáticos
> pela impressão digital do TLS — `httpx` e `curl` levam 403 em todo o domínio,
> mesmo com User-Agent de navegador. Por isso a ingestão usa `curl_cffi`
> ([ADR-005](docs/decisoes.md)). Um **403** indica esse bloqueio; um **404**
> indica nome de arquivo errado no catálogo.

## Fontes

Todas do [portal de dados abertos do TSE](https://dadosabertos.tse.jus.br):
prestação de contas eleitorais de candidatos e de partidos, consulta de
candidaturas e resultados por município e zona.

## Licença

MIT para o código. Os dados são públicos e pertencem ao TSE.
