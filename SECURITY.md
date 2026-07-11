# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 0.1.x  | ✅ Active |
| older   | ❌ Please upgrade |

## Reporting a Vulnerability

**Please email** `security@jsbsim-mcp.local` (placeholder — replace with
your real address when launching).

**Do not** open public GitHub issues for security-sensitive disclosures.

Please include:
- A clear description of the vulnerability
- Reproduction steps or a minimal PoC
- Potential impact (RCE, info disclosure, privilege escalation, etc.)
- Suggested fix if you have one

We aim to acknowledge within 72 hours and patch critical issues within 7 days.

## Threat Model

`jsbsim-mcp` is a deterministic flight-dynamics simulator exposed via MCP.
Primary risks:

1. **Remote code execution** via JSBSim XML loader (a malformed .xml
   could exploit expat). Mitigation: the loader runs in the same
   process as the worker; no path-traversal to outside `JBSIM_ROOT`.
2. **CPU/memory exhaustion** via many concurrent sessions.
   Mitigation: `JBM_MAX_SESSIONS` env, default 32.
3. **Token leakage** if user pastes secret in chat.
   Mitigation: rotate & revoke; never paste tokens in conversation.
4. **LGPL compliance boundary**: JSBSim is loaded as a dynamic C
   extension, not statically linked. License notice propagated through
   `THIRD_PARTY_NOTICES.md`.

## Hardening Checklist (for self-hosters)

- [ ] Set `JBM_AUTH_TOKEN` and gate `app.py` with bearer middleware.
- [ ] Set `JBM_MAX_SESSIONS=4` on free-tier HF spaces.
- [ ] Set `JBM_IDLE_TTL=120` to recycle idle sessions promptly.
- [ ] Disable JSBSim's `console` output in production (set quiet
      verbose flags).
- [ ] Use reverse proxy (nginx / Cloudflare) for TLS + rate limiting.
