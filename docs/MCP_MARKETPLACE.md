# MCP 分发与上架说明（Distribution & Marketplace）

> 说明本项目作为 MCP Server 的分发形态、上架所需材料、发布前检查清单与发布前待办项。渠道名称与提交入口以各市场官网最新要求为准，提交前需再次核对。

## 1. 支持的分发形态

| 形态 | 入口 | 适用场景 |
|---|---|---|
| 本地 stdio MCP | `python server.py` | 接入 Claude / Cursor / VS Code 等本地 MCP 客户端 |
| 远程 HTTP MCP | `python -m lcg.server_http`（端点 `/mcp`，探活 `/healthz`，可选 Bearer） | 团队 / 数字人后台 / 服务化接入 |
| Python 包 | `pyproject.toml`（hatchling，`src/lcg`） | 可构建 wheel 发布到包索引；规则核心零第三方依赖 |
| 容器 | `deploy/Dockerfile` | 自托管 / 私有化部署 |

客户端配置示例见 `examples/mcp-client.stdio.json`、`examples/mcp-client.http.md`；项目级配置见根目录 `.mcp.json`（默认 `LCG_LLM_ENABLED=0` 纯规则运行，无 key 即可用；需要语义层时在客户端 env 中开启并配置模型 key）。

## 2. 上架材料清单

| 材料 | 现状 | 说明 |
|---|---|---|
| 仓库公开访问 | 发布前需设为 Public | 市场与用户需能匿名访问源码、LICENSE 与文档 |
| README（英文 + 中文） | 已有 | 含工具列表、快速开始、能力边界与免责声明 |
| LICENSE | 已有（MIT，署名 1ouxilisi） | 市场元信息需与之一致 |
| 包元信息 | `pyproject.toml`：name/version/description/keywords/license/authors | 检索关键词已补 |
| 项目级 MCP 配置 | `.mcp.json` | 供编辑器 / 客户端自动发现 |
| 工具 schema 文档 | `docs/TOOL_SCHEMA.md` | 工具入参、返回结构与风险级枚举 |
| 评测与信任凭证 | `reports/BENCHMARK.md`、`reports/LLM_EVAL.md`、`reports/PERF.md` | 检出率 / 在线快照 / 性能基准 |
| 合规依据与边界 | `docs/COMPLIANCE_MAPPING.md`、`docs/SCOPE_BOUNDARY.md` | 对外说明依据来源与不承接范围 |
| 变更记录 | `CHANGELOG.md` | 版本与规则词库变更留痕 |

## 3. 发布前检查清单

- [ ] 仓库改为 Public，匿名可访问。
- [ ] 回归全绿：`pytest -q`、`evals/run_evals.py`、`ruff check`、`export_rules.py --check`。
- [ ] 在线 LLM 评测快照为最新（`reports/LLM_EVAL.md`），或明确标注离线规则层成绩。
- [ ] 确认 `.env` / 密钥 / 内部台账未入库（`.gitignore` 已排除 `.env`、`*上架物料包*.md` 等）。
- [ ] 版本号、`CHANGELOG.md`、README 口径一致（规则版本、评测条数、能力边界）。
- [ ] README 中仓库地址、CI 徽章链接正确；公开且 Actions 跑通后徽章才显示。
- [ ] 合规表述统一为"风险提示 / 改写建议"，无"包过审 / 法律背书"字样。

## 4. 上架渠道（按优先级）

1. **官方 MCP server 列表 / 目录**：向 MCP 官方生态的 servers 仓库或目录提交条目（名称、一句话描述、仓库地址、传输方式、运行时要求）；具体提交模板与分类以官方仓库当前 CONTRIBUTING 为准。
2. **客户端市场 / 插件市场**：Cursor、VS Code、Claude 等客户端各自的 MCP / 插件发现渠道，按其表单填写。
3. **包索引**：若发布 Python wheel，按包索引上传流程提交；描述与关键词沿用 `pyproject.toml`。
4. **社区渠道**：技术社群、独立开发者目录、内容帖子引流到仓库。

> 提交条目建议字段：`name`、`description`（一句话中文/英文）、`keywords`、`repository`、`license`、`runtime`（Python ≥3.10）、`transport`（stdio / HTTP）、`optional`（LLM 层需 key）。

## 5. 发布前待办与解除方式

| 待办项 | 说明 | 解除方式 |
|---|---|---|
| 仓库可见性 | 若仍为 Private，匿名 API 访问 404，市场无法引用 | 仓库 Settings → General → Danger Zone 改为 Public；或由具备 repo 权限的 token 通过 API 切换 |
| 无发布凭据 | 当前无 `GH_TOKEN` / PAT / SSH，`gh` CLI 未安装 | 由仓库所有者生成具备 repo 权限的 PAT，或在网页端操作 |
| CI 徽章 | 仓库公开且 GitHub Actions 跑通后才显示 | 公开后推送触发 CI，确认 workflow 绿 |

## 6. 本地上架前自检

```bash
python server.py --selftest
python scripts/export_rules.py --check
python -m pytest -q
python evals/run_evals.py
# 可选：MCP Inspector 本地调试（Node devtools，见 package.json scripts.inspect）
```
