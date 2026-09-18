# Decisões de arquitetura

Registro curto do *porquê* de cada escolha. Se alguma premissa cair, a decisão
deve ser revisitada — cada ADR abaixo declara o que a invalidaria.

## ADR-001 — Ingestão e análise são etapas separadas

**Contexto.** Os ZIPs do TSE somam alguns GB por ciclo eleitoral e mudam
raramente (uma vez por publicação). As perguntas de análise, ao contrário,
mudam a cada sessão de trabalho.

**Decisão.** `fundo_eleitoral.ingestao` é a única camada que toca a rede e
escreve volume em disco. Ela produz Parquet e para por aí. Toda análise lê
exclusivamente esses Parquet e nunca baixa nada.

**Por quê.** Juntar as duas coisas significa re-baixar gigabytes a cada restart
de ambiente efêmero (Codespaces hiberna e é descartado após 30 dias parado).
Separadas, um restart custa segundos.

**Invalidaria esta decisão:** o TSE passar a oferecer uma API incremental que
torne o download completo desnecessário.

## ADR-002 — Dados não entram no repositório

**Decisão.** `dados/` está no `.gitignore`. Os Parquet tratados vão para um
dataset no Hugging Face; o repo carrega apenas código e as tabelas de dimensão
pequenas (partidos, UFs), que precisam estar disponíveis para os testes rodarem
sem rede.

**Por quê.** Git versiona mal arquivo binário grande: cada nova publicação do
TSE duplicaria o histórico permanentemente. O Hugging Face versiona dataset com
git-lfs, que é a ferramenta certa para isso, e de quebra torna a análise
reproduzível por terceiros sem precisar refazer a ingestão.

## ADR-003 — DuckDB + Parquet, não Postgres

**Decisão.** Sem banco servidor. DuckDB lendo Parquet, inclusive remoto via
`httpfs`.

**Por quê.** O volume depois da conversão é de centenas de MB, não de dezenas de
GB — cabe confortavelmente em memória em qualquer free tier. Um Postgres aqui
adicionaria container, migrations e credenciais para resolver um problema de
concorrência de escrita que este projeto não tem: a carga é 100% leitura
analítica, exatamente o caso de uso do DuckDB.

**Invalidaria esta decisão:** precisar de escrita concorrente ou de servir as
consultas para uma aplicação multiusuário.

## ADR-004 — Tudo é lido como texto na ingestão

**Decisão.** `infer_schema_length=0`: todo campo vira string no Parquet bruto.

**Por quê.** O schema do TSE não é estável entre anos, e a inferência
automática diverge entre UFs do mesmo ano (uma UF sem nenhuma doação faz a
coluna virar nulo e mudar de tipo), o que quebra o `concat`. Tipagem é decisão
explícita da etapa de transformação, onde ela pode ser testada.

## Pendências conhecidas

- **Catálogo de URLs não verificado.** `fontes.py` segue o padrão publicado
  pelo TSE, mas o domínio responde 403 a partir de algumas faixas de IP
  residenciais. Validar com `--verificar` num ambiente de saída liberada.
- **Nomes de fornecedor vêm sujos.** Mesmo CNPJ aparece com grafias diferentes;
  a normalização é pré-requisito de qualquer análise por fornecedor.
- **Transferências entre diretórios causam dupla contagem.** Somar receita
  ingenuamente infla o total: o repasse nacional → estadual → candidato aparece
  três vezes. Tratar como grafo, não como soma.
