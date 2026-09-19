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

Ingestão completa nos três ciclos, dados publicados em
[huggingface.co/datasets/buscafe/fundo-eleitoral-br](https://huggingface.co/datasets/buscafe/fundo-eleitoral-br)
(27 tabelas, 364 MB, público). Dois recortes de análise prontos: cota de gênero
e concentração x pulverização do FEFC.

### Achado: a cota de gênero não é uma regra de 30%

| ciclo | FEFC | a candidaturas femininas |
|---|---|---|
| 2018 | R$ 1,83 bi | 26,7% |
| 2022 | R$ 4,90 bi | 30,8% |
| 2026 (parcial) | R$ 4,68 bi | 34,5% |

O agregado sugere cumprimento a partir de 2022. Mas a regra (ADI 5617) exige
repasse **proporcional** às candidaturas femininas do partido, com 30% apenas
como piso. Medido assim, **15 dos 24 partidos analisados descumpriram em
2022** — e 9 deles estavam acima dos 30%, portanto invisíveis sob a leitura
simplificada. O PT repassou 27,2% com 37,1% de candidaturas; o MDB, 31,7%
com 34,2%.

Reproduz com `python -m fundo_eleitoral.analise` — lê direto do Hugging Face,
sem ingestão local. Ver
[docs/decisoes.md](docs/decisoes.md) para as decisões de arquitetura e as
pendências conhecidas.

### Achado: o FEFC ficou mais pulverizado nas chapas federais

Nas células `partido x UF` para deputado federal com ao menos 10 candidaturas e
R$ 1 milhão de fundo, o Gini mediano caiu de **0,761 em 2018 para 0,629 em
2022**. A cobertura mediana subiu de 73,3% para 92,1%, enquanto a parcela dos
10% mais financiados caiu de 71,3% para 51,4%.

O retrato parcial de 2026 mantém o movimento, mas ainda não é comparável a uma
prestação final. Veja método, exemplos e ressalvas em
[docs/concentracao.md](docs/concentracao.md). Reproduz com:

```bash
python -m fundo_eleitoral.concentracao --ano 2022 --por uf cargo \
  --cargo "DEPUTADO FEDERAL" --minimo-milhoes 1 --minimo-candidaturas 10
```

## Arquitetura em uma frase

Ingestão baixa os ZIPs do TSE e escreve Parquet; a análise só lê Parquet, via
DuckDB, sem banco servidor. As duas etapas são deliberadamente separadas —
o porquê está em [ADR-001](docs/decisoes.md#adr-001--ingestão-e-análise-são-etapas-separadas).

```
fontes.py      catálogo de URLs e dialeto dos CSVs do TSE
ingestao.py    baixa → extrai → converte para Parquet  (roda raro)
publicacao.py  sobe os Parquet para um dataset público no Hugging Face
analise.py     consultas sobre os Parquet (lê do HF, não baixa nada)
concentracao.py mede concentração do FEFC por partido, UF e cargo
dados/         ignorado pelo git (ADR-002)
```

## Rodando

O projeto foi desenhado para rodar em ambiente efêmero na nuvem (Codespaces ou
Colab), sem ocupar disco local. Há um `.devcontainer` pronto.

```bash
make verificar                              # testa as 9 URLs sem baixar nada
REPO=usuario/fundo-eleitoral-br make tudo   # ingere e publica o ciclo
make teste

make ingerir ANO=2018                       # um ciclo especifico
```

`make tudo` encadeia ingestão e publicação de propósito: o Parquet não pode
ficar só na máquina efêmera ([ADR-007](docs/decisoes.md)). Para publicar é
preciso uma conta no Hugging Face e um token de escrita, via
`huggingface-cli login` ou `HF_TOKEN`.

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
