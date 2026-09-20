# Metodologia comum

Este documento reúne as regras que valem para todos os recortes. Os documentos
de concentração, raça, geografia, renovação, eficiência e fluxos descrevem as
decisões específicas de cada pergunta.

## Escopo observado

As métricas analíticas usam o **FEFC repassado diretamente por partidos às
candidaturas**. A fonte é `receitas_candidatos`, com
`ds_fonte_receita = FUNDO ESPECIAL`. Receitas cuja origem é `Recursos de outros
candidatos` ficam fora: esse dinheiro já apareceu quando o partido o repassou à
primeira candidatura e incluí-lo novamente produziria dupla contagem.

Isso não equivale ao total da dotação do FEFC, ao total recebido por órgãos
partidários nem ao total gasto nas campanhas. O recorte de fluxos é a exceção:
ele preserva transferências porque seu objeto é o caminho declarado do dinheiro,
mas não soma as etapas como recursos novos.

## Unidade e denominadores

Cada indicador declara sua unidade antes do cálculo:

| indicador | unidade | denominador |
|---|---|---|
| gênero e raça | partido ou Brasil | candidaturas únicas e FEFC direto |
| concentração | candidatura dentro de partido × UF × cargo | FEFC direto da célula |
| renovação | candidatura comparada ao ciclo anterior por CPF | candidaturas e FEFC direto |
| território | UF | eleitorado ou cadeiras, nunca ambos misturados |
| eficiência | candidatura em cargo proporcional de turno único | voto nominal |
| fluxos | aresta declarada entre origens e destinos | nenhum total consolidado |

Candidaturas são deduplicadas por `sq_candidato`. Quando um ciclo já contém
situação eleitoral confiável, entram apenas candidaturas aptas. Se o campo ainda
não foi publicado — como ocorre na parcial de 2026 — o filtro não é aplicado;
aplicar um filtro sobre `#NE` produziria um resultado vazio com aparência válida.

## Ciclos parciais

Um ciclo parcial pode mudar entre duas publicações. Portanto:

- valores de 2026 são uma fotografia, identificada por `generatedAt`;
- resultados eleitorais e eficiência permanecem indisponíveis até existirem
  votos oficiais;
- cadeiras usam o último ciclo com resultado e informam o ano de referência;
- nenhuma variação parcial é descrita como tendência encerrada;
- comparações com 2018 e 2022 são descritivas, não equivalentes a uma prestação
  final.

O painel publica também a razão entre FEFC direto observado e dotação oficial.
Em 19/09/2026, eram R$ 4.610.565.650,36 de repasses diretos para uma dotação de
R$ 4.961.519.777,00, ou 92,93%. Essa razão **não é uma taxa de conclusão**:
recursos podem permanecer no partido, ser devolvidos ou aparecer em canais que
o recorte direto exclui.

A dotação é uma referência externa do
[Tribunal Superior Eleitoral](https://www.tse.jus.br/eleicoes/eleicoes-2026-content/prestacao-de-contas/fundo-especial-de-financiamento-de-campanha-fefc).

## Âncoras externas e reconciliação

Antes de publicar um indicador, pelo menos uma grandeza deve ser reconciliada
com uma referência independente sempre que ela existir. Exemplos:

- dotação oficial do FEFC;
- eleitorado oficial por ciclo;
- 513 cadeiras de deputado federal;
- total de FEFC direto preservado entre os diferentes recortes;
- ausência de votos e resultados em um ciclo ainda não realizado.

Diferenças não são corrigidas por aproximação. Elas devem ser explicadas por
escopo, investigadas ou fazer a publicação falhar. Uma refatoração metodológica
só pode alterar números quando a mudança de definição estiver documentada.

## Limites de interpretação

As análises descrevem alocação declarada, não intenção, causalidade ou
regularidade jurídica definitiva. Em especial:

- despesas partidárias compartilhadas podem beneficiar candidaturas sem virar
  receita individual;
- voto de legenda não é atribuído artificialmente a candidaturas;
- valores são nominais e ainda não corrigidos pela inflação;
- siglas históricas ainda não são harmonizadas, exceto `PC DO B`/`PCDOB`;
- dados raciais e de gênero dependem da classificação publicada pelo TSE;
- fornecedor final exige normalização de CPF/CNPJ e nome antes de análise.

## Reprodutibilidade

O pipeline separa ingestão, publicação e análise. As análises leem Parquet e o
dashboard recebe apenas agregados sem nomes ou documentos. A validação mínima é:

```bash
make check
```

Para uma nova fotografia de 2026, a ordem é ingestão, derivação das dimensões,
publicação dos Parquet e exportação do dashboard. O JSON só deve ser commitado
depois das reconciliações e dos testes.
