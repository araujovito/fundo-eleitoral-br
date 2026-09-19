# Contexto do projeto

Documento de orientação: por que este projeto existe, onde ele está e para
onde vai. As decisões técnicas e o *porquê* de cada uma estão em
[decisoes.md](decisoes.md); aqui fica o mapa.

Última atualização: 18/09/2026.

## A pergunta

Quanto cada partido gastou é dado público e pouco informativo. A pergunta é
**onde cada partido apostou o dinheiro** do Fundo Eleitoral (FEFC) e do Fundo
Partidário — e o que essa alocação revela da estratégia eleitoral.

O recorte temporal são três ciclos: 2018, 2022 e 2026. O último está em
prestação parcial, com a eleição a poucas semanas, o que permite acompanhar
uma campanha em curso contra uma linha de base histórica.

## O que já existe

**Pipeline completo, em três etapas separadas de propósito** (ADR-001):

```
ingestao.py    baixa os ZIPs do TSE → Parquet          (roda raro)
publicacao.py  Parquet → dataset público no Hugging Face
analise.py     consultas sobre o Parquet               (roda sempre)
```

**Dados publicados:**
[huggingface.co/datasets/buscafe/fundo-eleitoral-br](https://huggingface.co/datasets/buscafe/fundo-eleitoral-br)
— 27 tabelas, 364 MB, público. Nove tabelas por ciclo: receitas e despesas
(contratadas e pagas) de candidaturas e de órgãos partidários, as duas versões
de doador originário, e o cadastro de candidaturas.

A análise lê direto de lá. Quem clonar o repositório reproduz os números sem
refazer a ingestão — que é a parte cara e cheia de armadilhas.

**Primeiro recorte analisado: cota de gênero.** O achado está no
[README](../README.md#achado-a-cota-de-gênero-não-é-uma-regra-de-30). Em
resumo: a regra não é um piso de 30%, é proporcionalidade às candidaturas
femininas com 30% de mínimo, e sob o critério correto 15 dos 24 partidos
descumpriram em 2022 — contra 6 sob a leitura simplificada.

**Segundo recorte: concentração x pulverização.** A análise inclui candidaturas
sem repasse e calcula cobertura, Gini, HHI, número efetivo de recebedores e
participação dos 10% do topo. Nas chapas a deputado federal, o Gini mediano por
partido e UF caiu de 0,761 em 2018 para 0,629 em 2022. Método completo em
[concentracao.md](concentracao.md).

## O que pretendemos fazer

Em ordem de interesse, não necessariamente de execução:

1. **Incumbentes x estreantes.** O fundo financia renovação ou reeleição?
   Exige cruzar `consulta_cand` entre ciclos por CPF.
2. **Proporcionalidade racial.** Mesmo método da cota de gênero, usando
   `ds_cor_raca`, que já vem nas receitas.
3. **Prioridade geográfica.** Quais UFs recebem acima do seu peso no
   eleitorado — e se isso acompanha disputa apertada ou reduto consolidado.
4. **Eficiência.** Reais por voto obtido, por partido e por perfil de
   candidatura. Depende de ingerir os resultados
   (`votacao_candidato_munzona`), ainda fora do catálogo.
5. **O caminho do dinheiro.** Repasse nacional → estadual → candidatura, com
   as tabelas de órgãos partidários e de doador originário. É a parte mais
   difícil e a mais reveladora.

## Armadilhas já mapeadas

Cada uma destas custou tempo ou quase produziu número errado:

- **Arquivos por UF não são partição.** Usar só os `_BRASIL` (ADR-006). Somar
  as UFs descarta a eleição presidencial inteira.
- **`despesas_contratadas` ≠ `despesas_pagas`.** Em 2026 parcial, contratadas
  são o dobro das pagas.
- **Transferências entre diretórios duplicam.** Nacional → estadual →
  candidatura aparece três vezes. Tratar como grafo.
- **Siglas mudam entre ciclos.** `PC do B` em 2022, `PCDOB` em 2026.
  Normalizar antes de agrupar por partido.
- **Campos de 2026 ainda vazios.** `ds_situacao_candidatura` = `#NE`, registros
  sob julgamento. Filtro de aptidão só se aplica quando existe.
- **Nomes de fornecedor vêm sujos.** Mesmo CNPJ com grafias diferentes;
  pré-requisito de qualquer análise por fornecedor.
- **CDN do TSE recusa clientes programáticos** por impressão digital de TLS
  (ADR-005). Um 403 é bloqueio; um 404 é nome de arquivo errado.

## Como rodar

```bash
pip install -e '.[dev]'
python -m fundo_eleitoral.analise     # lê do Hugging Face, não baixa nada
make verificar                        # testa as URLs do TSE
make ingerir ANO=2022                 # refaz a ingestão de um ciclo
make teste
```

Para publicar é preciso credencial da Hugging Face (`HF_TOKEN` ou
`huggingface-cli login`).

## Método

Uma regra que vale para tudo aqui: **conferir o número contra uma referência
externa antes de confiar nele.** O total do FEFC de 2022 calculado a partir de
`ds_fonte_receita` deu R$ 4,90 bi, que é o valor real do fundo naquele ciclo —
é isso que autoriza usar a coluna. Quando não houver âncora externa, dizer
explicitamente que não houve.
