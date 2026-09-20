# Atalhos do projeto. Ambiente efemero (Codespaces) costuma tornar a digitacao
# de comandos longos um problema -- colar nem sempre funciona no navegador.

ANO ?= 2022

.PHONY: setup verificar ingerir publicar tudo teste lint-python dashboard-check check checar-token

setup:
	pip install -e '.[dev]'

verificar: setup
	python -m fundo_eleitoral.ingestao --verificar --ano $(ANO)

ingerir: setup
	python -m fundo_eleitoral.ingestao --ano $(ANO)

# Falha antes do download, nao depois. Segredo do Codespaces so entra na
# maquina no boot: criar o segredo com a maquina ligada nao basta, e o erro
# so apareceria ao fim de centenas de MB de ingestao.
checar-token:
	@test -n "$$HF_TOKEN" || { \
	  echo "HF_TOKEN ausente. O segredo do Codespaces so e injetado quando a"; \
	  echo "maquina inicia -- pare e reabra o codespace, ou confira se o segredo"; \
	  echo "tem acesso a este repositorio em github.com/settings/codespaces."; \
	  exit 1; }

# REPO=usuario/nome make publicar
publicar: setup checar-token
	python -m fundo_eleitoral.publicacao --repo $(REPO) --ano $(ANO)

# Ingere e publica na sequencia: o Parquet nao pode ficar so na maquina
# efemera, senao some com ela (ADR-002).
tudo: checar-token ingerir publicar

teste:
	python -m pytest -q

lint-python:
	python -m ruff check src tests

dashboard-check:
	pnpm --dir dashboard check

check: teste lint-python dashboard-check
