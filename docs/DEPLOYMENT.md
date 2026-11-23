# 部署与平台化演进（Deployment & Platform Evolution）

> 本文区分**当前已实现的自托管能力**与**尚未实现的平台化方向**，避免把路线图当成现有功能。
> 本工具仅为合规风险提示，不构成法律意见；数据留存与合规责任由部署方按自身业务及所在地法规确定。

## 1. 当前部署形态（已实现）

| 形态 | 入口 | 说明 |
|---|---|---|
| 本地 stdio MCP | `python server.py` | 接入本地 MCP 客户端；规则核心零第三方依赖 |
| 远程 HTTP MCP | `python -m lcg.server_http` | `/mcp` 端点 + `/healthz` 探活 + 可选 Bearer 鉴权 |
| Python wheel | `pyproject.toml`（hatchling） | 规则词库随包打入；可 `pip install` 后独立运行 |
| 容器 | `deploy/Dockerfile` | 整仓拷贝自托管 / 私有化部署 |

## 2. 当前架构边界（现状，勿过度承诺）

- **单进程**：LLM 语义缓存、调用预算为进程内单例（`pipeline._GLOBAL_JUDGE`），重启即清空；多实例间不共享。
- **无账号体系**：HTTP 层支持多个共享访问 Key（`LCG_BEARER_TOKEN` 单值兼容 / `LCG_BEARER_TOKENS` 逗号分隔），仍没有用户 / 租户 / 角色概念；`lcg.tenant` 提供进程内存实现与可选本机 SQLite 后端，不做鉴权、不做跨进程隔离。
- **留痕为本地文件**：审计（`lcg.audit`）与反馈（`lcg.feedback`）默认关闭，启用后写本地 JSONL；配额 / 用量可选落本机 SQLite；无外置数据库、无远程汇聚。
- **文本输入**：`lcg.ingest` / `lcg.sources` 归一上游 ASR / OCR / 字幕 / 表格产出的文本片段；本服务不做 ASR 语音识别、不做 OCR 图像识别。`lcg.sources` 定义了输入源协议与 `Recognizer` 识别适配器协议及内存桩，均不发起真实网络调用；真实识别后端由部署方接入。
- **规则与代码同仓**：词库为仓库内 JSON，更新需随版本发布或重新部署；暂无在线热更新控制台。

## 3. 配置项速查

| 环境变量 | 作用 | 默认 |
|---|---|---|
| `LCG_LLM_ENABLED` | 语义层总开关 | `1`；`0/false/no/off` 关闭，纯规则运行 |
| `LCG_LLM_PROVIDER` | provider（siliconflow/modelscope/openrouter/openai，或自定义 base_url） | `siliconflow` |
| `LCG_MODEL_PRIMARY` / `LCG_MODEL_FALLBACK` | 主 / 备模型 | 空（无模型则降级纯规则） |
| `LCG_LLM_API_KEY` / 各 provider key | 模型密钥，只来自 env / 平台 Secret，不入库 | 空 |
| `LCG_LLM_TIMEOUT` | 单次调用超时（秒，须 >0） | `20.0` |
| `LCG_LLM_MAX_CALLS` | 单进程调用预算（0 或超限即禁用 LLM） | `200` |
| `LCG_PRICE_INPUT_PER_MTOK` / `LCG_PRICE_OUTPUT_PER_MTOK` | 每百万 token 单价，用于成本估算；0 = 只报 token | `0` |
| `LCG_BEARER_TOKEN` | HTTP 共享访问令牌（单值，向后兼容）；不设置则本地开放（仅限可信内网） | 空 |
| `LCG_BEARER_TOKENS` | HTTP 多 Key，逗号分隔；与 `LCG_BEARER_TOKEN` 合并生效 | 空 |
| `LCG_STORE_DSN` | 配额 / 用量存储：空 = 进程内存；文件路径 = 本机 SQLite 落盘；`:memory:` = SQLite 内存库 | 空（内存） |
| `LCG_HTTP_HOST` / `LCG_HTTP_PORT` | HTTP 监听地址 / 端口 | `0.0.0.0` / `8000` |
| `LCG_AUDIT_LOG` | 审计 JSONL 路径；不设置则不落盘 | 空（关闭） |
| `LCG_AUDIT_REDACT` | `1` 时审计不记录原始话术，仅留长度与截断命中片段 | `0` |
| `LCG_FEEDBACK_LOG` | 反馈 JSONL 路径；不设置则不落盘 | 空（关闭） |

非法配置（未知 provider、非正超时、负单价 / 负预算）会回退安全默认值并写入 `LLMConfig.warnings`，不会让服务崩溃。

## 4. 生产自托管建议（落地前核对）

- **鉴权**：公网部署务必设置 `LCG_BEARER_TOKEN` 或 `LCG_BEARER_TOKENS`；置于反向代理 / 网关之后，由网关负责 TLS 与限流。多 Key 仅为静态共享凭证，不等同账号体系。
- **密钥**：模型 key 只通过环境变量或平台 Secret 注入；不要写进仓库、日志或审计文本。
- **降级预期**：无 key / 超时 / 超预算 / 脏返回时自动回退纯规则（`mode=rules_only`），服务不中断；上线前确认纯规则结果可接受。
- **留痕与隐私**：开启审计前明确留存范围与期限；涉及主播口播原文时优先开启 `LCG_AUDIT_REDACT`。
- **健康检查**：`/healthz` 返回版本、规则版本与规则条数，可接入负载均衡探活。
- **合规口径**：对外统一表述为“风险提示 / 改写建议”，不得承诺“包过审 / 法律背书”；法条与平台规则版本需经法务或官方规则中心复核。

## 5. 平台化演进路线（均为未实现方向）

> 以下是从“单租户自托管原型”走向“多租户服务”需要补的能力；当前版本**均未实现**，不应在对外材料中宣称已具备。

| 方向 | 现状基础 | 待补能力 |
|---|---|---|
| 多租户隔离 | `lcg.tenant` Tenant/配额骨架；内存或可选本机 SQLite；多共享 Key | 租户身份、独立词库 / 插件包、数据与配置隔离、按租户配额 |
| 账号与鉴权 | HTTP 多共享 Key 静态校验（Bearer 集合） | 用户/租户账号体系、API Key 签发与轮换、角色与权限、审计到人 |
| 配额与计费 | `lcg.tenant` 配额扣减与用量快照；内存 + 可选本机 SQLite；已有调用计数与 token usage 透传 | 外置持久化计量、对接账单与套餐；单价配置化 |
| 存储 | 本地 JSONL（审计 / 反馈）；配额 / 用量可选本机 SQLite | 外置数据库或对象存储、留存策略、检索与导出、备份 |
| 无状态与扩展 | 进程内缓存 / 预算 | 缓存与预算外置（Redis 等），支持多实例水平扩展 |
| 规则运营 | 规则随版本发布；`rules/plugins/_*.json` 占位骨架 | 规则在线版本管理、灰度发布、命中反馈回流到规则评审流程 |
| 输入接入 | `lcg.ingest` 归一契约；`lcg.sources` 输入源协议 + `Recognizer` 识别适配器协议与内存桩 | 对接真实 ASR / OCR 上游、实时字幕流；识别能力仍由外部服务承担 |

## 6. 明确不承接 / 不具备

- 不核验资质、备案、证书真伪；不做语音 / 图像识别；不提供法律结论或免责背书。
- 医疗器械、教育培训、金融理财、酒水、跨境英文等行业规则尚未覆盖（见 README Roadmap）。
- 规则层存在固有漏报 / 误报；线上结果随模型版本与账户余额波动。
