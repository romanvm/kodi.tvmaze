lint:
	. .venv/bin/activate && \
	pylint metadata.tvmaze/libs metadata.tvmaze/main.py

PHONY: lint
