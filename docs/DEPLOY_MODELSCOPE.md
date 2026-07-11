# 在魔搭社区上架 jsbsim-mcp(Self-Hosted 模式)

> 适用于不想维护公网部署 / HF token / Render 订阅的项目维护者。
> 推荐路线:**仅注册 metadata,完全 self-hosted,用户自己跑 stdio**。

## 0. 前置准备

- 一个 GitHub 公开仓库(本项目 `jsbsim-mcp`)
- 一个 ModelScope 账号
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

## 2. 上架魔搭 MCP(非 hosted 模式)

URL: https://www.modelscope.cn/mcp/create(登录后)

完整文案素材全部在 `docs/MAGICSTUDIO.md`,照搬对应字段即可。

| 字段 | 内容 |
|---|---|
| 服务名称 | `jsbsim-fdm-local` |
| 中文名 | `JSBSim 飞行动力学仿真` |
| 描述 | 复制 `docs/MAGICSTUDIO.md` 的中文描述段 |
| 英文描述 | 复制 `docs/MAGICSTUDIO.md` 的英文描述段 |
| 标签 | `飞行仿真, FDM, aircraft, simulation, developer-tools, self-hosted, mcp` |
| 仓库 URL | `https://github.com/flyintothesky/jsbsim-mcp` |
| 部署方式 | **`Self-Hosted` / `Local stdio`**(不要选 Hosted) |
| server_config | 复制 `docs/MAGICSTUDIO.md` 的"Stdio 接入"块 |

⚠️ **重要:** 部署方式**必须选 Self-Hosted / local stdio**,
否则魔搭会要求你提供公网 URL,我们没有就不用管它。

## 3. (可选) 用户在 Claude Desktop 接入

将 `docs/MAGICSTUDIO.md` 里的"Stdio 接入"块复制到:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

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

重启 Claude Desktop,即可见 10 个工具。

## 4. (可选) 一行安装命令

```bash
pip install "git+https://github.com/flyintothesky/jsbsim-mcp.git"
```

要求 Python ≥ 3.10,以及 `pip install jsbsim==1.3.1`(自动作为本项目
依赖安装)。

## 5. (高级)本地有公网环境才考虑 Hosted 模式

如果你将来:①Render / Fly.io 永久免费 tier 部署,②hf.space 重新
deploy(需要 token),③自建有公网 IP 服务器,**可以再升级到 Hosted 模式**:

| 公网后端 | 难度 | Token 风险 |
|---|---|---|
| Render.com 免费 web service | 低,5 分钟 | 0(GitHub OAuth) |
| Fly.io 免费 tier | 低 | 0(GitHub OAuth) |
| HF Space | 中(需要写 token) | 中(易泄漏) |
| Cloudflare Tunnel + 本地机器 | 高(本机要常驻) | 0 |
| 自有服务器 | 视情况 | 自控 |

Hosted 模式下,魔搭会:

1. 验证你的 `POST /mcp` URL 返回有效 JSON-RPC initialize
2. 分配一个 hash URL:`https://mcp.api-inference.modelscope.net/<hash>/mcp`
3. 任何人通过 Claude 都能用你的服务

详见 `docs/HF_DEPLOY.md`(模板 — 现在为空)。

## 6. 故障排查

### 6.1 Claude Desktop 看不到 tools

- 检查 `claude_desktop_config.json` JSON 语法正确
- 检查 Python 路径 — 用 `which python` 替换 config 里的 "python"
- 检查 `run_stdio.py` 是绝对路径
- 重启 Claude Desktop(不是只重启会话)

### 6.2 `ModuleNotFoundError: jsbsim`

- 你的 python venv 没装 jsbsim 1.3.1
- 解决:`pip install jsbsim==1.3.1`

### 6.3 时延 / 速度

- stdio 模式无网络延迟,适合本地跑高频仿真
- 如果 step(seconds=60) 卡住,检查 LFM 模型是否太大(默认 c172x 良好)

### 6.4 想启用 hosted 模式但被卡在公网 URL

参见 5;最低成本是用 Render 永久免费 tier。

## 7. License 边界

JSBSim LGPL-2.1 + 本项目 Apache-2.0 兼容策略,
见 `THIRD_PARTY_NOTICES.md`:

| 组件 | License | 静态/动态 |
|---|---|---|
| JSBSim | LGPL-2.1 | 动态加载(pip install) |
| jsbsim-mcp | Apache-2.0 | 主代码 |
| 飞机数据(XML) | 上游 JSBSim | 复制 + 注明出处 |

魔搭审核对 LGPL + Apache 组合是合规的。
