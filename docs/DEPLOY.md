# Deploy to Hugging Face Spaces

This project ships as an HF Space using the **Docker SDK** — `Dockerfile`
copies everything (Python deps + JSBSim data) into a Debian-slim image.

## Steps

### 1. Create Space

Go to https://huggingface.co/new-space → **Docker** → name it e.g.
`jsbsim-mcp` → leave it empty for now.

### 2. Clone the Space

```bash
git clone https://huggingface.co/spaces/<you>/jsbsim-mcp
cd jsbsim-mcp
```

### 3. Copy project files

```bash
# From the project root, copy the runtime files only:
cp -r ../jsbsim-mcp/{app.py,src,run_stdio.py,docs,README.md,requirements.txt,Dockerfile,THIRD_PARTY_NOTICES.md,.gitignore,jsbsim_data} .
```

> `jsbsim_data/` is the bundled JSBSim aircraft directory (~30 MB
> uncompressed). For smaller bundle, only include the aircraft you ship
> — see `app.py` `--aircraft-set`.

### 4. Commit & push

```bash
git add . && git commit -m "Initial deploy"
git push
```

HF will:
1. Build the image from `Dockerfile`
2. Run `CMD ["uvicorn", "app:parent", "--host", "0.0.0.0", "--port", "7860"]`
3. Assign a URL like `https://<you>-jsbsim-mcp.hf.space`

### 5. Configure

In *Settings → Secrets* (optional):
- `PORT` (already 7860)
- `JBM_MAX_SESSIONS` (default 32)
- `JBM_IDLE_TTL` (default 300 seconds)
- `JBM_AUTH_TOKEN` (HF-encrypted bearer, optional — see `app.py`
  `verify_bearer_token` hook — Phase 2)

### 6. Smoke-test

```bash
curl -sf https://<you>-jsbsim-mcp.hf.space/healthz | jq
curl -sf https://<you>-jsbsim-mcp.hf.space/api/aircraft | jq '.aircraft | length'
```

### 7. Connect a Claude Desktop client

```json
{
  "mcpServers": {
    "jsbsim": {
      "url": "https://<you>-jsbsim-mcp.hf.space/mcp"
    }
  }
}
```

Claude will then list the 10 jsbsim-fdm tools.

---

## Resource / Cost

| Tier | CPU | RAM | Sessions | SLA |
|---|---|---|---|---|
| Free (Cpu) | 2 vCPU | 16 GB | 4 (recommend) | ~95% monthly |
| Upgrade | 8 vCPU | 32 GB | 16 | 99% |

Default config targets **free tier**: `JBM_MAX_SESSIONS=4`,
`JBM_IDLE_TTL=120`. Bump in *Secrets* if upgraded.

---

## Local Docker sanity-check

```bash
docker build -t jsbsim-mcp:dev .
docker run --rm -p 7860:7860 jsbsim-mcp:dev
curl -s http://localhost:7860/healthz | jq
```
