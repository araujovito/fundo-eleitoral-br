# Incumbentes x novos nomes

Este recorte pergunta se o FEFC financia renovação ou protege quem já venceu
uma eleição. O código reproduzível está em `fundo_eleitoral.renovacao`.

## O que cada perfil significa

O pareamento usa o CPF da candidatura atual contra o ciclo geral anterior. O
resultado eleitoral anterior (`ds_sit_tot_turno`) separa cinco perfis:

1. **Incumbente no mesmo cargo:** foi `ELEITO%` para o mesmo cargo no ciclo
   anterior.
2. **Eleito em outro cargo:** venceu a eleição anterior, mas agora disputa
   outro cargo.
3. **Candidato recorrente:** concorreu no ciclo anterior, mas não consta como
   eleito.
4. **Novo no recorte:** não aparece no ciclo imediatamente anterior.
5. **CPF inválido:** não pode ser pareado com segurança, como a sentinela `-4`
   encontrada nos arquivos do TSE.

"Novo no recorte" não significa estreante absoluto na política. A pessoa pode
ter concorrido antes da janela, ocupado cargo municipal ou exercido função não
eletiva. Da mesma forma, "incumbente" aqui significa **eleito para o mesmo
cargo no ciclo anterior**, não confirmação de que permaneceu no mandato até o
dia do novo registro.

## Método

As eleições suplementares presentes nos arquivos anuais são excluídas dos dois
lados do pareamento. Cada candidatura atual entra uma vez; seus repasses de
`FUNDO ESPECIAL` são somados e candidaturas sem FEFC entram com zero.

O recorte principal é deputado federal. O mandato dura quatro anos, portanto
2018 → 2022 e 2022 → 2026 são janelas coerentes. O mesmo método não deve ser
aplicado diretamente ao Senado: senadores têm mandato de oito anos e parte dos
incumbentes não aparece no ciclo imediatamente anterior.

Além de cobertura e valor médio, calculamos um **índice de alocação**:

```
participação do perfil no FEFC / participação do perfil nas candidaturas
```

Valor 1 significa alocação proporcional ao tamanho do perfil. Acima de 1 é
sobrerrepresentação financeira; abaixo de 1, sub-representação.

## Resultado nacional — deputado federal

### 2022 comparado a 2018

| perfil | candidaturas | FEFC | índice | média por candidatura |
|---|---:|---:|---:|---:|
| incumbente no mesmo cargo | 4,0% | 28,3% | 7,05x | R$ 1,739 mi |
| eleito em outro cargo | 1,3% | 5,6% | 4,15x | R$ 1,024 mi |
| candidato recorrente | 18,2% | 23,2% | 1,27x | R$ 314 mil |
| novo no recorte | 76,4% | 43,0% | 0,56x | R$ 139 mil |
| CPF inválido | 0,1% | 0,0% | 0,00x | R$ 0 |

Incumbentes no mesmo cargo eram apenas 426 das 10.630 candidaturas, mas
receberam R$ 740,8 milhões dos R$ 2,621 bilhões analisados. A média de R$ 1,739
milhão por incumbente foi **12,5 vezes** os R$ 139 mil de um nome novo no
recorte.

O viés varia entre partidos. Entre as legendas com ao menos R$ 5 milhões no
recorte e algum incumbente, o PL destinou 49,0% do FEFC a incumbentes no mesmo
cargo, o PCdoB 47,9% e o PT 44,2%. No PL, eles eram 13,7% das candidaturas; no
PT, 13,7%.

### 2026 comparado a 2022 — parcial

| perfil | candidaturas | FEFC | índice | média por candidatura |
|---|---:|---:|---:|---:|
| incumbente no mesmo cargo | 5,3% | 32,1% | 6,04x | R$ 2,063 mi |
| eleito em outro cargo | 1,4% | 5,5% | 4,06x | R$ 1,385 mi |
| candidato recorrente | 25,4% | 27,8% | 1,09x | R$ 374 mil |
| novo no recorte | 68,0% | 34,7% | 0,51x | R$ 174 mil |

O padrão permanece no retrato parcial: a média por incumbente é 11,9 vezes a
média de um novo nome. Como as prestações ainda estão em andamento, esses
percentuais não devem ser tratados como resultado final do ciclo.

## Reprodução

Agregado nacional de deputado federal:

```bash
python -m fundo_eleitoral.renovacao \
  --ano 2022 \
  --por \
  --cargo "DEPUTADO FEDERAL"
```

Detalhamento por partido:

```bash
python -m fundo_eleitoral.renovacao \
  --ano 2022 \
  --por partido \
  --cargo "DEPUTADO FEDERAL" \
  --minimo-milhoes 5
```

`--por partido uf` abre células estaduais; `--apenas-aptas` restringe o ciclo
atual às candidaturas aptas quando o campo já foi publicado.

## Validação e limites

O agregado reproduz exatamente uma consulta direta às candidaturas ordinárias
de deputado federal: 10.630 candidaturas e R$ 2,621 bilhões em 2022; 7.801 e R$
2,664 bilhões na parcial de 2026. Os testes sintéticos cobrem eleitos no mesmo e
em outro cargo, recorrentes não eleitos, novos nomes, CPF sentinela, eleições
suplementares, candidaturas sem repasse e múltiplos repasses.

Não usamos neste estágio uma lista externa de ocupantes efetivos. Por isso, um
suplente que assumiu o mandato depois da eleição continua classificado como
candidato recorrente, enquanto alguém eleito que deixou o cargo continua no
grupo de incumbentes. Essa diferença precisará de uma fonte histórica da Câmara
para ser resolvida.
