# Contexto do projeto

Documento de orientação: por que este projeto existe, onde ele está e para
onde vai. As decisões técnicas e o *porquê* de cada uma estão em
[decisoes.md](decisoes.md); cada recorte tem seu próprio documento de método.
Aqui fica o mapa.

Última atualização: 19/09/2026.

## A pergunta

Quanto cada partido gastou é dado público e pouco informativo. A pergunta é
**onde cada partido apostou o dinheiro** do Fundo Eleitoral (FEFC) e do Fundo
Partidário — e o que essa alocação revela da estratégia eleitoral.

Três ciclos: 2018, 2022 e 2026. O último está em prestação parcial, com a
eleição a poucas semanas, o que permite acompanhar uma campanha em curso contra
uma linha de base histórica.

## O que já existe

**Pipeline em quatro etapas, separadas de propósito** (ADR-001):

```
ingestao.py    ZIPs do TSE → Parquet                    (roda raro)
dimensoes.py   deriva eleitorado e votos do TSE         (ADR-011)
publicacao.py  Parquet → dataset público no Hugging Face
consulta.py    a definição única da consulta de FEFC    (ADR-010)
<recorte>.py   análise; lê Parquet, nunca baixa
dashboard.py   agregados dos recortes → JSON do painel
```

**Dados:**
[huggingface.co/datasets/buscafe/fundo-eleitoral-br](https://huggingface.co/datasets/buscafe/fundo-eleitoral-br)
— 27 tabelas mais as dimensões derivadas, público. A análise lê direto de lá:
quem clonar o repositório reproduz os números sem refazer a ingestão.

**Sete recortes prontos**, cada um com documento de método próprio:

| recorte | pergunta | doc |
|---|---|---|
| `analise` | cota de gênero é cumprida? | README |
| `concentracao` | poucos puxadores ou chapa inteira? | [concentracao.md](concentracao.md) |
| `renovacao` | financia reeleição ou renovação? | [renovacao.md](renovacao.md) |
| `raca` | proporcionalidade racial é cumprida? | [raca.md](raca.md) |
| `geografia` | quais UFs recebem acima do seu peso? | [geografia.md](geografia.md) |
| `eficiencia` | quanto custa cada voto? | [eficiencia.md](eficiencia.md) |
| `fluxos` | por onde o dinheiro circula? | [fluxos.md](fluxos.md) |

**Dashboard.** `dashboard/` traz a **Festa da Democracia**: sete abas em React
sobre os mesmos agregados, com filtros por ciclo, partido e cargo. A interface
prioriza uma leitura editorial, mas mantém as tabelas e os agregados
verificáveis. Ela não consulta o Parquet ao abrir — `dashboard.py` exporta uma
fotografia datada para `dashboard/public/data.json`, sem nome, CPF ou CNPJ, e a
interface lê esse arquivo. Atualizar o painel é reexecutar a exportação e
commitar o JSON.

Os limites permanecem explícitos: eficiência compara apenas cargos
proporcionais de turno único; território usa cadeiras em disputa quando há um
único cargo escolhido e eleitorado apenas como referência descritiva no
recorte amplo; fluxos não somam as etapas como dinheiro novo; e 2026 é parcial.
Além de tipos, build e testes de reconciliação, a interface foi revisada em
desktop, tablet e celular.

## O que aprendemos

Os achados estão no [README](../README.md). O que vale registrar aqui é o
padrão por trás deles, porque ele se repetiu quatro vezes:

**Toda medida ingênua subestimava a desigualdade que queríamos medir.**
Incluir o repasse entre candidaturas reduzia o Gini, suavizava o viés
pró-incumbente e diluía a defasagem de gênero (ADR-009). Comparar fundo com
eleitorado, em vez de com cadeiras, atribuía à estratégia partidária o que era
piso constitucional, e invertia o sinal (ADR-012). Somar arquivos por UF
descartava a eleição presidencial (ADR-006); a dimensão de votos versionada no
git também a omitia (ADR-011).

**Nenhum desses erros foi encontrado lendo código.** Todos apareceram ao
conferir um número contra referência externa: R$ 4,90 bi do FEFC de 2022,
156 milhões de eleitores, 513 deputados federais.

## O que pretendemos fazer

Antes de abrir o oitavo recorte, consolidar:

1. **Uma visão que atravesse os recortes.** Hoje cada um responde a sua
   pergunta isoladamente. O partido que concentra é o mesmo que descumpre a
   cota? Quem financia incumbentes é quem gasta mais por voto?
2. **2026 em acompanhamento.** A prestação é parcial e muda até a eleição.
   Vale reingerir periodicamente e observar o que se move — é o único recorte
   que ninguém mais está fazendo em tempo real.
3. **Fechar o ciclo do dashboard.** A visualização existe, mas o JSON é
   gerado à mão. O painel data a própria extração no rodapé, então não engana
   quem olha; o que falta é a exportação acompanhar a reingestão de 2026, em
   vez de depender de alguém lembrar de rodá-la.
4. **A normalização de sigla está copiada em sete módulos.** `PC DO B` →
   `PCDOB` aparece solto em cada recorte e agora também em `dashboard.py`. É o
   mesmo padrão que gerou o ADR-010: quando a próxima sigla mudar, a correção
   terá de ser feita sete vezes.

Depois disso: incumbentes por cargo (hoje só deputado federal), eficiência
descontando o efeito de puxador de voto, e o grafo de fluxos levado até o
fornecedor final.

## Armadilhas já mapeadas

Cada uma custou tempo ou quase produziu número errado:

- **Arquivos por UF não são partição** na prestação de contas: usar só os
  `_BRASIL` (ADR-006). Mas em `perfil_eleitorado` o `_BRASIL` é a **união** e
  somá-lo duplica o total (ADR-011). Mesmo sufixo, tratamento oposto.
- **`despesas_contratadas` ≠ `despesas_pagas`.** Em 2026 parcial, contratadas
  são o dobro das pagas.
- **Repasse entre candidaturas conta o mesmo dinheiro duas vezes** (ADR-009).
  Só `fluxos.py` deve incluí-lo: lá ele é o objeto de estudo.
- **Siglas mudam entre ciclos.** `PC do B` em 2022, `PCDOB` em 2026.
- **Colunas mudam de nome entre ciclos.** `qt_eleitores_perfil` em 2018,
  `qt_eleitores` depois. Detectar, não presumir.
- **Campos de 2026 ainda vazios.** Situação da candidatura e resultado vêm
  `#NULO` ou `#NE`: filtro só se aplica quando existe.
- **CDN do TSE recusa clientes programáticos** por impressão digital de TLS
  (ADR-005). Um 403 é bloqueio; um 404 é nome de arquivo errado.
- **Fixture de teste que diverge do dado real esconde o bug** até alguém mexer
  na consulta. Aconteceu duas vezes com `ds_origem_receita`.

## Como rodar

```bash
pip install -e '.[dev]'
python -m fundo_eleitoral.analise                 # lê do Hugging Face
python -m fundo_eleitoral.geografia --ano 2022 --cargo "DEPUTADO FEDERAL"
make teste
```

Refazer a ingestão só é necessário para atualizar o dataset:

```bash
make verificar                                    # testa as URLs do TSE
make ingerir ANO=2026
python -m fundo_eleitoral.dimensoes --ano 2026
REPO=buscafe/fundo-eleitoral-br make publicar
```

## Método

Uma regra vale para tudo aqui: **conferir o número contra uma referência
externa antes de confiar nele.** O FEFC de 2022 calculado a partir de
`ds_fonte_receita` deu R$ 4,90 bi, que é o valor real do fundo; as cadeiras
derivadas dos eleitos dão 513, que é o tamanho da Câmara. É isso que autoriza
usar a coluna. Quando não houver âncora externa, dizer explicitamente que não
houve.

Corolário aprendido na prática: **refatoração que muda número é bug.** Antes de
mexer na consulta compartilhada, gravamos a saída dos recortes nos três ciclos
e comparamos depois — tem de ser idêntica.
