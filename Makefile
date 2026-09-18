# Atalhos do projeto. Ambiente efemero (Codespaces) costuma tornar a digitacao
# de comandos longos um problema -- colar nem sempre funciona no navegador.

ANO ?= 2022

.PHONY: setup verificar ingerir publicar tudo teste

setup:
	pip install -e '.[dev]'

verificar: setup
	python -m fundo_eleitoral.ingestao --verificar --ano $(ANO)

ingerir: setup
	python -m fundo_eleitoral.ingestao --ano $(ANO)

# REPO=usuario/nome make publicar
publicar: setup
	python -m fundo_eleitoral.publicacao --repo $(REPO) --ano $(ANO)

# Ingere e publica na sequencia: o Parquet nao pode ficar so na maquina
# efemera, senao some com ela (ADR-002).
tudo: ingerir publicar

teste:
	python -m pytest -q
