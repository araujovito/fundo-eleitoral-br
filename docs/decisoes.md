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

### ADR-009, adendo: o viés do repasse tem cor e gênero

Ao aplicar a exclusão à análise de cota, apareceu um segundo motivo para ela,
mais forte que a dupla contagem. O repasse entre candidaturas não é uma amostra
aleatória do fundo:

| | FEFC total | só o repasse entre candidaturas |
|---|---|---|
| Masculino (2022) | 69,2% | 75,3% |
| Masculino (2026) | 65,5% | 75,8% |
| Preta (2022) | 9,1% | 10,9% |

Três quartos do que circula entre candidaturas vai para homens, contra dois
terços do fundo como um todo. Incluir esse fluxo no denominador da cota
subestimava a fatia feminina — e a distorção cresce de 2022 para 2026.

Efeito na medida: 2018 passa de 26,7% para 27,6%; 2022, de 30,8% para 31,0%;
2026, de 34,5% para 34,7%. Dois partidos mudam de lado em 2022 (Republicanos e
PCdoB, ambos marginais), e o corte de R$ 20 mi passa a excluir um partido que
só alcançava o limite graças ao repasse — daí 23 partidos onde antes eram 24.

**Aplicado em todo o projeto.** `analise.py`, `concentracao.py`, `raca.py` e
`renovacao.py` usam a mesma definição. Efeito nos recortes já publicados:
repasse a candidaturas negras em 2022 passa de 36,6% para 36,5% (defasagem de
R$ 671,4 mi para R$ 654,4 mi, e de 23 de 24 partidos abaixo para 21 de 23);
a razão incumbente/novo a deputado federal sobe de 12,5x para 12,7x, porque o
repasse entre candidaturas favorecia proporcionalmente os novos nomes.

## ADR-010 — Uma definição só para a consulta de FEFC

**Contexto.** Cada recorte novo nasceu copiando a consulta do anterior. O
resultado: `_VALOR`, o caminho do Parquet, o teste de aptidão e a CTE de FEFC
apareciam nos quatro módulos de análise. Quando o ADR-009 mostrou que a
consulta estava errada, a correção teve de ser feita e testada quatro vezes —
e nas duas primeiras vezes eu esqueci os outros dois módulos.

**Decisão.** `consulta.py` guarda a definição: `VALOR`, `FONTE_FEFC`,
`ORIGEM_REPASSE`, `caminho`, `tem_candidaturas_aptas`, `clausula_aptidao` e
`cte_fefc`. Quem escrever um recorte novo monta a CTE daí.

**Por quê.** O problema não era digitar a mesma coisa quatro vezes — era o
defeito se propagar por cópia. Um recorte novo herdava a consulta do vizinho
com o defeito que ela tivesse naquele dia.

**Verificação.** A refatoração foi validada comparando a saída dos quatro
recortes, nos três ciclos, antes e depois: byte a byte idêntica. Um teste em
`test_consulta.py` falha se algum módulo voltar a definir a própria versão.

**O que ficou de fora.** A agregação de `analise.py` é por partido, não por
candidatura, e não cabe na `cte_fefc` — ela usa as constantes compartilhadas
mas mantém a própria consulta. Forçar o encaixe teria produzido um helper com
parâmetros demais para servir a dois casos.

## ADR-011 — Dimensões derivadas do TSE, não versionadas

**Contexto.** `geografia.py` e `eficiencia.py` precisam de eleitorado por UF e
de votos por candidatura, que não estão na prestação de contas. Os dois Parquet
chegaram ao projeto **versionados no git, sem nenhum código que os gerasse** —
não davam para conferir, atualizar nem reproduzir.

**Decisão.** `dimensoes.py` deriva as duas tabelas de
`perfil_eleitorado` e `votacao_candidato_munzona`, publicadas pelo TSE. O
resultado vai para o dataset no Hugging Face, junto com o resto; o `.gitignore`
volta a ser absoluto.

**Por que importava.** Ao reproduzir, os números divergiram:

| | versionado | derivado |
|---|---|---|
| eleitorado 2018 | 146,81 mi | 146,81 mi |
| eleitorado 2022 | 155,76 mi | 155,76 mi |
| votos 2018 | 602,7 mi | 720,7 mi |
| votos 2022 | 564,2 mi | 714,2 mi |

O eleitorado batia exatamente. Os votos não: faltavam **presidente e
governador** — as disputas majoritárias, que são as que mais recebem FEFC. A
análise de eficiência media R$/voto sem a eleição presidencial, e nada no
projeto podia apontar isso, porque não havia como refazer o arquivo.

**A armadilha do `_BRASIL`, invertida.** Em `perfil_eleitorado` existe um
arquivo `_BRASIL` que é a **união** das UFs: somá-lo junto duplica o total
exato (312,9 mi de eleitores em vez de 156,5 mi). Na prestação de contas, o
arquivo de mesmo sufixo é um **superconjunto** e usá-lo sozinho é o correto
(ADR-006). Mesmo nome, tratamento oposto — conferir contra referência externa é
o que separa um do outro.

**Outras diferenças entre ciclos:** 2018 vem num CSV único, sem divisão por UF,
e chama a coluna de `qt_eleitores_perfil` em vez de `qt_eleitores`; `ZZ`
(exterior) precisa sair por linha, não só por nome de arquivo; e
`votacao_candidato_munzona_2026` existe mas está vazio, porque a eleição ainda
não aconteceu.

## ADR-012 — Prioridade geográfica medida por cadeira, não só por eleitorado

**Contexto.** A primeira versão comparava a fatia de cada UF no FEFC com a sua
fatia no eleitorado. Roraima aparecia com 6,33x, o Amapá com 6,31x — leitura
natural: os partidos privilegiam estados pequenos.

**O problema.** Isso mede sobretudo a Constituição, não a estratégia. Cada
estado elege no mínimo 8 deputados federais, então Roraima disputa 8 cadeiras
com 366 mil eleitores enquanto São Paulo disputa 70 com 34,7 milhões. O FEFC
segue candidaturas, que seguem cadeiras. Atribuir isso a escolha partidária é
confundir desenho institucional com decisão.

**Decisão.** Manter os dois denominadores. O índice por cadeira só é calculado
quando a análise filtra **um cargo**: cadeira de deputado federal e de
governador não se somam.

**Efeito, deputado federal em 2022:**

| UF | x eleitorado | x cadeira |
|---|---|---|
| RR | 6,33x | 0,95x |
| AP | 6,31x | 1,43x |
| SP | 0,62x | 1,02x |
| RS | 0,79x | 0,72x |

A leitura se inverte. São Paulo, aparentemente penalizada, recebe o
proporcional às suas cadeiras; Roraima fica ligeiramente abaixo do par. O que
resta de dispersão — 1,62x em Tocantins contra 0,72x no Rio Grande do Sul — é o
sinal estratégico de verdade, e é muito menor do que o primeiro número sugeria.

**De onde vêm as cadeiras.** De quem foi eleito no próprio ciclo, no cadastro
de candidaturas. Confere com referência externa: 513 deputados federais em 2018
e em 2022. Quando o ciclo ainda não tem resultado — 2026 — a função recua para
o ciclo anterior, e isso precisa ser dito ao leitor: a redistribuição de
cadeiras de 2023 alterou a bancada de vários estados.
