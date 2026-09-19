# Observatório do Fundo Eleitoral

Dashboard responsivo em React/Vinext, com seis abas: visão geral, território,
representatividade, eficiência, fluxos e metodologia. Os filtros de ciclo,
partido e cargo usam agregados reais do dataset público do projeto.

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

O FEFC direto segue `consulta.cte_fefc`. Fluxos incluem as receitas declaradas
por canal, com avisos sobre auto-receitas e dupla contagem. A eficiência da UI
é limitada aos cargos proporcionais de turno único; os demais cargos não são
comparados. As classificações eleitorais herdadas seguem o snapshot do projeto.

WebMCP opcional: `filtrar_fundo_eleitoral` atualiza os filtros usando a mesma
interface. Navegadores sem suporte continuam funcionando normalmente. O
contrato não foi executado em um contexto WebMCP compatível nesta entrega.

Validação visual automatizada no navegador não foi realizada. O build de
produção, tipos TypeScript e testes de reconciliação dos agregados são os
controles desta entrega.
