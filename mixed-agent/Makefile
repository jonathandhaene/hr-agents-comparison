.PHONY: seed dev test deploy

PYTHON ?= python3

seed:
	@mkdir -p backend/data
	@cp -r ../shared-fixtures/*.json backend/data/
	@cp -r ../shared-fixtures/policies backend/data/
	@echo "Seeded backend/data from shared-fixtures."

dev: seed
	@echo "Starting Functions host on :7071. Run 'make foundry-dev' in another shell for the connected agent REPL."
	cd backend && func start

foundry-dev:
	$(PYTHON) -m pip install -q -r foundry/agent/requirements.txt
	HR_API_BASE=http://localhost:7071 $(PYTHON) -m foundry.agent.main

test: seed
	$(PYTHON) -m pip install -q -r backend/requirements.txt pytest
	$(PYTHON) -m pytest -q tests

deploy:
	@echo "Use the GitHub Actions workflow ../.github/workflows/mixed.yml"
