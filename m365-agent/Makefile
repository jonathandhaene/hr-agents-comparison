.PHONY: seed dev test deploy

PYTHON ?= python3

seed:
	@echo "Copying shared fixtures into local backend/data ..."
	@cp -r ../shared-fixtures/*.json backend/data/
	@cp -r ../shared-fixtures/policies backend/data/
	@echo "Done."

dev: seed
	@echo "Starting backend (8000) and agent (3978) locally ..."
	$(PYTHON) -m venv .venv >/dev/null 2>&1 || true
	. .venv/bin/activate && pip install -q -r backend/requirements.txt -r src/requirements.txt
	. .venv/bin/activate && (cd backend && uvicorn app.main:app --port 8000 &) && \
		(cd src && HR_API_BASE=http://localhost:8000 DISABLE_GRAPH=1 $(PYTHON) -m agent)

test:
	$(PYTHON) -m venv .venv >/dev/null 2>&1 || true
	. .venv/bin/activate && pip install -q -r backend/requirements.txt -r src/requirements.txt pytest pytest-asyncio
	. .venv/bin/activate && pytest -q tests

deploy:
	@echo "Use the GitHub Actions workflow ../.github/workflows/m365-agent.yml"
