# Proporcionalidade racial do FEFC

Este recorte compara a participação de candidaturas negras com a parcela do
Fundo Especial de Financiamento de Campanha que elas recebem diretamente. O
código reproduzível está em `fundo_eleitoral.raca`.

## A regra

Em 2020, o TSE decidiu na Consulta 0600306-47 que FEFC, Fundo Partidário e tempo
de propaganda devem ser distribuídos proporcionalmente ao total de
candidaturas negras apresentadas pelo partido. A regra passou a valer nas
eleições gerais de 2022. O Tribunal rejeitou criar um piso fixo de 30%: a
referência é a proporção efetiva de candidaturas.

Na classificação usada pelo TSE e pelo IBGE, a população negra reúne pessoas
autodeclaradas pretas e pardas. Fontes oficiais:

- [decisão original do TSE, de 25/08/2020](https://www.tse.jus.br/comunicacao/noticias/2020/Agosto/tse-distribuicao-fefc-candidatos-negros);
- [balanço das ações afirmativas publicado pelo TSE](https://www.tse.jus.br/comunicacao/noticias/2023/Novembro/acoes-afirmativas-da-justica-eleitoral-contribuem-para-aumentar-a-representacao-negra-na-politica).

## Método

A unidade é a candidatura ordinária (`sq_candidato`). A raça vem do cadastro
de candidaturas, e não da repetição do campo em cada linha de receita. Todos os
repasses cuja fonte é `FUNDO ESPECIAL` são somados por candidatura; quem não
recebeu entra com valor zero. Eleições suplementares são excluídas.

O padrão inclui todas as candidaturas registradas. Isso mantém no mesmo
universo os R$ 4,903 bilhões efetivamente repassados em 2022, inclusive R$ 72
milhões destinados a candidaturas que depois ficaram inaptas. O recorte
alternativo `--apenas-aptas` está disponível. Em 2026 ele não é aplicado
enquanto o TSE ainda não tiver publicado a situação.

Para cada partido calculamos:

- percentual de candidaturas pretas ou pardas;
- percentual do FEFC direto recebido por essas candidaturas;
- diferença entre as duas participações, em pontos percentuais;
- valor adicional que igualaria as participações;
- percentual de candidaturas sem raça informada ou divulgável.

## Resultado nacional

| ciclo | candidaturas negras | FEFC direto | diferença | déficit equivalente |
|---|---:|---:|---:|---:|
| 2018 — linha de base | 46,5% | 24,3% | -22,1 pp | R$ 405,4 mi |
| 2022 — regra vigente | 50,3% | 36,6% | -13,7 pp | R$ 671,4 mi |
| 2026 — parcial | 48,4% | 34,2% | -14,1 pp | R$ 660,0 mi |

A distância proporcional diminuiu entre 2018 e 2022, mas permaneceu grande no
primeiro ciclo de vigência. O valor absoluto do déficit aumentou porque o fundo
de 2022 foi muito maior. Em 2026, que ainda está em prestação parcial, não há
melhora proporcional até o retrato analisado.

Entre os partidos com ao menos R$ 20 milhões de FEFC em 2022, **23 de 24**
repassaram diretamente a candidaturas negras uma fatia menor que sua presença
nas candidaturas. As maiores diferenças foram:

| partido | candidaturas negras | FEFC direto | diferença |
|---|---:|---:|---:|
| PSDB | 45,7% | 19,9% | -25,8 pp |
| PDT | 52,2% | 27,7% | -24,5 pp |
| PT | 50,0% | 28,0% | -21,9 pp |

A União Brasil foi a única acima da proporção nesse corte: 47,6% das
candidaturas e 48,0% do FEFC direto. Em 2018, antes da regra, todos os 19
partidos do corte estavam abaixo. Na parcial de 2026, são 19 de 20; apenas o
Avante aparece acima.

## O que o resultado não prova

Esta é uma análise de **receitas diretas das candidaturas**, não uma auditoria
completa da obrigação legal. Partidos podem pagar despesas compartilhadas ou
registrar gastos partidários em benefício de candidaturas negras sem que o
valor apareça como receita individual no Parquet usado aqui. A prestação
jurídico-contábil também pode considerar ajustes e documentos fora deste
recorte.

Por isso, “abaixo da proporção” significa abaixo nos repasses diretos
observados. É um sinal material de desigualdade e de possível risco de
conformidade, mas não autoriza, sozinho, afirmar que o partido cometeu infração.
Uma auditoria legal exigiria incorporar despesas dos órgãos partidários e a
destinação declarada de gastos compartilhados.

## Reprodução

```bash
python -m fundo_eleitoral.raca --ano 2022 --minimo-milhoes 20
```

Para restringir o denominador às candidaturas aptas:

```bash
python -m fundo_eleitoral.raca --ano 2022 --apenas-aptas
```

Os testes sintéticos cobrem pretos e pardos, candidaturas sem repasse,
duplicatas, múltiplas receitas, suplementares, aptidão, raça não informada e o
cálculo do déficit em reais.
