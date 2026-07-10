# Third-party notices

This project bundles or depends on the following open-source components.

## JSBSim (LGPL-2.1)

- Project: https://github.com/JSBSim-Team/jsbsim
- Version: 1.3.1 (May 17, 2026)
- License: **LGPL-2.1** (https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html)
- Use: bundled aircraft XML, engine models, atmosphere tables, and Python
  bindings installed via `pip install jsbsim`. The library is loaded as a
  separate C-extension, preserving LGPL compliance through dynamic linking.

## MCP Python SDK (MIT)

- Project: https://github.com/modelcontextprotocol/python-sdk
- License: **MIT**

## FastAPI / Starlette / Uvicorn (BSD-3-Clause / BSD-3-Clause / BSD-3-Clause)

- Projects: https://github.com/tiangolo/fastapi, https://github.com/encode/starlette, https://github.com/encode/uvicorn
- License: **BSD-3-Clause**

## Pydantic (MIT)

- Project: https://github.com/pydantic/pydantic
- License: **MIT**

## Aircraft data (CC-BY-SA from JSBSim authors)

- Distribution: under `jsbsim_data/aircraft/*` — used verbatim from
  JSBSim upstream.

## Three.js (MIT)

- Project: https://github.com/mrdoob/three.js
- License: **MIT**

## Plotly.js (MIT)

- Project: https://github.com/plotly/plotly.js
- License: **MIT**

---

Any modifications to JSBSim's XML files, when redistributed, must retain
JSBSim's LGPL notice and copyright. JSBSim binaries are loaded as a
separate Python C-extension module (no static linking), in accordance
with LGPL §6 ("Combined Work" provisions).
