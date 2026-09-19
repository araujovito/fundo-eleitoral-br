# Concentração x pulverização do FEFC

Este recorte mede se cada partido concentrou o Fundo Especial de Financiamento
de Campanha em poucas candidaturas ou o distribuiu de forma mais ampla. O
código reproduzível está em `fundo_eleitoral.concentracao`.

## Unidade de análise

A unidade básica é a candidatura (`sq_candidato`). Primeiro, todos os repasses
cuja fonte é `FUNDO ESPECIAL` são somados por candidatura. Depois, o resultado
é ligado ao cadastro completo de candidaturas; quem não recebeu FEFC entra com
valor zero.

Esse último passo é indispensável. Calcular a desigualdade apenas entre quem
recebeu faria um partido que financiou 10 de 100 candidaturas parecer tão
pulverizado quanto outro que financiou as 100 com a mesma distribuição entre
os recebedores.

Por padrão entram todas as candidaturas registradas, inclusive as que ao final
ficaram inaptas. A pergunta é onde o partido alocou o dinheiro, e excluí-las
retiraria R$ 46,4 milhões em 2018 e R$ 72,0 milhões em 2022 do valor
efetivamente repassado. Para perguntas sobre a disputa final existe o recorte
alternativo `--apenas-aptas`. Ele não é aplicado a 2026 enquanto o TSE ainda
não tiver publicado a situação das candidaturas.

## Métricas

- **Cobertura:** percentual das candidaturas que recebeu algum FEFC.
- **Gini:** desigualdade dos valores, incluindo zeros; 0 é igualdade perfeita
  e 1 é concentração máxima.
- **HHI:** soma dos quadrados das participações. A saída o mostra na escala
  convencional de 0 a 10.000.
- **Número efetivo:** inverso do HHI. Responde quantos recebedores iguais
  produziriam a concentração observada.
- **Top 10%:** parcela do FEFC apropriada pelos 10% de candidaturas com maiores
  repasses, arredondando o tamanho do grupo para cima.

Nenhuma métrica deve ser lida isoladamente. Cobertura separa exclusão de
concentração entre recebedores; Gini resume a desigualdade; HHI e número efetivo
dão mais peso aos maiores repasses; top 10% é a medida mais fácil de comunicar.

## Recorte principal

Para estudar "puxadores", a comparação principal usa candidaturas a deputado
federal e células `partido x UF`. Misturar Presidência, governos e eleições
proporcionais numa linha nacional faria uma campanha majoritária dominar a
métrica sem revelar a estratégia da chapa legislativa.

Para reduzir células instáveis, o resumo abaixo exige pelo menos 10
candidaturas e R$ 1 milhão de FEFC na célula. São medianas entre células, de
modo que cada partido em cada UF tem o mesmo peso:

| ciclo | células | cobertura mediana | Gini mediano | FEFC dos 10% do topo |
|---|---:|---:|---:|---:|
| 2018 | 95 | 73,3% | 0,761 | 71,3% |
| 2022 | 243 | 92,1% | 0,629 | 51,4% |
| 2026 (parcial) | 183 | 92,0% | 0,588 | 46,6% |

O movimento de 2018 para 2022 aparece nas três medidas: mais candidaturas
receberam recursos, a desigualdade caiu e os 10% maiores ficaram com uma fatia
menor. É evidência descritiva de maior pulverização, não uma conclusão causal.
A composição das células não é fixa entre ciclos, partidos mudaram e o dado de
2026 é uma fotografia de campanha em curso.

As diferenças dentro de um mesmo ciclo também são grandes. Aplicando um corte
mais conservador de R$ 5 milhões em 2022, o PSC de Minas Gerais apresentou
Gini 0,883 e concentrou 89,3% do fundo nos 10% do topo. No outro extremo, PP de
Alagoas teve Gini 0,231 e 13,6% no topo. Esses exemplos descrevem a distribuição
do dinheiro; chamar uma candidatura de "puxadora" ainda exige cruzar votos, que
pertence ao recorte de eficiência.

## Reprodução

Visão nacional por partido, útil como diagnóstico geral:

```bash
python -m fundo_eleitoral.concentracao --ano 2022
```

Recorte principal de deputado federal por partido e UF:

```bash
python -m fundo_eleitoral.concentracao \
  --ano 2022 \
  --por uf cargo \
  --cargo "DEPUTADO FEDERAL" \
  --minimo-milhoes 1 \
  --minimo-candidaturas 10
```

Os argumentos `--cargo` e `--uf` são repetíveis. Use `--apenas-aptas` para o
recorte alternativo que exclui candidaturas inaptas.

## Validação e limites

Todos os `sq_candidato` com FEFC nos três ciclos encontram correspondência no
cadastro. Os valores agregados reconciliam com os totais já ancorados contra o
fundo nacional: R$ 1,834 bilhão em 2018, R$ 4,903 bilhões em 2022 e R$ 4,676
bilhões no retrato parcial de 2026.

Não usamos neste estágio uma referência externa que publique Gini ou HHI por
partido e UF para conferência direta. As métricas foram verificadas com
casos sintéticos de igualdade perfeita, concentração máxima, candidaturas sem
repasse, repasses múltiplos e duplicatas no cadastro.

## Correção: repasse entre candidaturas (ADR-009)

A primeira versão somava como FEFC recebido tudo que vinha marcado como
`FUNDO ESPECIAL`, inclusive o que uma candidatura repassou a outra — dinheiro
já contado quando o partido o distribuiu. A medida agora exclui esse repasse
por padrão.

O efeito sobre o total é modesto (+1,4% a +8,3% conforme o ciclo), mas o
efeito sobre a *medida* é enviesado numa direção só: incluir o repasse sempre
reduz o Gini, porque as transferências saem de quem recebeu muito para
candidaturas menores. Quem quiser reconciliar com o total bruto do fundo usa
`incluir_repasse_entre_candidatos=True`.
