# Prioridade geográfica

## Pergunta

Quais UFs recebem FEFC diretamente em proporção maior — ou menor — que seu
peso no eleitorado?

## Método

Para cada UF, o módulo soma o FEFC repassado diretamente pelo partido às
candidaturas registradas nela e compara sua participação no total à participação
da UF no eleitorado brasileiro domiciliado. O índice é:

```
participação da UF no FEFC / participação da UF no eleitorado
```

Logo, 1,00x é proporcional; acima de 1,00x indica sobrepeso no fundo. A opção
`--por-partido` repete a conta com o total de cada partido como denominador.

## Limites que importam

- Repasse entre candidaturas não entra, pela mesma razão dos demais recortes:
  ele duplica recursos já recebidos do partido ([ADR-009](decisoes.md#adr-009--repasse-entre-candidaturas-fica-fora-da-concentração)).
- Candidaturas com `SG_UF = BR`, como a presidencial, não pertencem a uma UF e
  não entram no índice. O relatório não tenta distribuí-las por população,
  votação ou domicílio do candidato.
- `ZZ` representa o eleitorado no exterior e também fica fora do denominador;
  o comparativo é entre as 27 UFs brasileiras.
- Em 2026, a prestação de contas é parcial. O eleitorado do ciclo é completo,
  mas o numerador ainda pode mudar.

## Fonte do eleitorado

`dados/dimensoes/eleitorado.parquet` contém somente `ano`, `sg_uf` e
`qt_eleitores`: 81 linhas, uma por UF e ciclo. Os valores são a soma de
`QT_ELEITORES_PERFIL` (2018) ou `QT_ELEITORES` (2022 e 2026) nos arquivos
`perfil_eleitorado_<ano>.zip` do [TSE](https://dadosabertos.tse.jus.br/),
disponíveis no CDN público em
`https://cdn.tse.jus.br/estatistica/sead/odsele/perfil_eleitorado/`.
É uma dimensão pequena, mantida no repositório para que as análises não
dependam de rede, conforme ADR-002.
