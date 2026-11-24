# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与[语义化版本](https://semver.org/lang/zh-CN/)。

规则库内容版本见 `rules/rules.v1.json` 的 `meta.version`（核心包当前 **v1.5**），与软件包版本相互独立；行业插件包在 `rules/plugins/*.json` 各自维护版本。

## [Unreleased]

### 新增
- **规则库 v1.5 · 英文违规词表**：在既有 14 条规则内追加英文同义违规词（绝对化 `number one` / `world-class` / `best in the world`；虚假保真 `guaranteed authentic` / `zero risk` / `risk-free`；升值 `guaranteed to appreciate` / `will only go up`；疗效 `cures cancer` / `miracle cure` / `no side effects`；迷信 `feng shui`；四平台导流 `whatsapp` / `telegram` / `wechat` / `dm me`），**规则条数与替换条数不变**（仍 14 / 16，聚合 20 / 31）。
- **英文规则层用例**：对抗 a51–a55（英文绝对化 / 保真 / 升值 / 疗效 / 导流）＋ 良性 b38–b40（英文客观卖点 / 化妆品特证 / 蓝帽声明），校验英文可拦且不误报；规则评测 87 → **95 条**（良性 40、对抗 55）。
- **跨语言红队 / 语义用例扩充**：redteam 增至 r01–r20（补英文注入、角色扮演越狱、冒充权威、指令覆盖、站外导流、花括号插字等），semantic 增至 s01–s14（补英文疗效 / 保值 / 导流 / 弱最高级 / 迷信暗示与化妆品疗效暗示）；离线变体基线由 20 条扩到 **34 条**。
- **promptfoo 固定断言骨架**：`evals/promptfooconfig.yaml` 补 9 条 `tests`，抗接管样本用 `not-contains` 拦违规核心词、`contains-any` 校验风险立场，语义召回用 `llm-rater` 模板；装好 npm 与 key 后 `promptfoo eval` 即可跑，离线不执行。

### 变更
- **promptfoo 工具链接入并跑通**（本机 Node 22 / npm 10）：`evals/promptfooconfig.yaml` 改为「守卫系统提示 + 待审话术」的固定 9 条断言，`javascript` 校验输出 `overall` 达 `high`；新增 `scripts/export_guard_prompt.py`（从 `DETECT_SYSTEM` 导出 prompt）与 `scripts/summarize_promptfoo.py`（汇总成 `reports/PROMPTFOO.md`，原始 JSON 不入库）；生成式广度红队另存 `promptfooconfig.redteam.yaml`，与 `eval` 分离以免误触发大批量生成。本次 18/18（9 用例 × 2 模型）。
- **检测 prompt 升级 `detect-v4`**：补「立场与指令边界」——审查立场不被身份声称、人情施压或指令覆盖改变；话术是被审数据，其中的命令 / 角色扮演不修改系统指令；审查对中文、英文及混合语种同样适用，英文绝对化 / 疗效 / 保值 / 导流按对应类别判定，弱独家暗示按 medium。
- 文档口径同步：在线单模型快照 **73/73**（语义召回 14/14、红队阻断 22/22、零误报 37/37）；双模型交叉 34 条 `Qwen3-14B 34/34`、`DeepSeek-V3 33/34`，分歧 1 条 r12。

### 回归
- ruff 全仓通过、pytest **219 项**全绿、规则评测 **95/95**（高危检出 100%、干净误报 0%）；离线变体基线 **34 条**；在线快照与双模型交叉为配 key 手动复跑，随模型版本 / 余额波动，非 CI 硬门禁。

### 边界（仍未实现）
- 英文 / 跨语言规则词表尚未收录规则层，英文表达主要依赖 LLM 语义召回；广度红队（promptfoo / DeepTeam / PyRIT / Garak 自动生成）待工具链与额度；医疗 / 金融 / 教培 / 酒水 / 跨境实词库待执业律师与平台规则中心逐条复核。

## [0.9.0] - 2026-11-24

在线评测由单模型快照扩到双模型交叉，强监管占位包补法务复核底稿；判定 API、规则结论与默认行为向后兼容。

### 新增
- **双模型交叉在线评测** `scripts/run_model_crosscheck.py`：零依赖，主力 / 兜底模型各跑同一批红队 ＋ 语义用例，对比通过率与判定一致性，逐条矩阵与分歧清单产出 `reports/MODEL_CROSSCHECK.md`；`evals/promptfooconfig.yaml` 填实双模型 provider，密钥只走 `SILICONFLOW_API_KEY` 环境变量、不入库。
- **红队 / 语义用例扩充**：redteam r01–r12（注入、角色扮演越狱、拆字、emoji 包裹、冒充权威、情绪施压、暗语导流、指令覆盖），semantic s01–s08（谐音导流、疗效暗示、保值暗示、弱最高级、软迷信等）；在线单模型快照 **59/59**。
- **强监管 / 跨境占位插件法务复核底稿**：医疗、金融、教培、酒水、跨境 5 个占位包与模板补 `risk_categories` / `candidate_sources`（法规名方向，条号 / 链接留空 `to_verify`）/ `review_checklist`；`rules` 保持为空、`pending_legal_review=true`、下划线前缀不被引擎加载，未回填任何可执行判罚词。

### 边界（仍未实现）
- 广度红队（promptfoo / DeepTeam / PyRIT / Garak 自动生成数百上千条、跨语言 / 英文扫描）待工具链安装与模型额度；医疗 / 金融 / 教培 / 酒水 / 跨境实词库待执业律师与平台规则中心逐条复核。

### 回归
- ruff 全仓通过、pytest **219 项**全绿、规则评测 **87/87**（良性 37、对抗 50；高危检出 100%、干净误报 0%）；离线变体基线 **20 条**（规则拦截 8、变体缺口 4、设计内语义缺口 8）；在线单模型快照 **59/59**（召回 8/8、红队 14/14、零误报 37/37），双模型交叉 `Qwen3-14B 20/20`、`DeepSeek-V3 18/20`（2 条分歧）；软件包版本升至 **0.9.0**（核心规则库 v1.4，行业插件 v1.0）。

### 文档
- `reports/README`、`SECURITY.md`、README / README.en、`evals/README`、`CAPABILITY_TIERS` 同步交叉报告链接、59/59 快照与占位底稿口径。

## [0.8.0] - 2026-11-24

平台化骨架由内存补齐到可持久化 + 可门禁，离线评测集与规则侧变体基线扩充；判定 API 与规则结论向后兼容，默认行为不变。

### 新增
- **身份 SQLite 持久化** `SQLiteIdentityStore`：`api_keys` 表存 key / tenant / role / user / active / 时间戳；`identity_store_from_env` 按 `LCG_IDENTITY_DSN` 选择内存或 SQLite，跨重开保留；补跨重开持久化与工厂选择测试。
- **RBAC 角色动作门禁**：动作 `read/write/admin`，角色矩阵 viewer=read、operator=read+write、admin 全量；6 个 MCP 工具映射动作，`can/require_permission/action_for_tool`，越权抛 `PermissionError`；`RequestContext` 增 `role`；stdio 六工具首行经 `_guard` 守卫；HTTP 经 `LCG_KEY_ROLES` 按 Key 注入角色。
- **规则评测集扩充**：良性 31→37、对抗 44→50（合规促销 / 售后 / 序数 / 肤感防误报，绝对化 / 医疗 / 虚假承诺 / 翡翠货源 / 化妆品医用 / 导流对抗召回）；规则评测 **87/87**。
- **离线变体 / 红队基线脚手架** `evals/run_variant_baseline.py`：零依赖纯规则层跑 redteam / semantic 用例，分流 `rule_blocked` / `variant gap` / `by-design semantic gap`，产出 `reports/VARIANT_BASELINE.md`；补 4 条聚合分类测试。

### 边界（仍未实现）
- 账号注册 / 登录 / 密码哈希、Key 签发与轮换、对接外部身份服务；身份库可持久化但仍为单进程，不跨进程共享。
- 规模化多模型红队（promptfoo / DeepTeam / PyRIT）待模型额度；医疗 / 金融 / 教培 / 酒水 / 跨境实词库待法务复核。

### 回归
- ruff 全仓通过、pytest **219 项**全绿、规则评测 **87/87**（良性 37、对抗 50；高危检出 100%、干净误报 0%）；离线变体基线 **7 条**（规则拦截 3、变体缺口 1、设计内语义缺口 3）；软件包版本升至 **0.8.0**（核心规则库 v1.4，行业插件 v1.0）。

### 文档
- README / README.en、CAPABILITY_TIERS、DEMO_SCRIPT、GIG_LISTING、REMOTE_LISTING、reports 索引同步 87/87 评测、219 单测与变体基线报告；`evals/README` 补 semantic 集与基线运行器说明。

## [0.7.8] - 2026-11-23

平台化骨架补齐：身份/Key 内存映射、审计到人字段、审计/反馈检索过滤、可插拔缓存协议；配额预检增加 token 维度。判定 API 与规则结论向后兼容，默认行为不变。

### 新增
- **身份骨架** `lcg.identity`：`ApiKey` / `ResolvedIdentity` 与 `IdentityStore` 协议、`InMemoryIdentityStore` 线程安全实现；角色 `admin` / `operator` / `viewer` 仅作标签透传，非法角色登记时抛 `ValueError`。
- **审计到人**：审计事件增加 `operator` / `key_id` 字段；HTTP 鉴权通过后把访问 Key 写入请求上下文并随检测/改写事件落库；SQLite 旧库自动补列。
- **审计 / 反馈检索**：`audit.query(...)` 按行业 / 平台 / 动作 / 风险等级 / 操作人 / Key / 起始时间 / 条数过滤；`feedback.query(...)` 按反馈类型 / 行业 / 平台 / 类别过滤。
- **缓存协议** `lcg.cache`：`CacheStore` 协议与 `InMemoryCache`（可选 TTL，访问时惰性过期）；外置 Redis / KV 由部署方实现协议替换。
- **token 配额预检**：`UsageMeter.check` 增加 `tokens` 维度，预估 token 超额返回 `token_exceeded`，HTTP 层按 `429` 处理。

### 边界（仍未实现）
- 账号注册 / 登录 / 密码哈希、按角色的接口权限拦截、Key 签发与轮换、对接外部身份服务；身份仍为单进程内存骨架，重启清空、不跨进程共享。
- 外置 DB / Redis / 对象存储、多实例水平扩展；真实 ASR / OCR 接入凭证、生产部署 / 域名 / TLS / 支付 / SLA、法条逐条法务复核与资质核验，均属外部依赖，不在本仓库内闭环。

### 回归
- ruff 全仓通过、pytest **198 项**全绿、规则评测 **75/75**（高危检出 100%、干净误报 0%）；软件包版本升至 **0.7.8**（核心规则库 v1.4，行业插件 v1.0）。

### 文档
- 新增 `docs/CAPABILITY_TIERS.md`：上架口径能力三档分档（A 可写进卖点 / B 骨架·可选 / C 不可承诺）；Gig、远程渠道、README 与边界文档对齐 198 单测、75/75 评测、性能基准与身份/配额/审计/缓存骨架边界。

## [0.7.7] - 2026-11-23

平台化计量与留痕补强：token 用量回填配额、超额/停用请求拦截、审计/反馈可选 SQLite 后端；运行时判定 API 与规则结论向后兼容，默认行为不变。

### 新增
- **token 回填**：HTTP 鉴权后把 `(meter, tenant)` 挂入请求上下文，`pipeline` 结束后把本次 LLM `total_tokens` 回填到归属租户；无归属或纯规则调用不回填，回填异常不阻断主流程。
- **配额预检拦截**：放行前校验租户状态——未注册 / 停用返回 `403`，调用次数超额返回 `429`；存储异常按放行处理（`store_error`），避免存储故障阻断全部流量。
- **审计 / 反馈 SQLite 后端**：`LCG_AUDIT_LOG` / `LCG_FEEDBACK_LOG` 路径按扩展名分流——`.jsonl`/`.json`/普通文件走 JSONL，`.db`/`.sqlite`/`.sqlite3` 或 `:memory:` 走 SQLite；两种后端读回结构一致，CSV 导出不变。
- 新增 `lcg.ledger`：DSN 判定与 SQLite 连接缓存工厂；`lcg.request_ctx`：请求级租户上下文（contextvar）。

### 边界（仍未实现）
- token 超额的强制拦截、按 token 配额停用；外置持久化计量与账单/套餐对接；账号注册登录、角色权限、Key 签发轮换、审计到人。
- 审计/反馈的检索界面、留存策略与跨进程共享；仍为本机单进程持久化骨架。

### 回归
- ruff 全仓通过、pytest **177 项**全绿、规则评测 **75/75**（高危检出 100%、干净误报 0%）；软件包版本升至 **0.7.7**（核心规则库 v1.4，行业插件 v1.0）。

## [0.7.6] - 2026-11-23

HTTP 配额计量接线：Key→租户映射与请求级调用计数；判定 API 与规则结论向后兼容。

### 新增
- **Key→租户映射**：`server_http` 解析 `LCG_KEY_TENANTS`（逗号分隔 `key=tenant_id`），把访问 Key 映射到配额租户；非法片段（无 `=`、空 key/tenant）跳过。
- **请求级调用计数**：鉴权通过后，按映射租户记一次 calls 到 `UsageMeter`，存储复用 `LCG_STORE_DSN` 选择内存 / SQLite；未映射 Key 不计费，计量异常不阻断主流程。

### 边界（仍未实现）
- 不做 token 用量回填配额、不做超额 / 停用请求拦截；无账号注册登录与角色体系；token 计量仍由 LLM 层透传，未贯穿到配额。
- 审计 / 反馈仍为本地 JSONL，本轮未迁关系库。

### 回归
- ruff 全仓通过、pytest **163 项**全绿、规则评测 **75/75**（高危检出 100%、干净误报 0%）；软件包版本升至 **0.7.6**（核心规则库 v1.4，行业插件 v1.0）。

## [0.7.5] - 2026-11-23

平台化骨架补强：可选 SQLite 配额持久化、HTTP 多 Key 鉴权、ASR/OCR 识别适配器协议；运行时判定 API 与规则结论向后兼容，默认行为不变。

### 新增
- **SQLite 配额后端**：`lcg.tenant` 新增 `SQLiteQuotaStore`（标准库 sqlite3，零第三方依赖）与 `quota_store_from_env` 工厂；`LCG_STORE_DSN` 为空走进程内存，文件路径落盘持久化，`:memory:` 为内存库。配额口径与内存实现一致，用量可跨连接复用。
- **HTTP 多 Key 鉴权**：`lcg.server_http` 支持 `LCG_BEARER_TOKENS`（逗号分隔多 Key），与单值 `LCG_BEARER_TOKEN` 合并生效；仍为静态共享凭证，不做账号 / 角色体系。
- **识别适配器协议**：`lcg.sources` 新增 `Recognizer` 协议与 `StubRecognizer` 桩，把媒体负载适配为文本片段交 `ingest` 归一；不内置真实 ASR/OCR 模型、不发起网络请求，真实后端由部署方接入。

### 变更
- `UsageMeter.snapshot` 改为通用读取底层 store 的快照方法，不再限定内存实现。
- 文档：`DEPLOYMENT.md` / `SCOPE_BOUNDARY.md` 同步现状基础与边界；审计 / 反馈仍为本地 JSONL，本轮未迁移关系库。
- 回归：ruff 全仓通过、pytest **161 项**全绿、规则评测 **75/75**（高危检出 100%、干净误报 0%）；软件包版本升至 **0.7.5**（核心规则库 v1.4，行业插件 v1.0）。

### 未实现（外部条件 / 产品边界）
- 真实 ASR/OCR 服务接入、外置数据库 / 对象存储、账号注册登录与角色权限、生产部署与支付对接、强监管行业规则转实、资质真伪核验、法律意见判定，仍需外部凭证 / 法务复核 / 部署资源，见 `docs/DEPLOYMENT.md` 第 5、6 节。

## [0.7.4] - 2026-11-23

规则层紧凑归一化补强：拦截斜杠 / 竖线 / 反斜杠分隔的阻断变体；判定 API 与规则结论向后兼容。

### 新增
- **紧凑层分隔符剥离**：`models.normalize_compact` 剥离集在空格 / 中点 / emoji 之外，新增斜杠 `/`、竖线 `|`、反斜杠 `\` 三个纯并列 / 装饰分隔符，可拦“最/好”“最|好”“最\好”“v/x：abc12345”“薇/信 abc12345”等被分隔符拆开的绝对化词与联系方式。
- **评测与单测扩充**：对抗集新增斜杠分隔绝对化、斜杠分隔导流两条召回用例；良性集新增并列斜杠（男/女、大/小）防误报用例；`test_normalize.py` 补分隔符剥离下标映射、分隔阻断召回与句子边界 / 并列斜杠防误报共 6 例。

### 变更
- **边界保持**：中文逗号 / 感叹号 / 问号 / 括号等句子停顿成分仍保留，紧凑层不跨标点合并；谐音 / 拼音 / 拆字还原仍归 LLM 语义层，规则层不做。
- 在线 LLM 快照复跑：**40/40**（语义召回 3/3、红队阻断 6/6、LLM 零误报 31/31；Qwen3-14B 主、DeepSeek-V3 兜底），结果随模型版本与余额波动，以 `reports/LLM_EVAL.md` 为准。
- 回归：ruff 全仓通过、pytest **146 项**全绿、规则评测 **75/75**（良性 31、对抗 44；高危检出 100%、干净误报 0%）；软件包版本升至 **0.7.4**（核心规则库 v1.4，行业插件 v1.0）。
- **在线 LLM 快照刷新**：配 key 复跑 `scripts/run_llm_evals.py`，语义召回 **3/3**、红队阻断 **6/6**（检测抗注入 4 ＋ 改写抗越狱 2）、LLM 零误报 **31/31**，合计 **40/40**；主模型 `Qwen/Qwen3-14B`，40 次调用，无降级 / 解析错误。快照见 `reports/LLM_EVAL.md`；在线结果随模型版本与账户余额波动，非离线 CI 门禁。

## [0.7.3] - 2026-11-23

成品样例与对外物料补齐；输入源 / 配额计量骨架与强监管占位插件落地；运行时判定 API 与规则结论不变。

### 新增
- **周报导出脚本** `scripts/export_report.py`：离线生成整场 HTML 周报（风险分布 / 类别 / 主播分级 / 待整改 / 明细）、批量 CSV、改写前后对照 CSV、反馈导出 CSV；零第三方依赖，支持 `--input` / `--industry` / `--platform` / `--out-dir`。
- **成品样例** `samples/`：由脚本可复现的报告与对照表快照（虚构示例数据，不代表真实客户 / 场次），附字段说明与复现命令。
- **英文 README** `README.en.md` 与 **Gig 文案草稿** `docs/GIG_LISTING.md`：能力清单、交付档位骨架、边界与平台内交易口径；定价留空待发布人确定。
- **输入源协议骨架** `src/lcg/sources.py`：`TranscriptSource` 协议 + `ListSource` / `StubSource` 内存实现；不含真实 ASR/OCR、不发网络请求。
- **配额计量骨架** `src/lcg/tenant.py`：进程内租户注册、调用 / token 扣减与用量快照；无持久化、无鉴权、不跨进程共享。
- **强监管 / 跨境占位插件** `rules/plugins/_medical/_finance/_education/_alcohol/_crossborder.json`：空规则占位、`pending_legal_review`，下划线前缀不参与加载。

### 变更
- 文档口径同步：DEPLOYMENT / SCOPE_BOUNDARY 标注 tenant / sources 为骨架、占位插件未启用；README 架构段与导航补 samples、英文 README、GIG 草稿。
- 回归：ruff 全仓通过、pytest **140 项**全绿、规则评测 **72/72**；软件包版本升至 **0.7.3**（核心规则库 v1.4，行业插件 v1.0）。

## [0.7.2] - 2026-11-23

演示走查脚本、录屏分镜文档、治理层底层件与 CI 守门补齐；运行时判定 API 与规则结论不变。

### 新增
- **离线演示脚本** `scripts/demo_walkthrough.py`：分 9 节走查合规放行、高危拦截、变体绕过、行业插件、整场批量、批量聚合/输入适配/反馈闭环/审计事件、改写闭环、LLM 融合/降级、性能快照；支持 `--offline`（强制纯规则、不耗额度）与 `--json`（结构化输出），零第三方依赖、离线可跑。
- **录屏分镜与口播脚本** `docs/DEMO_SCRIPT.md`：开场到收尾逐镜的命令、屏幕预期、中文口播与 English voiceover，附录制前准备、剪辑上架口径红线与复现命令清单。
- **输入适配** `src/lcg/ingest.py`：把上游 ASR/字幕/表格的异构片段（dict/list/tuple/str）归一为 `scan_batch` 契约；本服务不做 ASR/OCR，只消费已转写文本，空片段丢弃、seq 缺省重排。
- **整场聚合** `src/lcg/aggregator.py`：对批量结果做风险等级分布、命中类别、按主播最高风险/分段数/high 命中数与待整改清单统计；只归类不改判定结论。
- **反馈闭环** `src/lcg/feedback.py`：误报/漏报/存疑记录到本地 JSONL（`LCG_FEEDBACK_LOG`，未配置则禁用），支持读回与 UTF-8 BOM CSV 导出，作为规则迭代与评测扩充输入。
- **本地审计留痕** `src/lcg/audit.py`：可选 JSONL 事件落盘（`LCG_AUDIT_LOG`），默认关闭；`LCG_AUDIT_REDACT=1` 时不写原始话术、仅留长度与截断命中片段；写盘异常不影响主流程。
- **输入源协议骨架** `src/lcg/sources.py`：定义 `TranscriptSource` 协议与 `ListSource`/`StubSource` 内存实现，统一交付给 `ingest` 归一；不含真实 ASR/OCR 模型、不发起网络请求。
- **配额计量骨架** `src/lcg/tenant.py`：进程内租户注册、调用/token 扣减与用量快照（`InMemoryQuotaStore`/`UsageMeter`）；无持久化、无鉴权、不跨进程共享，生产多租户需外置存储与账号体系（见 DEPLOYMENT.md）。
- **行业插件模板与占位骨架**：`rules/plugins/_template.json` 为模板；`_medical/_finance/_education/_alcohol/_crossborder.json` 为空规则占位（`status: placeholder`、`pending_legal_review`），下划线前缀不参与聚合加载与校验；新增插件流程见 `CONTRIBUTING.md`。
- **部署与平台化演进文档** `docs/DEPLOYMENT.md`：梳理当前单租户自托管边界、配置项速查、生产部署建议，以及多租户/鉴权/配额计费/存储/无状态化等尚未实现的演进方向，避免把路线图当成现有功能。

### 变更
- **LLM 配置清洗加固**：未知 provider 回退 siliconflow 并记录；非法超时、负调用预算、负单价回退默认值，原因写入 `config.warnings`，非法 env 不导致服务崩溃。
- `rules_store` 跳过下划线前缀插件文件；`CONTRIBUTING.md` 补充新增行业插件的完整流程。
- CI 增加 Ruff 静态检查与 wheel 打包守门（构建后解包断言规则词库随包打入，防止独立安装后加载空词库）。
- 清理 `evals/run_evals.py` 历史 lint：import 排序、移除未用导入、去除冗余 f 前缀、长行折行。
- 回归：ruff 全仓通过、pytest **140 项**全绿、规则评测 **72/72**；软件包版本升至 **0.7.2**（核心规则库 v1.4，行业插件 v1.0）。

## [0.7.1] - 2026-11-23

LLM token usage 计量落地、规则评测集扩充、成本基准口径刷新。规则核心判定与对外 API 向后兼容。

### 新增
- **token usage 采集与透传**：`OpenAIBackend` 解析 `comp.usage`，`JudgeResult` 与 `llm` 审计 meta 增加 `prompt_tokens` / `completion_tokens` / `total_tokens`；检测与自然改写两条链路均透传；缓存命中沿用基准那次用量，主备切换仅成功调用计 token。
- **成本单价配置**：`LCG_PRICE_INPUT_PER_MTOK` / `LCG_PRICE_OUTPUT_PER_MTOK`（每百万 token，币种随 provider 账单）；`scripts/bench_perf.py` 抽样汇总输入/输出/总 token，配置单价后自动估算金额，未配置则只报 token 量、不报金额。
- 规则评测集 51 → **72 条**（良性 30、对抗 42）：补充通用家电/箱包/客服/序数、食品原料与饮品、化妆品护发/面膜等防误报用例，以及虚假承诺、投资诱导、站外私下交易、食品/化妆品医疗与速效宣称、迷信功效等对抗召回用例。

### 变更
- **打包词库修复**：wheel 原先仅打入 `lcg/*.py`，运行时规则 JSON（核心包 + food/cosmetics 插件）未随包分发，pip 独立安装后引擎会加载空词库；现通过 hatch `force-include` 将 `rules/` 映射到 `lcg/rules`，`rules_store` 按「包内资源 → 源码布局 → 进程 cwd」三候选解析规则目录；已隔离安装到项目外目录验证 20 条规则正常加载。
- 性能基准 `reports/PERF.md` 成本段由"公式占位"改为真实 usage 汇总；规则层本机复测约 1.9ms / P95 2.7ms / 约 520 句/秒（相对值，随机器负载波动）。
- 回归：pytest **96 项**全绿、规则评测 **72/72**（高危检出 100%、干净误报 0%）。
- 软件包版本升至 **0.7.1**（核心规则库 v1.4，行业插件 v1.0）。

### 未闭环（需现实动作，非工程可替代）
- 在线规模化红队、demo 录屏、新行业插件 / 英文跨境规则、法条与平台规则法务复核仍待外部条件，见 README Roadmap。

## [0.7.0] - 2026-11-23

工程与文档补齐：扩充评测与性能基准、补齐合规依据/边界/上架文档，并修掉一处站外导流规则盲区。规则核心 API 不变。

### 新增
- **性能与成本基准脚本** `scripts/bench_perf.py`：离线测规则层单句延迟（avg/P50/P95/max）、吞吐与批量均摊；LLM 层抽样记录 mode/状态/模型/调用次数/延迟。结果写入 `reports/PERF.md`（本机测量，仅供相对比较；后端未回传 token usage，精确单句成本待接入 usage 后核算）。
- **合规依据对照表** `docs/COMPLIANCE_MAPPING.md`：核心 14 条 ＋ 食品 3 条 ＋ 化妆品 3 条，逐条对齐风险级、适用范围、法条/平台依据与复核状态；未核验项统一标注"待法务/平台复核"，不伪造背书。
- **承接范围与能力边界** `docs/SCOPE_BOUNDARY.md`：覆盖行业/平台、明确不承接的强监管领域、规则层与 LLM 层技术边界、人工复核义务与免责声明。
- **MCP 分发与上架说明** `docs/MCP_MARKETPLACE.md`：分发形态、上架材料清单、发布前 checklist、渠道与发布前待办；新增项目级配置 `.mcp.json`，`pyproject.toml` 补检索关键词。

### 变更
- **规则库 v1.4**：四平台站外导流规则补入"扫码/进群/私下转账"（各 3 词，共 +12），修复"扫码进群、私下转账"变体在规则层漏报的盲区；规则条数 14、替换建议 16 不变。
- 评测集由 37 条增至 **51 条**（良性 21、对抗 30）：新增 a23–a30（导流变体、虚构原价、多绝对化叠加、翡翠升值、食品/化妆品功效、迷信伪科学等）与 b16–b21（家电/服装/翡翠证书/食品/化妆品/客服话术防误报）。
- 回归：pytest **91 项**全绿、ruff 全过、`export_rules.py --check` 一致、规则评测 **51/51**（高危检出 100%、干净误报 0%）。
- 软件包版本升至 **0.7.0**（核心规则库 v1.4，行业插件 v1.0）。

### 未闭环（需现实动作，非工程可替代）
- 仓库仍为 **Private**，需所有者在网页 Settings 切 Public 或提供 repo 权限 PAT 后才能进 MCP 目录；CI 徽章待公开且 Actions 跑通后显示。
- 法条条款序号、平台规则版本与链接待法务/官方规则中心复核。

## [0.6.0] - 2026-10-07

LLM 语义层真实联调（M6）：用硅基流动真实密钥把「规则＋LLM 融合检测、红队抗性、自然改写」全链路跑通，并固化为可复跑的在线评测；检测 prompt 经实测迭代到 detect-v3。

### 新增
- **在线 LLM 评测运行器** `scripts/run_llm_evals.py`（需模型 key、手动复跑，**不进离线 CI**）：裁决三组——①语义召回（semantic 3 条，规则层必然漏检，须由 LLM 补判到期望严重度且命中 `source=llm`）；②红队阻断（redteam 4 条检测抗注入 ＋ r01/r04 改写抗越狱，改写后复检须 clean 且不残留违规核心词）；③LLM 零误报（benign 15 条接入模型后不得超出该用例期望严重度）。结果写入 `reports/LLM_EVAL.md`（含日期 / 模型 / prompt 版本 / 调用数的快照）。
- **红队评测报告** `reports/SECURITY.md`：威胁模型、评测方法、四条注入 / 越狱用例的阻断结果，以及多层缓解设计（规则硬底线只增不减、结构化强解析失败安全回退、改写复检 gate、模型不被接管）。
- 检测 prompt 升级 **detect-v3**：补「严重度判定口径」（站外导流、暗示疗效、暗示升值等硬违法即使不出现原词也一律 high）、谐音导流与违规判定示例，以及**合规放行白名单与正例**（蓝帽保健食品法定功能 ＋ “本品不能代替药物”声明、化妆品普通 / 特证功效、敏感肌 / 提亮肤色等），在把语义漏检拉到 high 的同时保证合规话术零误报。

### 变更 / 实测结论（硅基流动 OpenAI 兼容接口）
- 模型选型经 6 个模型同 prompt 横向实测：主力 **Qwen/Qwen3-14B**、兜底 **deepseek-ai/DeepSeek-V3**（均支持 `response_format=json_object`）；Qwen3-8B 对“薇芯”谐音导流漏判故弃用，`zai-org/GLM-4.5-Air` 不支持 JSON mode，Qwen3.5-9B 思考超时。
- 真实结果（Qwen3-14B ＋ detect-v3，24 次调用）：语义召回 **3/3**、红队阻断 **6/6**、LLM 零误报 **15/15**，合计 **24/24**；高危翡翠话术与越狱文本的 LLM 自然改写均通过规则复检 clean，未被诱导产出违规内容。
- `.env.example` 更新推荐模型路由与实测注意事项；`.env` 仍被 `.gitignore` 强制忽略，密钥绝不入库。
- 离线规则门禁保持不变：pytest **91 项**全绿、规则评测 37/37（100%、干净误报 0）；软件包版本升至 **0.6.0**（核心规则库仍 v1.3、行业插件 v1.0）。

## [0.5.0] - 2026-10-07

规则规模化（M5）：把单文件规则库升级为「**核心包 ＋ 行业插件包**」插件化架构，并落地首批两个法规最明确、直播违规最高频的行业包——食品 / 保健食品、化妆品。全部法条条款号经权威库逐条核实。

### 新增
- **规则库插件化**：核心包 `rules/rules.v1.json`（通用 ＋ 平台 ＋ 翡翠，保持 v1.3、14 规则 / 16 替换不变）之外，新增 `rules/plugins/<name>.json` 行业插件包；`rules_store` 启动时聚合加载并逐包校验（插件规则 `scope` 必须等于 `industry:<meta.industry>`），行业之间天然隔离、互不串扰，新增行业无需改动引擎。
- **食品 / 保健食品插件包** `rules/plugins/food.json`（3 规则 / 8 替换，v1.0）：①疾病治疗宣称（《广告法》第 17 条、《食品安全法》第 73 条）；②功效安全性断言保证（《广告法》第 18 条、广告审查管理暂行办法第 11 条）；③医疗代言与健康恐惧（medium）。
- **化妆品插件包** `rules/plugins/cosmetics.json`（3 规则 / 8 替换，v1.0）：①医疗作用宣称 / “药妆”（《化妆品监督管理条例》第 37、43 条、《广告法》第 17 条）；②速效与安全性断言（广告审查标准第 100 条、《广告法》第 9、28 条）；③贬低同类与无依据数据（medium）。
- 新增 `tests/test_plugins.py`（25 项）：包结构 / 法条来源完整性、行业隔离、食品与化妆品违规召回，以及合规话术零误报——法定声明“本品不能代替药物”、备案保健功能“增强免疫力”、保湿补水、美白防晒双特证、敏感肌、提亮肤色、合规“祛痘”“修护屏障”。
- 评测集新增食品、化妆品良性 / 对抗各 4 条（b08–b15、a15–a22）；规则层评测由 21 条增至 **37 条**，仍 100% 通过、干净误报率 0%。

### 变更
- `scripts/export_rules.py` 由单文件守门升级为「逐文件规范化 / 校验 ＋ 聚合视图校验」，CI `--check` 同时校验核心包与每个插件包；聚合后全局 **20 条规则 / 31 条替换**（食品与化妆品包共用“无副作用”一条中性替换，替换表按词去重）。
- `models.INDUSTRIES` 由 `jadeite/general` 扩展为 `jadeite/general/food/cosmetics`；HTTP `healthz` 暴露的全局规则数随之变为 20。
- 行业包只收录核心包未覆盖的行业增量词与组合，避免同词跨类重复计数；备案目录内保健功能、合规化妆品功效与特殊化妆品注册功效刻意放行，资质 / 备案范围识别超出规则层能力，留给 LLM 语义层与人工。
- pytest 由 66 项增至 **91 项**；软件包版本升至 **0.5.0**（核心规则库仍为 v1.3，行业插件包各自为 v1.0）。

## [0.4.0] - 2026-10-06

规则引擎确定性召回增强（B4 高级归一化）：在**不依赖模型 key** 的前提下，把一批原本只能交给 LLM 的字形变体下沉到免费、离线、可复现的规则层。

### 新增
- 等长层新增**常用繁体字一对一转简体**（`models.normalize_text`）：全角 / 繁简 / 大小写均为 1→1 等长映射，下标不失真，繁体话术（全網銷量第一、絕對、穩賺不賠、養生辟邪等）直接命中现有规则。
- 新增**紧凑归一化** `models.normalize_compact` 与引擎第二匹配通道：在等长归一化之上剔除空白、零宽字符、emoji 与插入式装饰符（`· ・ • . - _ ~ * # ^`），并通过「紧凑下标 → 原文下标」映射无损还原命中区间，可拦“最 好”“NO·1”“微❤️abc12345”等插空格 / 符号 / emoji 阻断；刻意保留中文标点与句子边界，不跨句合并。
- 新增 `tests/test_normalize.py`（14 项）：繁简等长、紧凑下标映射、三类阻断变体召回、中文标点不合并、英文 `voucher` 不误判导流、紧凑命中不重复计数、紧凑命中参与改写闭环。
- 评测集新增对抗用例 a12–a14（空格 / 中点 / emoji 阻断，规则层现可判 high）；规则层评测由 18 条增至 **21 条**，仍 100% 通过。

### 变更
- 站外导流正则收紧为“**词首 v / 中文引导字 ＋ 号码必须含数字**”（四平台统一）：修复英文正常句中 `voucher` / `provide` 等含 v 单词被误判导流的隐患；该严格正则同时用于等长与紧凑通道。
- 命中词替换查找增加紧凑键兜底：被阻断的命中（如“最 好”）能正确映射到“最好”的合规替换文案并通过复检。
- `get_rules` 透出可选 `patterns_compact` 字段（本版规则未使用，紧凑通道默认回退 `patterns`）。
- pytest 由 52 项增至 **66 项**；软件包版本升至 **0.4.0**。

### 规则库
- `meta.version` 升至 **v1.3**：引擎归一化能力升级（繁简等长 ＋ 阻断符紧凑合并 ＋ 导流正则收紧）；规则条数 14、替换建议 16 不变。
- 谐音（薇芯）、近义暗示（“老毛病不闹腾了”“越来越值钱”）等字形归一化仍无法可靠识别的 3 条保留在语义层待跑集 `semantic.jsonl`，配模型 key 后裁决。

## [0.3.0] - 2026-10-06

在规则内核之上引入 **LLM 语义层**，从“纯关键词规则”升级为“规则硬底线 ＋ LLM 语义融合”；无 key 或模型侧故障时全自动降级，服务始终可用。

### 新增
- 新增 `lcg.llm`：OpenAI 兼容语义客户端（硅基流动 / 魔搭 / OpenRouter 仅 base_url 不同），含环境配置（C1）、Provider 抽象（C2）、主备路由＋一次重试（C3）、JSON 强解析（C4）、Prompt 模板版本化 `detect-v1`/`rewrite-v1`（C7）、进程内调用预算与入参哈希缓存（C8）；`openai` 延迟导入，未安装或无 key 不影响纯规则服务。
- 新增 `lcg.pipeline` 融合编排（C5/C6/C9）：`analyze()` 中规则永远先跑且为硬底线，LLM 只能补充命中、**不能降低**规则结论，最终风险取二者最高；`smart_rewrite()` 优先 LLM 自然整句改写并做规则复检，复检不通过或 LLM 不可用即回退规则机械替换并标 `needs_human_review`。
- 新增两个 MCP 工具 `scan_smart`、`rewrite_smart`（工具总数 4→6），返回 `mode`（`rules_only` / `rules_plus_llm`）、逐命中 `source`（`rule`/`llm`）与 `llm` 审计元数据（`status`/`model`/`prompt_version`/`cached`/`calls`/`error`）。
- 新增 `tests/test_llm.py`（20 项）：用可注入 `FakeBackend` 在无网络、无 key 下验证硬底线、六类降级（禁用 / 无 key / 脏 JSON / 异常 / 超预算 / 未配模型）、语义补充与 span 定位、重复抑制与更严重升级保留、缓存、主备切换、改写采用 / 拒绝 / 回退、配置解析。
- 新增语义层待跑评测集 `evals/cases/semantic.jsonl`（6 条：谐音“薇芯”、插空格拆“最好”、暗示疗效、暗示升值、`NO·1` 变体、emoji 阻断导流，已确认规则层全部漏检）；`run_evals.py` 对其计数，配置模型 key 后由 LLM 层裁决。
- `.env.example` 新增 `LCG_LLM_ENABLED/PROVIDER/BASE_URL/API_KEY/TIMEOUT/MAX_CALLS` 配置说明。

### 变更
- `engine.Hit` 新增 `source` 字段（默认 `rule`，向后兼容）；pytest 由 32 项增至 **52 项**。
- `server.py --selftest` 增加语义融合入口断言（高危句融合后必须仍为 high）。
- 软件包版本升至 **0.3.0**（pyproject / package.json / `lcg.__version__`）；规则库内容版本仍为 **v1.2**（本版未改规则数据）。
- `deploy/Dockerfile` 改为安装 `.[http,llm]`，公网镜像内置语义层（模型 key 由平台 Secret 注入）。

## [0.2.0] - 2026-10-06

在 0.1.0 工程化基线上补齐语义消歧、改写闭环、远程传输与协议级测试。

### 新增
- 远程 MCP 入口 `lcg.server_http`：Streamable HTTP（端点 `/mcp`）、免鉴权健康检查 `GET /healthz`、可选纯 ASGI Bearer 鉴权（环境变量 `LCG_BEARER_TOKEN`，不缓冲、兼容 SSE 流式），监听由 `LCG_HTTP_HOST`/`LCG_HTTP_PORT` 控制；新增 `create_mcp()` 工厂，stdio 用模块单例、HTTP 每次构建独立实例（FastMCP 会话管理器每实例只能启动一次）。
- `safe_rewrite` 新增改写闭环字段：`rewritten`（按命中区间替换拼回的改写全文）、`rewritten_risk`、`rewritten_clean`（对改写文本再扫描复检），原有字段保持不变。
- 新增协议级测试 `tests/test_stdio_mcp.py`（stdio 子进程握手、列举 4 工具、调用、非法入参错误）与 `tests/test_http.py`（真实本地随机端口验证 healthz、Bearer 401/放行、HTTP MCP 握手与调用）。
- 评测集由 15 条增至 **18 条**：新增序数良性用例 b06/b07 与排名对抗用例 a11；`run_evals.py` 报告抬头改为动态读取规则版本。

### 变更
- “第一”序数语义消歧（B5）：后接顺序/序量词（第一步、第一款、第一期、第一产业、第一人称等）不再判排名绝对化；“销量第一/行业第一/第一名”等排名用法仍判 high。
- pytest 由 21 项增至 **32 项**；开发依赖新增 `pytest-asyncio`、`uvicorn`，pyproject 新增 `http` optional-dependency（`pip install ".[http]"`）。
- 软件包版本升至 **0.2.0**（pyproject / package.json / `lcg.__version__`）。

### 规则库
- `meta.version` 升至 **v1.2**：引擎层新增“第一”序数语义消歧；规则条数 14、替换建议 16 不变。

## [0.1.0] - 2026-10-06

首个可对外的最小可用版本（MVP），完成规则引擎分层重构与工程化加固。

### 新增
- 规则引擎重构为可安装包 `src/lcg/`，分层为 `models`（常量/校验/归一化）、`rules_store`（JSON 加载）、`engine`（纯逻辑）、`server_stdio`（FastMCP stdio 薄封装）。
- `rules/rules.v1.json` 成为**唯一事实源**，运行时直接加载；Python 与未来 TS/Cloudflare 运行时共用同一份语言无关规则。
- 新增**等长输入归一化**（`lcg.models.normalize_text`）：全角字母/数字/符号转半角、英文小写，不增删字符，命中下标可无损映射回原文；可识别全角“１００％”“ｖｘ：ａｂｃ…”等绕过变体。
- 新增 pytest 单元测试 `tests/test_engine.py`（21 项）与 `tests/conftest.py`，覆盖核心判定、批量聚合、行业隔离、改写、归一化、非法入参、边界输入、规则库加载、stdio 实例化。
- 新增 `CHANGELOG.md`、`SECURITY.md`（安全策略）、`CONTRIBUTING.md`、GitHub issue 模板。
- 根 `server.py` 支持 `--version`。

### 变更
- 根 `server.py` 退化为**向后兼容 shim**：re-export `lcg.engine` 公共 API，旧脚本 `import server` 与 `python server.py` 行为不变。
- `scripts/export_rules.py` 角色反转：不再从 Python 源码导出规则，改为规则 JSON 的**规范化写回 + 一致性校验**（`--check` 用于 CI 守门）。
- 依赖钉到已验证版本：`mcp>=1.27.2`、`openai>=3.11.0`、`httpx>=0.28.1`；Node 开发工具精确钉版 `@modelcontextprotocol/inspector@2.9.0`、`promptfoo@0.123.1`。
- 软件包版本统一为 `0.1.0`（pyproject / package.json）。
- CI 在规则校验、基线、评测之外新增 `pytest` 单元测试环节。
- 评测集由 13 条增至 **15 条**（新增 2 条全角变体对抗用例）。

### 修复
- 修复“泛化最高级”正则把多字词 `便宜/划算/先进` 误放进字符类导致永远无法匹配的缺陷，改为 `最(?:[好佳大低高美强优新先]|便宜|划算|先进)`。
- 修正根 `server.py` 文档字符串中工具名与实际 MCP 工具名不一致的问题。

### 规则库
- `meta.version` 升至 **v1.1**：修正泛化最高级正则；规则层新增全角等长归一化。规则条数 14、替换建议 16 不变。

### 暂未纳入（当时计划，后续进展见 README Roadmap）
- 繁简/谐音/emoji/拆字等高级归一化与 LLM 语义消歧（B4/B5）。
- 法条条款号/版本/URL 元数据深化（B6）、改写后再扫描闭环（B7）。
- MCP 协议一致性握手测试（B9）、Streamable HTTP + 鉴权入口 `server_http`、LLM 语义层与对模型红队报告 `reports/SECURITY.md`。
