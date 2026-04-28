.PHONY: seed dev test pack import

seed:
	@echo "Copying shared fixtures into local backend/data ..."
	@cp -r ../shared-fixtures/*.json backend/data/
	@cp -r ../shared-fixtures/policies backend/data/
	@echo "Done."

dev: seed
	python3 -m venv .venv >/dev/null 2>&1 || true
	. .venv/bin/activate && pip install -q -r backend/requirements.txt
	. .venv/bin/activate && cd backend && uvicorn app.main:app --port 8000

test:
	python3 -m venv .venv >/dev/null 2>&1 || true
	. .venv/bin/activate && pip install -q -r backend/requirements.txt pytest
	. .venv/bin/activate && pytest -q tests

pack:
	pac solution pack --zipfile out/ContosoHrConcierge.zip --folder solution --packagetype Both

import: pack
	pac solution import --path out/ContosoHrConcierge.zip --activate-plugins --publish-changes
