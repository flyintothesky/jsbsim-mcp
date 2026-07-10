# jsbsim-mcp — Architecture & Design (v1.0)

> 状态: Stable · 版本: v1.0 · 配套文档: `REQUIREMENTS.md`
>
> 模块边界清晰、接口契约严格,便于商业化部署与多人协作。

---

## 1. 总览

`jsbsim-mcp` 是**三进程/同进程并存**的架构,部署形态可拉伸:

```
                      ┌────────────────────────────────────────┐
   Claude Code /      │       jsbsim-mcp Server (HF Space)      │
   Claude Desktop /   │                                        │
   Cursor / Codex ───►│  ┌───────────────────────────────┐      │
   Web Browser        │  │   FastAPI / ASGI              │      │
        │             │  │   ┌────────────────────┐     │      │
        ▼             │  │   │ MCP streamable_http│◄────┼──────┤
   JSON-RPC 2.0       │  │   │ (port 8000)        │     │      │
   (stdio / HTTP /WS) │  │   └─────────┬──────────┘     │      │
        │             │  │             │                │      │
        │             │  │   ┌─────────▼──────────┐     │      │
        │             │  │   │ Web Dashboard      │◄────┼──────┤
        │             │  │   │ :7860 (HF default) │     │      │
        │             │  │   │  - REST API        │     │      │
        │             │  │   │  - WebSocket       │     │      │
        │             │  │   └─────────┬──────────┘     │      │
        │             │  │             │                │      │
        │             │  │   ┌─────────▼──────────┐     │      │
        │             │  │   │ core.engine        │     │      │
        │             │  │   │  - Session Pool    │     │      │
        │             │  │   │  - jsbsim wrapper  │     │      │
        │             │  │   │  - Streamer        │     │      │
        │             │  │   └─────────┬──────────┘     │      │
        │             │  │             │                │      │
        │             │  └─────────────┼────────────────┘      │
        │             │                │                       │
        │             │   ┌────────────▼────────────┐         │
        │             │   │ libJSBSim v1.3.1        │         │
        │             │   │ (C ABI, isolated dyn)   │         │
        │             │   └─────────────────────────┘         │
        │             │   ┌─────────────────────────┐         │
        │             │   │ jsbsim_data/ (aircraft  │         │
        │             │   │  engines systems)       │         │
        │             │   └─────────────────────────┘         │
                      └────────────────────────────────────────┘
```

**核心原则**:
1. 单进程多协议 (stdio + HTTP 同时提供; HF Spaces 优先 HTTP)
2. **LGPL 边界隔离**:JSBSim 通过 C ABI 调用,代码动态加载,不静态链接,新代码全部 Apache-2.0
3. **无状态协议 + 状态化引擎**:MCP tools 是幂等 request/response,Session Pool 在引擎内做 state

---

## 2. 模块划分

### 2.1 `src/server/` — MCP 层

| 文件 | 职责 |
|---|---|
| `mcp_app.py` | MCP 实例注册、tools / resources / prompts 注册 |
| `mcp_transports.py` | stdio runner + streamable_http FastAPI 集成 |
| `tools/*.py` | 每个 tool 一个文件:`create_session.py` / `step.py` / `get_property.py` / `trim.py` / ... |
| `resources/*.py` | `telemetry_resource.py` / `aircraft_resource.py` |
| `prompts/*.py` | 模板化提示词 |
| `schemas.py` | Pydantic 模型(JSON Schema 源) |

**接口契约(MCP tools)**:

```python
# 工具契约示例
class CreateSessionInput(BaseModel):
    aircraft: str = Field(description="e.g. c172x, a320, f16")
    initial_conditions: Optional[Dict[str, float]] = None
    sample_rate_hz: int = 60

class CreateSessionOutput(BaseModel):
    session_id: str              # UUID v4
    aircraft: str
    sim_time: float
    sample_rate: int
    dt: float
```

### 2.2 `src/engine/` — 仿真核心

| 文件 | 职责 |
|---|---|
| `session.py` | `JSBSimSession` 单架飞机的封装, lock 保护并发访问 |
| `pool.py` | `SessionPool` LRU + TTL 管理 |
| `catalog.py` | 扫描 `aircraft/` 列出可用飞机 |
| `telemetry.py` | `TelemetryFrame` 数据类,采样+广播 |
| `properties.py` | `JSBSim` 属性节点列表(1600+) |

**调用模型**:
```
MCP tool call -> engine.handle(action) -> session.execute(action)
                 -> FDMExec.run() (60Hz) -> telemetry_frame
                 -> Response.pydantic-validated
```

### 2.3 `src/dashboard/` — Web Dashboard

| 文件 | 职责 |
|---|---|
| `app.py` | FastAPI entrypoint |
| `ws.py` | WebSocket telemetry broadcaster |
| `static/index.html` | 单页应用 |
| `static/pfd.svg.js` | PFD SVG 组装 |
| `static/three_view.js` | Three.js 3D 视图 |
| `static/charts.js` | Plotly 时序图 |

---

## 3. 接口契约

### 3.1 MCP Tools (FR-1.1)

| Tool | 关键输入 | 关键输出 |
|---|---|---|
| `list_aircraft` | — | `["c172x", "a320", "f16", "737", "ball", ...]` |
| `create_session` | `aircraft`, `ic?`, `rate?` | `session_id`, `aircraft`, `dt` |
| `close_session` | `session_id` | `ok: true` |
| `set_initial_conditions` | `session_id`, `ic{}` | `ok`, `loaded` |
| `trim` | `session_id`, `mode` | `report` (alpha/thrust/elevator) |
| `step` | `session_id`, `seconds` | `frames_run`, `sim_time` |
| `get_property` | `session_id`, `path` | value / NaN |
| `set_property` | `session_id`, `path`, `value` | `ok` |
| `get_telemetry` | `session_id` | `TelemetryFrame` (60 fields) |
| `execute_script` | `session_id`, `script_xml_string` 或 path | `report` |

### 3.2 MCP Resources (FR-1.2)

| URI | Mime | 用途 |
|---|---|---|
| `jsbsim://aircraft` | application/json | 列出所有内置飞机 |
| `jsbsim://aircraft/{name}` | application/json | 特定飞机元数据 |
| `jsbsim://engines/{name}` | application/json | 引擎元数据 |
| `jsbsim://airports` | application/json | 已知跑道 |
| `jsbsim://sessions` | application/json | 当前活跃 session |
| `jsbsim://sessions/{sid}/telemetry` | application/json | 最新遥测 |
| `jsbsim://sessions/{sid}/trajectory` | application/json | 完整轨迹(运行后) |

### 3.3 MCP Prompts (FR-1.3)

| Name | Template |
|---|---|
| `cruise_c172` | "The user wants C172 cruising at altitude at airspeed Vc. Steps: 1) create_session 'c172x' 2) set_initial_conditions 3) trim mode=longitudinal 4) hold heading. Reply with telemetry each minute." |
| `stall_recovery` | "Stall recovery training: pull 8° nose up from level flight; report alpha; if alpha > 16° perform recovery pitch-down 5° + full throttle." |
| `metar_wind_inject` | "Inject METAR winds: parse wind direction/speed from {metar}, set property forces/wind-…-fps; rerun trim." |

---

## 4. 部署拓扑

### 4.1 本地开发 (stdio)

```
claude_code   <-->    python server.py (stdio)   <-->   jsbsim
```

### 4.2 HF Spaces (streamable_http)

```
client internet -> https://jsbsim-fdm.hf.space/mcp (HTTPS+token)
                  -> uvicorn :7860 -> MCP streamable_http
                  -> core.engine -> libJSBSim
```

---

## 5. 时序图(关键 UC)

### 5.1 create_session → step → get_telemetry

```
agent          MCP server            engine            JSBSim
 │                │                    │                  │
 │ create_session ─────►route───────►│                  │
 │                │  create(sid)     │ FGFDMExec(.load)│
 │◄──── sid ──────│                  │                  │
 │                │                    │                  │
 │ step(0.5s) ────►│                    │                  │
 │                │  loop 30*run()───►│ run*30 ────────►│
 │                │  telemetry[]     │ ◄──state──────────│
 │◄── frames:30 ──│                   │                  │
 │                │                    │                  │
 │ get_telemetry ─►│  snapshot() ─────►│                  │
 │◄── {...}───────│                    │                  │
```

### 5.2 Web Dashboard WebSocket

```
Browser             FastAPI                engine
 │                    │                       │
 │ WS open ─────────►│                       │
 │                    │ subscribe(sid) ─────►│
 │                    │                       │
 │                    │ stream 60Hz ◄────────│ run() loop
 │◄── frame ──────────│                       │
 │◄── frame ──────────│                       │
 │   ...              │                       │
```

---

## 6. 数据契约(TelemetryFrame)

```python
class TelemetryFrame(BaseModel):
    t: float                # sim time (sec)
    aircraft: str
    # 位置
    lat_deg: float
    lon_deg: float
    alt_ft: float
    altitude_agl_ft: Optional[float] = None
    # 姿态
    pitch_deg: float
    roll_deg: float
    heading_deg: float
    # 速度
    airspeed_kt: float
    ground_speed_kt: float
    mach: float
    # 相对气流
    alpha_deg: float
    beta_deg: float
    # 力
    thrust_lbs: float
    lift_lbs: float
    drag_lbs: float
    # 过载
    nz_g: float
    # 风
    wind_dir_deg: float
    wind_speed_kt: float
    # 引擎
    rpm: float
    fuel_remaining_lbs: float
    # 地面
    on_ground: bool
    gear_pos_norm: float
```

---

## 7. 可观测性(观测设计)

| 项 | 工具 |
|---|---|
| 日志 | 标准 logging + HF Space Logs |
| 指标 | `/metrics` Prometheus-style(JF-Phase 3) |
| Trace | MCP tool 调用追踪(每 tool 包装 decorator)|
| 健康 | `/healthz` 返回 200 + 关键指标 |

---

## 8. 商业化考虑

- **API 限制**(Phase 2):token 鉴权 + rate limit by session
- **多租户隔离**:HF Spaces 默认单用户, 升级 enterprise tier 时启用 namespace
- **统计 + 计费**(Phase 3):每个 tool call 记账, 量化 token 计费
- **License 双声明**:`THIRD_PARTY_NOTICES.md` 详细列出 JSBSim LGPL-2.1 自新代码 Apache-2.0

> **END of document** — last edited 2026-07-11
