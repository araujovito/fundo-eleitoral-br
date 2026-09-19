# Eficiência eleitoral

## Pergunta

Quantos reais de FEFC repassado diretamente pelo partido foram necessários por
voto nominal obtido pelas candidaturas?

## Método

O indicador é `FEFC direto / votos nominais`, agregável por partido, UF, cargo
e perfil de resultado (`eleito` ou `nao_eleito`). A análise parte de todas as
candidaturas do recorte, incluindo quem recebeu fundo mas não recebeu voto.
Por isso, uma campanha sem votos eleva o custo do seu grupo; se todo o grupo
não tiver voto, o resultado é mostrado como `sem votos`, nunca como zero.

O denominador não inclui voto de legenda. Esse voto pertence ao partido em uma
eleição proporcional, mas não identifica a candidatura que recebeu o recurso;
somá-lo às pessoas reduziria artificialmente o custo por voto nominal.

Para disputas de dois turnos, a dimensão usa apenas o último turno de cada
candidatura. Somar primeiro e segundo turnos contaria duas vezes os votos de
Presidência e governos.

## Cobertura e limites

`dados/dimensoes/votos_candidatos.parquet` contém os totais por candidatura
nos resultados oficiais de 2018 e 2022. Os valores vêm da soma de
`QT_VOTOS_NOMINAIS` em `votacao_candidato_munzona_<ano>_BRASIL.csv`, disponível
nos arquivos públicos do [TSE](https://dadosabertos.tse.jus.br/); `NR_TURNO`
foi usado para preservar apenas o maior turno de cada candidatura.

Ainda não há resultados de 2026. O módulo recusa o ano em vez de comparar uma
prestação de contas parcial com votos inexistentes.

Como nos outros recortes, transferências entre candidaturas ficam fora do FEFC
direto ([ADR-009](decisoes.md#adr-009--repasse-entre-candidaturas-fica-fora-da-concentração)).
