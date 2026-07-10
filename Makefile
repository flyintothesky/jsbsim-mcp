PY ?= python
PIP ?= pip

.PHONY: help install data run test fmt lint docker

help:
	@echo "jsbsim-mcp Makefile"
	@echo "  make install   install Python deps"
	@echo "  make data      download JSBSim aircraft data (≈30MB)"
	@echo "  make run       start the unified ASGI server (dashboard + MCP)"
	@echo "  make test      run pytest"
	@echo "  make docker    build Docker image"

install:
	$(PIP) install -r requirements.txt

data:
	@echo "Downloading bundled JSBSim aircraft data..."
	@mkdir -p jsbsim_data
	@curl -L -o /tmp/jsbsim.tgz https://github.com/JSBSim-Team/jsbsim/archive/refs/heads/master.tar.gz 2>/dev/null
	@tar -xzf /tmp/jsbsim.tgz --strip-components=1 -C jsbsim_data
	@echo "Done. Bundled in jsbsim_data/."

run:
	$(PY) app.py

test:
	PYTHONPATH=. pytest tests/

fmt:
	$(PY) -m black src tests
	$(PY) -m isort src tests

lint:
	$(PY) -m ruff check src tests

docker:
	docker build -t jsbsim-mcp:dev .
