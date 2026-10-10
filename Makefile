.PHONY: run test check smoke docker
run:
	uvicorn app.main:app --host 127.0.0.1 --port 8000

test:
	python -m pytest

check:
	python -m compileall -q app
	python -m pytest

smoke:
	python -m app.cli version
	python -m app.cli bazi --date 2000-08-16T04:00

docker:
	docker compose up --build

.PHONY: vault-check
vault-check:
	node tests/vault_smoke.cjs

.PHONY: release verify-release
release:
	python scripts/build_release.py

verify-release:
	python scripts/build_release.py --verify ../xuanshu-v.0.1.0.zip
