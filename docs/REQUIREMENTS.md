# jsbsim-mcp — Requirements Specification (v1.0)

> 文档目的:把"把 JSBSim 封装为 MCP 服务并可视化"的项目,以软件工程化方式拆分为可执行、可验证、可商业化的需求集合。
>
> 状态: **Stable** | 版本: v1.0 | 日期: 2026-07-11
>
> 项目代号: **Falcon** | 关联产品: JSBSim v1.3.1 (LGPL-2.1) · MCP 2025-06-18 · Hugging Face Spaces

---

## 1. 业务背景

JSBSim 是事实标准的开源 6 自由度飞行动力学模型,广泛用于:
- 航空科研 (NASA/DARPA 验证基线)
- 无人机 SITL (ArduPilot、PX4)
- 强化学习训练 (gym-jsbsim、RL AFSIM)
- 飞行模拟器内核 (FlightGear、X-Plane、Unreal)

**痛点**:
1. C++ API 对 AI/Agent 调用不友好,Python 绑定 `jsbsim` 已存在但**没有标准 MCP 协议层**
2. 缺乏**自然语言驱动**仿真 + **实时可视化**的统一栈
3. 缺乏可托管的商业 SaaS(每次都需部署)

**机会**:MCP 协议 (Anthropic 主导) 已被 Claude/GPT/Cursor 广泛支持。把 JSBSim 暴露为 MCP,可一步打开 AI × 飞行仿真的中间件市场。

---

## 2. 项目目标

| 维度 | 目标 |
|---|---|
| **G1** | 任意支持 MCP 的 Agent(Claude Code / Claude Desktop / Cursor / Codex)通过 MCP JSON-RPC 调用 JSBSim |
| **G2** | 每个 session 提供 < **100 ms** 的端到端调用延迟(p95,GitHub-hosted HF Spaces) |
| **G3** | 每个 session 提供 **60 Hz** 实时仿真推步(纯 6DoF、无风/无环境的最坏情况) |
| **G4** | 浏览器端 Dashboard 实时三维 + 时序可视化,延迟 < **200 ms** |
| **G5** | Hugging Face Spaces 一键部署(零配置 SDK) |
| **G6** | 全部功能 LGPL-friendly,新代码 Apache-2.0 |

---

## 3. 角色与用例

### 3.1 角色

- **RP1 — 仿真工程师 / RL 研究员**:在 Claude Code 里说 "训练一架 C172 在顺风下起飞", 自动 trim → 仿真 → 采样
- **RP2 — 飞行教员 / 飞行员**:在 Claude Desktop 里问 "今天 KSFO 跑道 28R 进近的风切变是多少?", 自动加载 METAR + 仿真回答
- **RP3 — 集成商**:把 `jsbsim-fdm` MCP 加入其多层 MCP 栈(radar、weather、ATC)
- **RP4 — 学生 / 爱好者**:用 Web Dashboard 直接看到 Cessna 在地图上飞,无需本地安装

### 3.2 用例 (核心 UC)

| UC | 触发 | 期望结果 |
|---|---|---|
| UC-1 | RP1: "配置一架 c172x,海平面 95kt 平飞" | session 自动 trim 到 95kts, 推 1 分钟零推力初始状态 |
| UC-2 | RP2: "给我当前空速/高度/迎角" | MCP tool `get_property` 返回标量 |
| UC-3 | RP1: "拉 5 秒 8° 抬头,告诉我失速" | step 5 秒后 alpha 趋近临界, 报告 |
| UC-4 | RP4 打开 Web Dashboard | 自动重连到最新 session, 显示 PFD、轨迹、图表 |
| UC-5 | RP3: 接力调用 `weather_metar.py` + `jsbsim-fdm` | 多 MCP 协同:真实天气注入仿真 |

---

## 4. 功能需求 (FR)

### FR-1 · MCP Server 暴露

| ID | 名称 | 说明 |
|---|---|---|
| FR-1.1 | Tools 集 | `create_session` / `set_initial_conditions` / `trim` / `step` / `run_for` / `get_property` / `set_property` / `execute_script` / `list_aircraft` / `get_telemetry` / `close_session` |
| FR-1.2 | Resources 集 | `telemetry/{session_id}` · `trajectory/{session_id}` · `aircraft/{name}` · `engines/{name}` · `airports` |
| FR-1.3 | Prompts 集 | `setup_c172_cruise` · `simulate_stall_recovery` · `metar_wind_inject` |
| FR-1.4 | 多传输 | stdio (本地) **+** streamable_http (远程商业化) |
| FR-1.5 | 鉴权 | streamable_http: Bearer token(MCP header) |
| FR-1.6 | 错误处理 | 仿真错误 → MCP error code, 不崩溃 |

### FR-2 · 仿真引擎

| ID | 名称 | 说明 |
|---|---|---|
| FR-2.1 | 多 session 隔离 | 一个进程内可同时承载 N 个并发 session, 每 session 一份 FGFDMExec |
| FR-2.2 | TTL 回收 | 默认空闲 5 分钟自动 close, 避免资源耗尽 |
| FR-2.3 | 数值稳定 | 60Hz 步长下连续跑 1h 无累积漂移(SLA: < 1% 重量误差) |
| FR-2.4 | 飞机元数据 | 内置 c172x / a320 / f-16 / 737, 引擎、完整 IC 文件 |
| FR-2.5 | 标准大气 | US76 默认 + 外部可注入温度/压强剖面(用 Property node) |
| FR-2.6 | 风 | XML `<wind>` 解析; 支持 turbulence model 7 种 |
| FR-2.7 | 配平 | `trim mode=longitudinal` 等 6 种模式 |

### FR-3 · Web Dashboard

| ID | 名称 | 说明 |
|---|---|---|
| FR-3.1 | 主页 UI | 飞机选择 / IC 输入 / Step 控件 / Session ID 显示 |
| FR-3.2 | PFD | 主飞行显示:空速带、高度带、姿态仪、HSI、垂直速度 |
| FR-3.3 | 3D 视图 | Three.js + Cesium 全球地形 + 实时轨迹 |
| FR-3.4 | 时序图 | Plotly: altitude/airspeed/alpha/beta/thrust 历史 |
| FR-3.5 | WebSocket 推流 | 后端每 ~100ms 推一帧 telemetry |
| FR-3.6 | 录制 | 支持 CSV 一键下载 |

### FR-4 · 部署与运维

| ID | 名称 | 说明 |
|---|---|---|
| FR-4.1 | HF Spaces SDK 配置 | `sdk: docker` + `app_port: 7860` + `app_file: app.py` |
| FR-4.2 | Dockerfile | 多阶段,JSBSim v1.3.1 预编译 wheels 镜像层缓存 |
| FR-4.3 | 健康检查 | `/healthz` 200 OK + JSON-RPC ping |
| FR-4.4 | 文档 | USAGE.md / API.md / ARCHITECTURE.md |
| FR-4.5 | Demo | GIF 或视频占位 + README 截图 |

---

## 5. 非功能需求 (NFR)

### 5.1 性能 SLA

| 指标 | 目标 | 测量 |
|---|---|---|
| **P-1** | tool_call → response p95 | < 100 ms |
| **P-2** | 60Hz 仿真单步推进 | < 16 ms |
| **P-3** | Web Dashboard WS 推流 | < 200 ms |
| **P-4** | cold start (首次 access) | < 5 s |
| **P-5** | 三维渲染 | ≥ 30 fps |

### 5.2 可用性

- 99% 月度可用(HF Spaces SLA base)
- HF Spaces 免费 tier CPU 够 demo; 付费 tier 准备商业 SLA
- Session 资源隔离,一个 session OOM 不影响他人

### 5.3 兼容性

| 客户端 | stdio | streamable_http |
|---|---|---|
| Claude Code | ✅ | ✅ |
| Claude Desktop | ❌ | ✅ |
| Cursor | ✅ | ✅ |
| Codex CLI | ✅ | ✅ |
| 自研 Agent | ✅ | ✅ |

### 5.4 安全 / 合规

- **S-1** — JSON-RPC 输入按白名单 schema 校验(避免 path traversal)
- **S-2** — 仿真错误隔离(sandbox-like), 永不拖累 server 主循环
- **S-3** — Token 由 HF Space runtime secret 提供, 不写死 .env
- **S-4** — 输出仅文本 + JSON, 不暴露本机路径
- **S-5** — License 边界清晰:JSBSim 是 LGPL-2.1(进程内 C ABI 隔离), 新代码 Apache-2.0
- **S-6** — 不含军用 flight 战术决策上下文

### 5.5 可维护性

- 模块清晰分层:
  ```
  /Users/chenlei/Projects/jsbsim-mcp/
  ├── src/
  │   ├── server/      # MCP protocol layer
  │   ├── engine/      # jsbsim wrapper + session pool
  │   └── dashboard/   # FastAPI + 3D viz
  ```
- 关键路径单元测试 ≥ 80% 覆盖
- 0 个 lint error (ruff)
- 全 Python type hint,pyright strict

### 5.6 可移植性

- Python 3.10+ (HF Spaces 默认 3.11/3.12)
- 跨平台 docker(Debian-slim base)
- 不依赖 GPU
- 默认 512 MB 内存运行 demo

---

## 6. 验收标准 (AC)

| AC | 描述 | 验证方法 |
|---|---|---|
| AC-1 | `pip install` 后, 单一 `python server.py` 同时启动 stdio + HTTP | `python server.py` + `curl /healthz` |
| AC-2 | `claude_desktop_config.json` 配置后, Claude Desktop tools 列表出现 `jsbsim-fdm` 9 个 tool | 截图 |
| AC-3 | `python client_demo.py` 能完成 "C172 起飞 → 爬升 → 巡航 → 配平" 全流程 | 自动化 |
| AC-4 | Web Dashboard 在 https://USER- jsbsim-fdm.hf.space 公开访问, 出现 PFD | 浏览器 |
| AC-5 | 7 项 ACS test,e2e 99% | GitHub Actions |
| AC-6 | LICENSE 中 JSBSim-LGPL-2.1 + 本项目 Apache-2.0 双声明 | 文本审查 |
| AC-7 | 测试覆盖率 ≥ 80% | `pytest --cov` |
| AC-8 | README 截图/动图显示 UAV SIM 流程 | 链接 |
| AC-9 | 60Hz 10 分钟无内存累计增长 | `tracemalloc` |
| AC-10 | HF Spaces 公开 URL 可访问, 不超时 30s | uptime monitor |

---

## 7. 约束与依赖

### 7.1 外部依赖

| 组件 | 来源 | 版本 |
|---|---|---|
| JSBSim | JSBSim-Team/jsbsim | v1.3.1 (LGPL-2.1) |
| MCP SDK | modelcontextprotocol/python-sdk | ≥ 1.0 |
| jsbsim pip | PyPI | 1.3.1 |
| FastAPI | tiangolo | ≥ 0.115 |
| Three.js | npm/CDN | 0.169+ |
| Plotly.js | CDN | 3.x |
| Cesium | Apache-2.0 | 1.x (可选) |

### 7.2 资产策略

- **飞机数据**: 内置 JSBSim upstream `aircraft/` 目录(CC-BY-SA,commercial OK)
- **机场数据**: 内置 upstream `aircraft/` 目录中 `reset*.xml` + 我们的扫描
- **地理数据**: 三维地形初期不接, 二维地图用 Leaflet + OSM tiles

### 7.3 不在本期范围

- 不集成 FlightGear Unreal 等外部视景(给后续)
- 不接 GRIB2 / WRF
- 不做 wind field 二维网格查询
- 不做 RL 标准接口(Gymnasium); 留 TODO Phase 2

---

## 8. 风险与缓解

| 风险 | 严重度 | 缓解 |
|---|---|---|
| HF Spaces CPU 配额限制 | 高 | 60Hz 目标做默认; 大仿真建议付费 tier |
| 第三方 LLM 厂商升级可能破坏 MCP JSON-RPC | 中 | 定型 MCP 2025-06-18, 在 facade 层封装 |
| 仿真器内存 — HF 免费 tier 16GB | 中 | session 限额 + LRU |
| 三维渲染卡顿 | 低 | Cesium 改为可选 |
| JSBSim 官方重新组织目录 | 低 | 启动时验证必备路径, README 锁定 v1.3.1 |

---

## 9. 项目管理

| 阶段 | 时间 | 关键产物 |
|---|---|---|
| Phase 1 — MVP | M1 | requirements · design · basic MCP server · 1 dashboard page |
| Phase 2 — Hardening | M2 | 测试 · Dockerfile · HF Space URL |
| Phase 3 — Commercial | M3 | 性能优化 · 可选 C++ 桥 · 鉴权 |

---

> **END of document** — last edited 2026-07-11
