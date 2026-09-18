"""Etapa 1 do pipeline: baixar os ZIPs do TSE e converter para Parquet.

Roda raro (so quando o TSE publica dado novo) e e a UNICA etapa que toca a rede
ou escreve muito em disco. A analise le exclusivamente os Parquet resultantes --
ver docs/decisoes.md (ADR-001).

Uso:
    python -m fundo_eleitoral.ingestao --verificar            # so checa as URLs
    python -m fundo_eleitoral.ingestao --ano 2022             # baixa e converte
    python -m fundo_eleitoral.ingestao --ano 2022 --manter-zip
"""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

import httpx
import polars as pl

from .fontes import DIALETO_TSE, Fonte, todas_fontes

# O CDN do TSE recusa user-agents de biblioteca. Nao e contorno de protecao:
# os dados sao publicos e o proprio portal oferece o link para download direto.
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"

RAIZ = Path(__file__).resolve().parents[2]
DIR_DADOS = RAIZ / "dados"
DIR_BRUTO = DIR_DADOS / "bruto"
DIR_PARQUET = DIR_DADOS / "parquet"


def verificar(fontes: list[Fonte]) -> int:
    """Confere se cada URL do catalogo existe. Retorna quantas falharam."""
    falhas = 0
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=30) as c:
        for f in fontes:
            try:
                r = c.head(f.url)
                if r.status_code >= 400:
                    r = c.get(f.url, headers={"Range": "bytes=0-1023"})
                tamanho = r.headers.get("content-length", "?")
                ok = r.status_code < 400
                print(f"{'OK ' if ok else 'ERRO'} {r.status_code:>3} {tamanho:>12}  {f.chave}")
                falhas += 0 if ok else 1
            except httpx.HTTPError as e:
                print(f"ERRO  --            ?  {f.chave}: {e}")
                falhas += 1
    return falhas


def baixar(fonte: Fonte, destino: Path) -> Path:
    destino.mkdir(parents=True, exist_ok=True)
    alvo = destino / f"{fonte.chave}.zip"
    if alvo.exists() and alvo.stat().st_size > 0:
        print(f"  ja baixado: {alvo.name}")
        return alvo

    parcial = alvo.with_suffix(".zip.parcial")
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=None) as c:
        with c.stream("GET", fonte.url) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            baixado = 0
            with parcial.open("wb") as fh:
                for bloco in r.iter_bytes(1 << 20):
                    fh.write(bloco)
                    baixado += len(bloco)
                    if total:
                        pct = 100 * baixado / total
                        print(f"\r  {fonte.chave}: {pct:5.1f}%", end="", flush=True)
    print()
    parcial.rename(alvo)
    return alvo


def _ler_csv(caminho: Path) -> pl.DataFrame:
    """Le um CSV do TSE ja normalizando o dialeto (latin-1, ';', decimal ',')."""
    df = pl.read_csv(
        caminho,
        separator=DIALETO_TSE["separator"],
        encoding=DIALETO_TSE["encoding"],
        null_values=DIALETO_TSE["null_values"],
        infer_schema_length=0,  # tudo como string; tipagem e decisao da etapa 2
        truncate_ragged_lines=True,
    )
    return df.rename({c: c.strip().lower() for c in df.columns})


def converter(zip_path: Path, fonte: Fonte, destino: Path) -> list[Path]:
    """Extrai os CSVs de interesse e grava um Parquet por prefixo."""
    destino.mkdir(parents=True, exist_ok=True)
    escritos: list[Path] = []

    with zipfile.ZipFile(zip_path) as z:
        nomes = [n for n in z.namelist() if n.lower().endswith(".csv")]
        for prefixo in fonte.prefixos_csv:
            membros = [n for n in nomes if Path(n).name.lower().startswith(prefixo.lower())]
            if not membros:
                print(f"  aviso: nenhum CSV com prefixo '{prefixo}' em {zip_path.name}")
                continue

            partes: list[pl.DataFrame] = []
            for nome in membros:
                tmp = destino / "_tmp.csv"
                with z.open(nome) as origem, tmp.open("wb") as saida:
                    shutil.copyfileobj(origem, saida)
                partes.append(_ler_csv(tmp))
                tmp.unlink()

            # UFs diferentes as vezes trazem colunas a mais; diagonal alinha por nome.
            df = pl.concat(partes, how="diagonal_relaxed")
            alvo = destino / f"{prefixo}.parquet"
            df.write_parquet(alvo, compression="zstd")
            print(f"  {alvo.name}: {df.height:,} linhas x {df.width} colunas".replace(",", "."))
            escritos.append(alvo)

    return escritos


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Ingestao dos dados abertos do TSE")
    p.add_argument("--ano", type=int, action="append", help="ano eleitoral (repetivel)")
    p.add_argument("--verificar", action="store_true", help="so testa as URLs do catalogo")
    p.add_argument("--manter-zip", action="store_true", help="nao apaga o ZIP apos converter")
    args = p.parse_args(argv)

    anos = tuple(args.ano) if args.ano else (2022,)
    fontes = todas_fontes(anos)

    if args.verificar:
        falhas = verificar(fontes)
        print(f"\n{len(fontes) - falhas}/{len(fontes)} fontes acessiveis")
        return 1 if falhas else 0

    for fonte in fontes:
        print(f"[{fonte.chave}]")
        try:
            zip_path = baixar(fonte, DIR_BRUTO)
        except httpx.HTTPError as e:
            print(f"  falhou: {e}")
            continue
        converter(zip_path, fonte, DIR_PARQUET / str(fonte.ano))
        if not args.manter_zip:
            zip_path.unlink()
            print(f"  zip removido (use --manter-zip para conservar)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
