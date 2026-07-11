# 魔搭社区 MCP 服务详情页文案

> 这是魔搭 MCP 详情页要填的内容源。复制本文件对应段落直接粘贴。

---

## 服务名称 (server name)
```
jsbsim-fdm-local
```

## 中文名
```
JSBSim 飞行动力学仿真
```

## 英文名
```
jsbsim-fdm-local
```

## 中文描述 (zh description)
```
把业界标准的开源 6 自由度飞行动力学模型(JSBSim v1.3.1)封装为本地 MCP 服务。

通过 pip install 或 docker 直接在你的 Mac / Linux 上跑,然后作为 stdio MCP
服务挂入 Claude Desktop / Cursor / Codex / Claude Code,即可让任何支持
MCP 的智能体用自然语言实时驱动 C172、A320、F-16 等 60 款飞机的仿真。

★ 10 个 MCP 工具: list_aircraft / create_session / close_session /
  set_initial_conditions / trim / step / get_property / set_property /
  get_telemetry / execute_script
★ 7 个 MCP 资源: jsbsim://aircraft 等
★ 2 个 MCP Prompt: cruise_c172, stall_recovery

★ 任意本地子网 / 团队内部署:自带 FastAPI + WebSocket Web Dashboard。
★ License: Apache-2.0(本项目) + LGPL-2.1(JSBSim 依赖,动态链接)。

注意: 本服务为 self-hosted / 用户本地部署型,不是魔搭代托管的 hosted endpoint。
请按下方 "使用方式" 在 Claude Desktop 里以 stdio 模式接入。
```

## 英文描述 (en description)
```
JSBSim flight dynamics, exposed as a self-hosted MCP service.

Run `pip install -e .` (or use the bundled Docker image) on your
own machine, then plug the `run_stdio.py` entry into Claude Desktop
/ Cursor / Codex as a stdio MCP server.

You get 10 tools, 7 resources and 2 prompts for driving any of the 60
bundled aircraft (C172, A320, F-16, 737, Concorde, X-15, etc.) in
real-time simulation through natural language.

★ Self-hosted only — no hosted endpoint. Run it on your laptop or
  any LAN-accessible machine.
★ License: Apache-2.0 (this project) + LGPL-2.1 (JSBSim dependency,
  dynamically linked — preserved).

For installation steps, see:
  https://github.com/flyintothesky/jsbsim-mcp/blob/main/README.md
```

## 标签 (tags)
```
飞行仿真, FDM, aircraft, simulation, developer-tools, physics,
self-hosted, mcp, autonomous-agents
```

## 仓库 URL (source_url)
```
https://github.com/flyintothesky/jsbsim-mcp
```

## 安装 / 接入 (server_config)

### Stdio 接入(推荐)
```json
{
  "mcpServers": {
    "jsbsim-fdm-local": {
      "command": "python",
      "args": ["/abs/path/to/jsbsim-mcp/run_stdio.py"]
    }
  }
}
```

### pip 安装(用于 Claude Desktop)
```bash
pip install "git+https://github.com/flyintothesky/jsbsim-mcp.git"
```

### Docker 镜像(自带 Web Dashboard)
```bash
docker build -t jsbsim-mcp https://github.com/flyintothesky/jsbsim-mcp.git
docker run --rm -p 7860:7860 jsbsim-mcp
# 浏览 http://localhost:7860/
```

---

## 详情页正文(readme,可以 paste 到魔搭详情页正文区)

```
# jsbsim-mcp

## 这是什么?

把 JSBSim(开源 6 自由度飞行动力学)封装成 MCP stdio 服务,让 Claude / Cursor
/ Codex 等 LLM Agent 能"自然语言控制一架飞机"。

## 安装(2 步)

1. pip install:
   pip install "git+https://github.com/flyintothesky/jsbsim-mcp.git"
2. 复制下面到 claude_desktop_config.json:

   {
     "mcpServers": {
       "jsbsim-fdm-local": {
         "command": "python",
         "args": ["run_stdio.py"]
       }
     }
   }

3. 重启 Claude Desktop。Tools 菜单能看到 10 个工具。

## 三步例

调用 list_aircraft → 选 c172x
调用 create_session(aircraft="c172x", initial_conditions={altitude_ft: 8000, ...})
调用 step(seconds=30) → 看 get_telemetry

## 进阶:打开 Web Dashboard

python app.py → http://localhost:7860/

• SVG PFD(主飞行显示,空速带 + 高度带 + 姿态仪)
• Three.js 3D 姿态
• Plotly 时序图(高度/速度/迎角/推力)
• WebSocket 实时推流
• JSON-RPC console 直接给 /mcp 调试

## License

• 本项目: Apache-2.0
• JSBSim 依赖: LGPL-2.1(动态链接,LGPL 合规)

## GitHub

https://github.com/flyintothesky/jsbsim-mcp
```

---

## 推广话术(给魔搭社区 / 朋友圈 / 公众号)

```
✈️  折腾 RL 训练 / AI 仿真 / 数字孪生 / 飞行教员的同学看过来

jsbsim-mcp 是一项 self-hosted MCP 服务,把 NASA 和 DARPA 也在用的开源
飞行动力学引擎(JSBSim)封装成 stdio MCP 服务器,直接接 Claude Desktop /
Cursor / Claude Code。

亮点:
• 60 架真飞机(C172/A320/F-16/737/Concorde/X-15 ...)
• 自然语言姿态控制
• 自带 Web Dashboard(PFD + 3D + 时序图)
• Apache-2.0 + LGPL-2.1

GitHub: https://github.com/flyintothesky/jsbsim-mcp
本地跑起来 5 分钟,欢迎试用。
```
