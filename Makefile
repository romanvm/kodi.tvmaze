PHONY: lint, format, ruff, test

lint:
	. .venv/bin/activate && ruff check

format:
	. .venv/bin/activate && ruff format

ruff:
	. .venv/bin/activate && ruff check --fix && ruff format

test:
	. .venv/bin/activate && pytest
