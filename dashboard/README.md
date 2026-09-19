# Festa da Democracia

Dashboard responsivo em React/Vinext, com sete abas: visão geral, território,
representatividade, estratégia, eficiência, caminho do dinheiro e metodologia.
Os filtros de ciclo, partido e cargo usam agregados reais do dataset público do
projeto. A interface apresenta o Fundo Eleitoral em linguagem acessível; FEFC
permanece apenas onde a denominação técnica é necessária para o método.

## Desenvolvimento

Requer Node >=22.13 e pnpm. Execute `pnpm install` e `pnpm dev`.
Para validar: `pnpm exec tsc --noEmit`, `pnpm test` e `pnpm build`.

## Atualização dos dados

Na raiz do repositório Python:

```bash
PYTHONPATH=src python3 -m fundo_eleitoral.dashboard --destino dashboard/public/data.json
```

A exportação consulta os Parquet do Hugging Face e as dimensões do projeto.
Não contém nomes, documentos ou identificadores individuais. O JSON é uma
fotografia datada: não há atualização automática ao abrir a interface.

O fundo eleitoral direto segue `consulta.cte_fefc`. Fluxos incluem as receitas
declaradas por canal, com avisos sobre auto-receitas e dupla contagem. A aba de
estratégia reúne as métricas de concentração e renovação. A eficiência da UI é
limitada aos cargos proporcionais de turno único, exclui da ordenação partidos
sem repasse direto e não mede causalidade. Território usa cadeiras em disputa
como referência quando um único cargo está selecionado; em recortes amplos,
compara apenas com o eleitorado. As classificações eleitorais herdadas seguem o
snapshot do projeto.

WebMCP opcional: `filtrar_fundo_eleitoral` atualiza os filtros usando a mesma
interface. Navegadores sem suporte continuam funcionando normalmente. O
contrato não foi executado em um contexto WebMCP compatível nesta entrega.

O build de produção, tipos TypeScript e testes de reconciliação dos agregados
são os controles desta entrega. A interface também foi revisada visualmente em
desktop, tablet (768 px) e celular (390 px); os filtros, tabelas e abas mantêm
leitura sem corte de conteúdo nesses recortes.
