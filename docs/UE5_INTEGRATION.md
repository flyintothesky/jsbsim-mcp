# jsbsim-mcp × ModelScope `unreal-engine-mcp` · 集成指南

> 把 JSBSim (飞行动力学) 与 UE5 (高保真 3D 场景) 通过两个 MCP 串起来。
> 客户端 Claude Agent 同时挂载两个 MCP,ReAct 循环里交替调用。

---

## 1. 概念图

```
   ┌─────────────────────────────────────────────────────────┐
   │            Claude Desktop / Claude Code                 │
   │            (MCP-aware Agent, ReAct loop)                 │
   │                                                         │
   │     MCP A: jsbsim-fdm            MCP B: unreal-engine-mcp│
   │     (HTTP,this repo)            (stdio,魔搭 / ChiR24)  │
   │     ─────────────────           ──────────────────────── │
   │     10 tools / 7 resources       23 tools (manage_asset, │
   │                                  manage_blueprint,      │
   │                                  manage_level,          │
   │                                  control_actor, …)       │
   │         │                              │                 │
   │         ▼                              ▼                 │
   │   JSBSim FDM v1.3.1            UE5 Editor (本地)        │
   │   60 飞机 6-DoF 物理引擎       • High-quality visuals    │
   │   trim / step / telemetry      • Asset management        │
   │                                  • Real-time scene control│
   │         │                              │                 │
   │         │     同一会话 MCP 循环         │                 │
   │         └──────────┬──────────────────┘                  │
   │                    ▼                                     │
   │            用户自然语言驱动                               │
   │   "在 UE5 里演示 C172 从 KSFO 起飞"                    │
   │     → call jsbsim-fdm.create_session(aircraft='c172x')   │
   │     → call jsbsim-fdm.trim + step(60)                   │
   │     → call unreal-engine-mcp.control_actor(set_pos)       │
   │     → call jsbsim-fdm.get_telemetry (读 40+ 字段)        │
   │     → call unreal-engine-mcp.animation_physics (应用航迹)│
   └─────────────────────────────────────────────────────────┘
```

## 2. 集成形态对比

| 项 | jsbsim-fdm (本项目) | unreal-engine-mcp |
|---|---|---|
| **协议** | streamable_http **+** stdio | stdio (npx) |
| **来源** | 自托管 (HF / Self-Hosted) | 魔搭 `modelscope.cn/mcp/...` + npx 调起本地服务 |
| **服务器侧部署** | python app.py / run_stdio.py | 必须本机有 Node.js 18+ |
| **UE 侧依赖** | 无 | UE5 (5.0-5.8) + `McpAutomationBridge` plugin + Remote Control API |
| **绑定到 Claude 的方式** | URL (HTTP) 或 stdio | stdio only (npx spawn 子进程) |

## 3. 安装准备

### 3.1 客户端要求

- Claude Desktop / Claude Code / Cursor / 任意 MCP 客户端
- Node.js 18+ (本机,用于 npx spawn)
- Python 3.10+ (运行 jsbsim-fdm server)
- Unreal Engine 5.x (本机,有付费/开源 license)
- **重要**: jsbsim-fdm 是 Python **server**,unreal-engine-mcp 是 Node.js **stdio bridge**

### 3.2 UE5 侧 (一次性配置)

1. **下载 UE5.7.4** (官方推荐版本,完整接受测试)
   ```bash
   brew install --cask unreal-engine   # macOS via Epic launcher
   # 或 https://www.unrealengine.com/download
   ```

2. **安装 McpAutomationBridge plugin**
   ```bash
   cd /path/to/YourProject
   # 把 Unreal_mcp repo 拷贝到 plugins/McpAutomationBridge/
   git clone https://github.com/ChiR24/Unreal_mcp.git
   cp -r Unreal_mcp/plugins/McpAutomationBridge plugins/
   ```

3. **在 .uproject 中启用 plugin**:
   ```json
   {
     "Plugins": [
       { "Name": "McpAutomationBridge", "Enabled": true },
       { "Name": "GeoReferencing",     "Enabled": true },
       { "Name": "PythonScriptPlugin",  "Enabled": true },
       { "Name": "EditorScriptingUtilities", "Enabled": true }
     ]
   }
   ```

4. **启动 UE Editor**(Editor 会自动在 :8091 启动 MCP bridge,看到状态栏 `● MCP :3000`)

### 3.3 jsbsim-fdm server 启动

```bash
cd /Users/chenlei/Projects/jsbsim-mcp
source .venv/bin/activate
python app.py    # → http://localhost:7860
```

## 4. Claude Desktop 配置(双 MCP)

编辑 `claude_desktop_config.json`:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "jsbsim-fdm": {
      "url": "http://127.0.0.1:7860/mcp"
    },
    "unreal-engine-mcp": {
      "command": "npx",
      "args": ["-y", "unreal-engine-mcp-server@0.5.13"],
      "env": {
        "MCP_AUTOMATION_PORT": "8091"
      }
    }
  }
}
```

**注意**:
- `jsbsim-fdm` 是 HTTP,**`url` 字段**
- `unreal-engine-mcp` 是 stdio,**`command` + `args` 字段**
- `-y` flag 让 npx 自动确认 yes 安装
- 锁版本 `0.5.13` 避免升级 break 接口
- `MCP_AUTOMATION_PORT` 与 UE Editor 启动的 plugin 端口一致

重启 Claude Desktop,工具列表里应出现 **33 个工具**(10 jsbsim + 23 unreal)。

## 5. Claude Code / Cursor (本地 stdio 模式)

**JSBSim 用 stdio 模式**(本项目 `run_stdio.py`):

```json
{
  "mcpServers": {
    "jsbsim-fdm": {
      "command": "python",
      "args": ["/Users/chenlei/Projects/jsbsim-mcp/run_stdio.py"]
    },
    "unreal-engine-mcp": {
      "command": "npx",
      "args": ["-y", "unreal-engine-mcp-server@0.5.13"],
      "env": { "MCP_AUTOMATION_PORT": "8091" }
    }
  }
}
```

## 6. 协同工作流示例

### 6.1 "演示一架 C172 从 KSFO 起飞"

Claude Agent 内部推理(伪):

```
Step 1: tool_call jsbsim-fdm.list_aircraft
        → ["737", "787-8", "A320", ..., "c172x", ...]

Step 2: tool_call jsbsim-fdm.create_session
        { aircraft: "c172x",
          initial_conditions: { altitude_ft: 4,
                                airspeed_fps: 60*1.6878,
                                latitude_deg: 37.62,
                                longitude_deg: -122.38 } }

Step 3: tool_call jsbsim-fdm.trim { mode: "longitudinal" }
Step 4: tool_call jsbsim-fdm.step { seconds: 5 }  // 起飞滑跑
Step 5: tool_call jsbsim-fdm.set_property
        { path: "fcs/throttle-cmd-norm", value: 1.0 }  // 全油门
Step 6: tool_call jsbsim-fdm.step { seconds: 30 }  // 起飞 + 爬升

Step 7: tool_call unreal-engine-mcp.control_editor
        { action: "load_level", name: "KSFO_Refhearsal" }

Step 8: tool_call unreal-engine-mcp.manage_asset
        { action: "spawn", type: "C172_Mesh",
          location: {lat: 37.62, lon: -122.38, alt: 4} }

Step 9: tool_call unreal-engine-mcp.animation_physics
        { actor: "C172", trajectory_source: "jsbsim://sessions/abc/telemetry" }

Step 10: tool_call unreal-engine-mcp.manage_camera
        { type: "follow", target: "C172" }
```

最终:UE5 Editor 里看到一架 C172 在 KSFO 跑道 28R 起飞,按真实 JSBSim 物理航迹飞行。

### 6.2 "测试失速恢复"

```
Step 1: jsbsim-fdm.create_session c172x 5000ft 90kt
Step 2: jsbsim-fdm.trim longitudinal
Step 3: jsbsim-fdm.set_property { path: "fcs/elevator-cmd-norm", value: -0.4 }
Step 4: jsbsim-fdm.step { seconds: 5 }   // 拉起
Step 5: jsbsim-fdm.get_telemetry         // 读 alpha
        if alpha > 16°:
            jsbsim-fdm.set_property elevator = +0.4, throttle = 1.0
            jsbsim-fdm.step { seconds: 3 }
        unreal-engine-mcp.animation_physics ...   // 在 UE 里可视化失速-恢复
```

## 7. 故障排查

| 现象 | 排查 |
|---|---|
| Claude 工具列表只有 10 个 jsbsim 工具 | unreal-engine-mcp 启动失败 — 看 npx 错误。常见:`Node.js` 未装、版本 <18、`MCP_AUTOMATION_PORT` 与 UE 不一致 |
| Unreal 工具列表为空 | UE Editor 未启动,或 MCP plugin 未 enable |
| `npx unreal-engine-mcp-server` 报 ECONNREFUSED | UE Editor 中 MCP plugin 没起,或端口不对 |
| `control_actor` 报 `actor not found` | Actor 还没 spawn,先 manage_asset |
| 时延大 | 给 `args` 末尾加 `--log-level warn` 减少 npx noise |

## 8. 已知边界

- 1 个 UE5 Editor 进程 = 1 个 MCP session。多 UE 实例需要多份 npx 起不同 `MCP_AUTOMATION_PORT`
- UE5 plugin 是 native C++,会随 UE 版本升级 break,锁定 UE5.7.4
- 23 个 unreal-engine-mcp tools 主要面向 Editor(关卡编辑、资产操作),不是 gameplay runtime 控制
- 此项目不内置 MCP `unreal-engine-mcp` 任何代码 — 完全是 **客户端组合**

## 9. License 边界

- jsbsim-fdm 主代码: Apache-2.0
- JSBSim 依赖: LGPL-2.1
- unreal-engine-mcp (npm): 上游 Repo (https://github.com/ChiR24/Unreal_mcp) — GPL-2.0 (上游声明)
- Unreal Engine 本身: Epic EULA,商业使用需付费授权

**结论**:本项目的代码永远不在 GPL 框架下(Apache-2.0 + LGPL-2.1 动态链接),组合使用时 UE/MCP 端各自遵循其 license。