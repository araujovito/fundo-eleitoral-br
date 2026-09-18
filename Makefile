# Atalhos do projeto. Ambiente efemero (Codespaces) costuma tornar a digitacao
# de comandos longos um problema -- colar nem sempre funciona no navegador.

.PHONY: setup verificar ingerir teste

setup:
	pip install -e '.[dev]'

verificar: setup
	python -m fundo_eleitoral.ingestao --verificar --ano 2022

ingerir: setup
	python -m fundo_eleitoral.ingestao --ano 2022

teste:
	python -m pytest -q
