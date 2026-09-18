"""Etapa 3 do pipeline: publicar os Parquet num dataset do Hugging Face.

Existe porque a ingestao roda em maquina efemera (Codespaces hiberna e e
descartado depois de 30 dias parado). Sem esta etapa, o resultado de um
download de centenas de MB morre junto com o container -- ver ADR-002.

Uso:
    python -m fundo_eleitoral.publicacao --repo usuario/fundo-eleitoral-br
    HF_TOKEN=hf_xxx python -m fundo_eleitoral.publicacao --repo usuario/nome
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

from .fontes import ANOS_ELEICAO
from .ingestao import DIR_PARQUET

CARTAO = """---
license: odc-by
language: [pt]
tags: [brazil, elections, campaign-finance, tse, politics]
pretty_name: Fundo Eleitoral e Fundo Partidario - prestacao de contas do TSE
---

# Fundo Eleitoral e Fundo Partidario (TSE)

Prestacao de contas eleitorais publicada pelo Tribunal Superior Eleitoral,
convertida de CSV para Parquet sem alteracao de conteudo.

Gerado por [{repo_codigo}]({repo_codigo_url}) em {data}.

## O que tem aqui

Um Parquet por tabela, por ciclo eleitoral, em `parquet/<ano>/`:

| tabela | o que e |
|---|---|
| `receitas_candidatos` | receitas declaradas por candidatura |
| `receitas_candidatos_doador_originario` | origem real por tras do doador intermediario |
| `despesas_contratadas_candidatos` | compromissos assumidos |
| `despesas_pagas_candidatos` | desembolsos efetivos |
| `receitas_orgaos_partidarios` | receitas dos diretorios (nacional, estadual, municipal) |
| `receitas_orgaos_partidarios_doador_originario` | idem, origem real |
| `despesas_contratadas_orgaos_partidarios` | compromissos dos diretorios |
| `despesas_pagas_orgaos_partidarios` | desembolsos dos diretorios |
| `consulta_cand` | cadastro das candidaturas (cargo, genero, raca, situacao) |

Ciclos: {anos}. O ciclo de 2026 esta em **prestacao parcial** -- a final so e
publicada apos a eleicao.

## Tres avisos antes de somar qualquer coisa

1. **`despesas_contratadas` nao e `despesas_pagas`.** Sao tabelas distintas e
   divergem: contratado e compromisso, pago e desembolso. Escolha
   explicitamente qual responde a sua pergunta.
2. **Transferencias entre diretorios causam dupla contagem.** O repasse
   nacional -> estadual -> candidato aparece nas tres pontas. Tratar como grafo,
   nao como soma.
3. **Todo campo e string.** A tipagem foi deixada para quem consome, de
   proposito: o schema do TSE nao e estavel entre anos e a inferencia
   automatica diverge entre arquivos do mesmo ciclo.

## Sobre a origem dos arquivos

Foram usados exclusivamente os CSV `_BRASIL` de cada tabela. Os arquivos por UF
publicados pelo TSE **nao sao uma particao**: em `receitas_candidatos_2022` as
26 UFs somam 271.352 linhas contra 674.944 do consolidado, e a diferenca sao as
candidaturas de ambito nacional (`SG_UF = 'BR'`) -- a eleicao presidencial. Nao
ha arquivo proprio para o DF.

## Como ler

```python
import duckdb
duckdb.sql("SELECT * FROM 'parquet/2022/receitas_candidatos.parquet' LIMIT 5")
```

## Licenca e fonte

Dados publicos do TSE, obtidos em <https://dadosabertos.tse.jus.br>. A conversao
nao altera conteudo. Credite o TSE como fonte primaria.
"""

REPO_CODIGO = "araujovito/fundo-eleitoral-br"


def montar_cartao(anos: tuple[int, ...]) -> str:
    return CARTAO.format(
        data=date.today().isoformat(),
        anos=", ".join(str(a) for a in anos),
        repo_codigo=REPO_CODIGO,
        repo_codigo_url=f"https://github.com/{REPO_CODIGO}",
    )


def publicar(repo: str, token: str | None, origem: Path, anos: tuple[int, ...]) -> int:
    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("huggingface_hub nao instalado. Rode: pip install -e '.[dev]'")
        return 1

    if not origem.exists() or not any(origem.rglob("*.parquet")):
        print(f"nada para publicar em {origem} -- rode a ingestao antes")
        return 1

    api = HfApi(token=token)
    api.create_repo(repo_id=repo, repo_type="dataset", exist_ok=True, private=False)

    cartao = origem.parent / "README.md"
    cartao.write_text(montar_cartao(anos), encoding="utf-8")

    arquivos = sorted(origem.rglob("*.parquet"))
    total_mb = sum(a.stat().st_size for a in arquivos) / 1e6
    print(f"publicando {len(arquivos)} arquivos ({total_mb:.1f} MB) em {repo}")

    api.upload_file(
        path_or_fileobj=str(cartao),
        path_in_repo="README.md",
        repo_id=repo,
        repo_type="dataset",
    )
    api.upload_folder(
        folder_path=str(origem),
        path_in_repo="parquet",
        repo_id=repo,
        repo_type="dataset",
        allow_patterns=["**/*.parquet"],
    )
    print(f"pronto: https://huggingface.co/datasets/{repo}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Publica os Parquet no Hugging Face")
    p.add_argument("--repo", default=os.environ.get("HF_REPO"),
                   help="destino no formato usuario/nome (ou defina HF_REPO)")
    p.add_argument("--ano", type=int, action="append", help="anos presentes (so rotula o cartao)")
    args = p.parse_args(argv)

    if not args.repo:
        print("informe --repo usuario/nome (ou defina HF_REPO)")
        return 2

    token = os.environ.get("HF_TOKEN")
    if not token:
        # huggingface-cli login grava o token em ~/.cache/huggingface; o HfApi
        # encontra sozinho. So avisamos para o erro nao chegar cru.
        print("HF_TOKEN nao definido -- usando credencial de 'huggingface-cli login', se houver")

    anos = tuple(args.ano) if args.ano else ANOS_ELEICAO
    return publicar(args.repo, token, DIR_PARQUET, anos)


if __name__ == "__main__":
    sys.exit(main())
