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

## ADR-005 — `curl_cffi` em vez de `httpx` para falar com o TSE

**Contexto.** O CDN do TSE fica atrás de um bot manager da Akamai. Requisições
de `httpx` e `curl` recebem 403 em *todo* o domínio, mesmo declarando um
User-Agent de Chrome. Testado de um IP residencial brasileiro e de um
datacenter da Microsoft nos EUA: 403 nos dois. O mesmo arquivo baixa
normalmente por um navegador.

**Decisão.** Usar `curl_cffi` com `impersonate="chrome"`, que reproduz o
handshake TLS do navegador.

**Por quê.** A classificação é feita pela impressão digital do TLS, não pelo
cabeçalho — por isso trocar o User-Agent não resolve. Confirmado: mesma
máquina, mesma URL, `httpx` → 403, `curl_cffi` → 206 com os bytes do ZIP.

Não há contorno de autenticação ou de paywall aqui: os dados são públicos por
lei e o próprio portal oferece o link de download direto. O que se está
contornando é uma heurística que classifica erroneamente um cliente
programático legítimo.

**Efeito colateral útil:** com o CDN acessível, um 404 passou a significar
"nome de arquivo errado" em vez de se confundir com o 403 do bloqueio — foi
assim que o ADR-006 apareceu.

## ADR-006 — Ingerir apenas os arquivos `_BRASIL`

**Contexto.** Cada ZIP traz, por tabela, 26 CSVs por UF **mais** um
`_BRASIL.csv`. A leitura natural é que o `_BRASIL` seja a concatenação dos
outros. Não é.

**Medido em `receitas_candidatos_2022`:**

| | linhas |
|---|---|
| soma dos 26 arquivos de UF | 271.352 |
| `_BRASIL` sozinho | 674.944 |

Por UF os números batem exatamente (SP: 40.138 nos dois). A diferença são
393.016 linhas com `SG_UF = 'BR'` — as candidaturas de âmbito nacional, ou seja
a eleição presidencial — que não aparecem em arquivo de UF nenhum. O DF também
não tem arquivo próprio.

**Decisão.** Ler só o `_BRASIL` de cada tabela.

**Por quê.** Concatenar as UFs descartaria 58% das linhas de receita, incluindo
a disputa presidencial inteira. E concatenar UFs *mais* `_BRASIL`, que era o que
a primeira versão do código fazia por casar nome com prefixo, duplicaria tudo
que já está no consolidado.

## Pendências conhecidas

- **Nomes de fornecedor vêm sujos.** Mesmo CNPJ aparece com grafias diferentes;
  a normalização é pré-requisito de qualquer análise por fornecedor.
- **Transferências entre diretórios causam dupla contagem.** Somar receita
  ingenuamente infla o total: o repasse nacional → estadual → candidato aparece
  três vezes. Tratar como grafo, não como soma.
- **`despesas_contratadas` x `despesas_pagas`.** São tabelas distintas e
  divergem. Decidir explicitamente qual responde cada pergunta antes de somar
  qualquer coisa.
- **2026 está em prestação parcial.** O ZIP de candidatos já existe (137 MB
  contra 377 MB de 2022), mas a prestação final só sai depois da eleição.

## ADR-007 — Publicação é etapa do pipeline, não passo manual

**Contexto.** A ingestão roda em Codespaces, que hiberna em 30 minutos de
inatividade e é apagado após 30 dias parado. Um `make ingerir` bem-sucedido
produz centenas de MB de Parquet que existem apenas ali dentro.

**Decisão.** `fundo_eleitoral.publicacao` sobe os Parquet para um dataset
público no Hugging Face, e `make tudo` encadeia ingestão e publicação. O
dataset leva um cartão gerado pelo próprio código, com a proveniência e as três
armadilhas de leitura (contratada x paga, dupla contagem entre diretórios,
tudo string).

**Por quê.** Se publicar for um passo manual e opcional, mais cedo ou mais tarde
alguém — provavelmente eu mesmo — vai rodar a ingestão, fechar a aba e perder o
resultado. Encadeado, o caminho barato e o caminho correto são o mesmo.

**Público, não privado:** o dado é público de origem, e um dataset aberto torna
a análise reproduzível sem exigir que terceiros refaçam a ingestão — que é
justamente a parte cara e cheia de armadilhas.

## ADR-008 — Conversão em fluxo, não em memória

**Contexto.** A primeira versão usava `pl.read_csv` + `write_parquet`, que
materializa a tabela inteira na RAM. Num Codespaces de 8 GB o processo foi
morto pelo sistema (`Terminated`) ao chegar em
`despesas_contratadas_candidatos_2022` — 2,2 milhões de linhas e 53 colunas,
todas string.

**Decisão.** `pl.scan_csv(...).sink_parquet(...)`: o arquivo é processado em
lotes e nunca existe inteiro em memória. Medido na maior tabela do pacote de
2022: pico de **2,3 GB**.

**Consequência de encoding.** `scan_csv` só aceita UTF-8, enquanto o TSE
publica em latin-1 — era o `read_csv` que fazia essa conversão. A transcodificação
passou a acontecer durante a extração do ZIP, também em blocos. Latin-1 é de
byte único, então qualquer corte de bloco cai numa fronteira válida; o mesmo
truque seria incorreto se a entrada fosse UTF-8.

**Também:** a conversão passou a pular tabelas já convertidas. Depois de um
processo morto no meio, reexecutar retoma de onde parou em vez de refazer o
que já estava pronto.

## ADR-009 — Repasse entre candidaturas fica fora da concentração

**Contexto.** Parte do que o TSE marca como `FUNDO ESPECIAL` chega com
`ds_origem_receita = 'Recursos de outros candidatos'`: o partido repassou ao
candidato A, que transferiu a B. Somar os dois conta os mesmos reais duas
vezes.

**Quanto pesa:**

| ciclo | FEFC sem dupla contagem | com | inflação |
|---|---|---|---|
| 2018 | R$ 1,694 bi | R$ 1,834 bi | +8,26% |
| 2022 | R$ 4,741 bi | R$ 4,903 bi | +3,42% |
| 2026 (parcial) | R$ 4,611 bi | R$ 4,676 bi | +1,41% |

**Decisão.** Excluir por padrão. `incluir_repasse_entre_candidatos=True`
restaura o comportamento antigo, para reconciliar com o total bruto do fundo.

**Por quê — e o efeito é maior do que o total sugere.** O erro não é só de
soma: quem repassou aparece como se tivesse ficado com o dinheiro, e quem
recebeu aparece duas vezes. Medido, o viés é **sistemático numa direção só**:
incluir o repasse sempre *reduz* o Gini, porque as transferências correm de
quem recebeu muito para candidaturas menores. Ou seja, a dupla contagem faz
todo partido parecer mais igualitário do que é — exatamente o oposto do que a
análise quer medir.

Casos extremos: PCdoB em 2018 passa de Gini 0,951 para 0,889 (−0,062, com o
total inflado em 24%); PSB em 2022, de 0,810 para 0,785.

**Observação sobre 2018.** A inflação de 8,26% é o dobro da de 2022. Vale
investigar se reflete mudança de regra entre ciclos ou apenas o FEFC menor
daquele ano — não está respondido.
