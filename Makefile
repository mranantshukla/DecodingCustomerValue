# Convenience targets. On Windows, run the underlying commands directly or use `make` via Git Bash / WSL.
.PHONY: help install pipeline test lint format dashboard glossary clean

help:
	@echo "install    Install the project with all extras (editable)"
	@echo "pipeline   Run the full end-to-end pipeline"
	@echo "test       Run the test suite"
	@echo "lint       Ruff lint"
	@echo "format     Black + ruff --fix"
	@echo "dashboard  Launch the Streamlit app"
	@echo "glossary   Regenerate docs/FEATURE_GLOSSARY.md from the registry"
	@echo "clean      Remove generated artefacts"

install:
	pip install -e ".[all]"

pipeline:
	python -m src.pipeline

test:
	pytest -q

lint:
	ruff check src tests scripts config

format:
	black src tests scripts config
	ruff check --fix src tests scripts config

dashboard:
	streamlit run src/dashboard/app.py

glossary:
	python scripts/generate_glossary.py

clean:
	rm -rf data/processed/*.db data/processed/*.csv reports/sql_exports reports/*.md reports/*.json
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
