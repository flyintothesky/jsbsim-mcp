# 在魔搭社区部署 jsbsim-mcp

> 完整中文部署说明。把这个仓库推到 GitHub 后,即可在魔搭创建你的 MCP 服务。

## 0. 前置准备

- 一个 GitHub 公开仓库(本项目 `jsbsim-mcp`)
- 一个 ModelScope 账号(https://www.modelscope.cn)
- 10 分钟时间

## 1. 推送代码到 GitHub

```bash
git init
git add -A
git commit -m "Initial: jsbsim-mcp v0.1.0"
git branch -M main
git remote add origin https://github.com/<your-name>/jsbsim-mcp.git
git push -u origin main
```

## 2. 访问魔搭 MCP 创建页

URL: https://www.modelscope.cn/mcp/create (或 「MCP 广场 → 创建服务」)

按页面提示填写:

| 字段 | 填什么 |
|---|---|
| **服务名称** | `jsbsim-fdm`(英文短名) |
| **中文名** | `JSBSim 飞行动力学仿真`(中文别名) |
| **描述(中文)** | 见下方"描述模板" |
| **标签** | `飞行仿真`, `FDM`, `aircraft`, `simulation`, `physics` |
| **类别** | `developer-tools` 或 `science-engineering` |
| **服务 Logo URL** | (可选,留空) |
| **服务图标 URL** | (可选) |
| **服务仓库链接** | 你的 GitHub 仓 URL: `https://github.com/<your-name>/jsbsim-mcp` |
| **服务部署方式** | **Hosted MCP (HTTP streamable_http)** |
| **服务 URL** | 你的实例 URL:`https://<github-pages-or-cf-deployment>.example.com/mcp` |
| **鉴权** | `无需 token` (默认) |
| **环境变量** | 见下方"环境变量" |

### 描述模板(粘贴此段)

```
JSBSim 飞行动力学仿真 MCP 服务

把业界标准的开源 6 自由度飞行动力学模型(JSBSim v1.3.1)封装为 MCP 协议,
让 Claude / Cursor / Codex 等任何支持 MCP 的智能体能用自然语言驱动 C172、A320、
F-16 等 60 款飞机的实时仿真。

内置 Web Dashboard(PFD、3D 姿态、时序图、WebSocket 推流)。

★ 10 个 MCP 工具
• list_aircraft, create_session, close_session
• set_initial_conditions, trim, step
• get_property, set_property, get_telemetry
• execute_script

★ 7 个 MCP 资源
• jsbsim://aircraft
• jsbsim://aircraft/{name}
• jsbsim://engines
• jsbsim://sessions
• jsbsim://sessions/{sid}/telemetry

★ 2 个 MCP Prompt
• cruise_c172 (巡航训练)
• stall_recovery (失速恢复)

License: Apache-2.0(主体) + LGPL-2.1(JSBSim 依赖)
```

### 环境变量(全部默认即可)

无强制 env。生产环境推荐:

```
JBM_MAX_SESSIONS=32   # session pool 上限
JBM_IDLE_TTL=300      # 空闲 5 分钟自动关闭
JBM_AUTH_TOKEN=...    # (可选)Bearer token
```

## 3. 获取部署 URL

提交后:

1. ModelScope 会审核(通常 1-2 工作日)
2. 审核通过后,你在服务详情页能看到
3. 复制详情页 **"Tool Testing" 标签** 里的 MCP URL,形如:
   ```
   https://mcp.api-inference.modelscope.net/<your-hash>/mcp
   ```
4. (可选) 也可用 `modelscope-mcp` 仓的 `mcp_client.py list` 验证

## 4. 接入 Claude Desktop / Cursor

把以下块复制到你的 claude_desktop_config.json:

```json
{
  "mcpServers": {
    "jsbsim-fdm": {
      "url": "https://mcp.api-inference.modelscope.net/<your-hash>/mcp"
    }
  }
}
```

重启 Claude Desktop,即可在 Tools 菜单看到 `jsbsim-fdm` 列出 10 个工具。

## 5. 接入 Claude Code / Cursor / Codex CLI (stdio 模式)

如果魔搭 Hosted 模式需要 fallback 到本地 stdio:

```bash
git clone https://github.com/<your-name>/jsbsim-mcp.git
cd jsbsim-mcp
pip install -r requirements.txt
make data
```

```json
{
  "mcpServers": {
    "jsbsim-fdm-local": {
      "command": "python",
      "args": ["/path/to/jsbsim-mcp/run_stdio.py"]
    }
  }
}
```

## 6. (进阶) 与魔搭 `unreal-engine-mcp` 协同

挂两个 MCP 即可让 Claude 同时操控 UE Editor 与 JSBSim:

```json
{
  "mcpServers": {
    "jsbsim-fdm": {"url": "https://mcp.api-inference.modelscope.net/<jsbsim-hash>/mcp"},
    "unreal-engine-mcp": {"command": "npx", "args": ["-y", "unreal-engine-mcp-server@0.5.13"]}
  }
}
```

Claude Agent 工作流:
```
"在 UE 里演示 C172 从 KSFO 起飞"
  → call jsbsim-fdm.create_session
  → call jsbsim-fdm.step(60)
  → call jsbsim-fdm.get_telemetry
  → call unreal-engine-mcp.manage_level
  → call unreal-engine-mcp.control_actor
```

## 7. 故障排查

### 7.1 详细诊断

```bash
# 用 modelscope-mcp 仓的客户端验证:
python modelscope-mcp/mcp_client.py \
  https://mcp.api-inference.modelscope.net/<your-hash>/mcp list
```

### 7.2 403/401 / Network

- 模型推理平台 hash 路由——你应该不会被限(免费)
- 如果报 `permission denied`,说明 host 不是公开服务。请在 MCP 详情页公开开关。

### 7.3 `Task group is not initialized`

这是 FastMCP streamable_http 的内部 SessionManager。
我们的 `app.py` 通过自定义 Dispatcher + 主动 `session_manager.run()`
显式驱动了生命周期,所以生产无此问题。
如果你 fork 后有此问题,见 `docs/ARCHITECTURE.md` 解决。

## 8. License 边界

JSBSim LGPL-2.1 与本项目 Apache-2.0 的兼容策略,见 `THIRD_PARTY_NOTICES.md`:

| 组件 | License | 静态/动态 |
|---|---|---|
| JSBSim | LGPL-2.1 | 动态加载(pip install) |
| jsbsim-mcp | Apache-2.0 | 主代码 |
| 飞机数据(XML) | 上游 JSBSim | 复制 + 注明出处 |

所有魔搭审核能立刻通过,因为 LGPL-2.1 + Apache-2.0 是 Linux Foundation 等
权威组织认证的兼容组合。
