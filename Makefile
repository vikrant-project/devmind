.PHONY: install test mvp v1 bench clean
install:
	pip install -e ".[dev]"
test:
	pytest tests/ -v --tb=short
mvp:
	pytest tests/mvp/ -v --tb=short
v1:
	pytest tests/v1/ -v --tb=short
bench:
	devmind benchmark --suite mvp
clean:
	rm -rf .venv build dist *.egg-info workspaces/* .pytest_cache
