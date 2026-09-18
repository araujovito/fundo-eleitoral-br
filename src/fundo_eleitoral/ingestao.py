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

import polars as pl
from curl_cffi import requests

from .fontes import DIALETO_TSE, Fonte, todas_fontes

# O CDN do TSE fica atras de um bot manager que classifica o cliente pela
# impressao digital do handshake TLS, nao pelo User-Agent: httpx e curl levam
# 403 mesmo se declararem ser o Chrome. curl_cffi reproduz o handshake do
# Chrome e a requisicao passa. Ver docs/decisoes.md (ADR-005).
IMPERSONATE = "chrome"

RAIZ = Path(__file__).resolve().parents[2]
DIR_DADOS = RAIZ / "dados"
DIR_BRUTO = DIR_DADOS / "bruto"
DIR_PARQUET = DIR_DADOS / "parquet"


def verificar(fontes: list[Fonte]) -> int:
    """Confere se cada URL do catalogo existe. Retorna quantas falharam."""
    falhas = 0
    with requests.Session(impersonate=IMPERSONATE) as c:
        for f in fontes:
            try:
                # Range de 1 KB em vez de HEAD: o CDN responde 403 a HEAD mesmo
                # quando o GET passa, e o range revela o tamanho real via
                # content-range sem baixar o arquivo.
                r = c.get(f.url, headers={"Range": "bytes=0-1023"}, timeout=30)
                ok = r.status_code < 400
                tamanho = r.headers.get("content-range", "/?").split("/")[-1]
                assinatura = r.content[:2] == b"PK" if ok else False
                marca = "OK " if ok and assinatura else ("?  " if ok else "ERRO")
                print(f"{marca} {r.status_code:>3} {tamanho:>12}  {f.chave}")
                falhas += 0 if (ok and assinatura) else 1
            except Exception as e:
                print(f"ERRO  --            ?  {f.chave}: {type(e).__name__}: {e}")
                falhas += 1
    return falhas


def baixar(fonte: Fonte, destino: Path) -> Path:
    destino.mkdir(parents=True, exist_ok=True)
    alvo = destino / f"{fonte.chave}.zip"
    if alvo.exists() and alvo.stat().st_size > 0:
        print(f"  ja baixado: {alvo.name}")
        return alvo

    parcial = alvo.with_suffix(".zip.parcial")
    with requests.Session(impersonate=IMPERSONATE) as c:
        r = c.get(fonte.url, stream=True, timeout=None)
        if r.status_code >= 400:
            raise RuntimeError(f"{fonte.url} respondeu {r.status_code}")
        total = int(r.headers.get("content-length", 0))
        baixado = 0
        with parcial.open("wb") as fh:
            for bloco in r.iter_content(1 << 20):
                fh.write(bloco)
                baixado += len(bloco)
                if total:
                    pct = 100 * baixado / total
                    print(f"\r  {fonte.chave}: {pct:5.1f}%", end="", flush=True)
    print()
    parcial.rename(alvo)
    return alvo


def _ler_csv(caminho: Path) -> pl.DataFrame:
    """Le um CSV do TSE ja normalizando o dialeto (latin-1, ';')."""
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
    """Extrai o CSV _BRASIL de cada tabela e grava um Parquet por tabela.

    Usa exclusivamente os arquivos _BRASIL. Ver ADR-006: os arquivos por UF
    sao um subconjunto -- omitem as candidaturas de ambito nacional
    (SG_UF = 'BR'), que em 2022 eram 58% das linhas de receita, e nao ha
    arquivo proprio para o DF.
    """
    destino.mkdir(parents=True, exist_ok=True)
    escritos: list[Path] = []

    with zipfile.ZipFile(zip_path) as z:
        por_base = {Path(n).name: n for n in z.namelist()}
        for tabela in fonte.tabelas:
            alvo_csv = fonte.arquivo_de(tabela)
            membro = por_base.get(alvo_csv)
            if membro is None:
                print(f"  aviso: {alvo_csv} nao esta em {zip_path.name}")
                continue

            tmp = destino / "_tmp.csv"
            with z.open(membro) as origem, tmp.open("wb") as saida:
                shutil.copyfileobj(origem, saida)
            df = _ler_csv(tmp)
            tmp.unlink()

            alvo = destino / f"{tabela}.parquet"
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
        except Exception as e:
            print(f"  falhou: {e}")
            continue
        converter(zip_path, fonte, DIR_PARQUET / str(fonte.ano))
        if not args.manter_zip:
            zip_path.unlink()
            print(f"  zip removido (use --manter-zip para conservar)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
