# Contributing

Thanks for your interest in contributing to jsbsim-mcp.

## Ground rules

- Code is Apache-2.0. By contributing you agree to license under Apache-2.0.
- Don't bundle JSBSim source modifications here — file upstream PRs at
  https://github.com/JSBSim-Team/jsbsim. We depend on the upstream binary.
- Keep changes scoped. One concern per PR.
- Add tests where you change engine or MCP surface.
- Update `docs/API.md` if you change the MCP public surface.

## Setup

```bash
git clone <repo>
cd jsbsim-mcp
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Bundle JSBSim aircraft data (≈30 MB)
mkdir -p jsbsim_data
curl -L https://github.com/JSBSim-Team/jsbsim/archive/refs/heads/master.tar.gz \
  | tar --strip-components=1 -C jsbsim_data -xz
```

## Run tests

```bash
PYTHONPATH=. pytest tests/
```

20 tests should pass.

## Coding style

- Python: ruff (line-length 100)
- Python type hints everywhere
- JS/HTML/CSS in static/: no transpiler; align with the existing three.js
  ESM dynamic-import fallback pattern.

## Release process

1. Bump `__version__` in `src/server/registry.py` + `app.py`
2. Update `CHANGELOG.md`
3. Tag `v0.x.y`
4. Push to GitHub; describe in PR

## Reporting issues

- Use GitHub Issues on the public repo
- For security: see SECURITY.md

## License header

Source files should include the Apache-2.0 boilerplate (LICENSE file).
JSBSim modifications MUST NOT enter this repo — keep upstream clean.
