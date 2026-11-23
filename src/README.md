# src/lcg/ —— 规则引擎包（能力标准件 ①，已落地 v0.5.0）

规则引擎已从单文件 `server.py` 重构到本包，做到**规则数据、判定逻辑、传输方式三层解耦**，
并以语言无关的 `rules/rules.v1.json` 为唯一事实源。根目录 `server.py` 现为向后兼容 shim。

## 已落地结构
```
src/lcg/
├── __init__.py     # 公共 API 导出 + __version__
├── models.py       # 枚举常量、validate_context()、normalize_text()/normalize_compact()（等长+紧凑归一化，零依赖）
├── rules_store.py  # 聚合加载核心包 rules.v1.json ＋ plugins/*.json 行业插件并逐包校验，active_rules(industry, platform)（零依赖）
├── engine.py       # detect / scan_batch / suggest_rewrite / get_rules 纯逻辑（零依赖；规则硬底线）
├── llm.py          # LLM 语义客户端：config / OpenAI+Fake 后端 / Judge / 主备 / 预算缓存 / 强解析（openai 可选）
├── pipeline.py     # analyze / smart_rewrite：规则硬底线＋LLM 融合与六类自动降级
├── server_stdio.py # FastMCP stdio 入口，6 个工具薄封装（依赖 mcp）
└── server_http.py  # Streamable HTTP 入口：/mcp + /healthz + 可选 Bearer（依赖 mcp/uvicorn）
```

## 分层约束
- `models / rules_store / engine` **零第三方依赖**，可被任意 Python 环境与未来 TS 运行时复用同一份 JSON。
- 判定逻辑只允许出现在 `engine`；`server_stdio`、`server_http` 只做传输与参数封装（工具注册统一走 `create_mcp()` 工厂）。
- 归一化分两层，均在 `models.py`：`normalize_text` 为等长层（全角/大小写/常用繁→简，1→1 下标无损）；`normalize_compact` 为紧凑补漏层（剔除空格/零宽/emoji/装饰符并经下标映射还原，保留中文标点与句子边界）。谐音、拆字、emoji 替字、近义暗示等仍需上下文判断的变体交给 LLM 层。
- 非法 `industry/platform` 在 `engine` 入口经 `validate_context` 抛 `ValueError`。

## 已完成（v0.1.0）
1. `rules_store` 直接加载 JSON 并做结构/计数校验；`active_rules` 按 scope 过滤。
2. `engine` 承接全部判定，输出字段与旧单文件版逐字一致。
3. 根 `server.py` 退化为 shim，`server.detect is lcg.engine.detect`；`tests/run_baseline.py` 与 `evals/run_evals.py` 保持全绿，另增 pytest 21 项直接覆盖 `lcg.*`。
4. `server_stdio` 初始提供 4 个 MCP 工具（scan_text / scan_livestream / compliance_rules / safe_rewrite）；v0.3.0 起增至 6 个（另加 scan_smart / rewrite_smart），详见 `docs/TOOL_SCHEMA.md`。
5. `scripts/export_rules.py` 反转为 JSON 规范化 + `--check` 一致性守门。

## 已完成（v0.2.0 增量）
1. `models.is_ordinal_first` + `engine`：“第一”序数消歧（次序用法放行，排名/榜首仍 high）。
2. `engine.suggest_rewrite` 新增改写闭环：输出 `rewritten` 全文，并复检 `rewritten_risk` / `rewritten_clean`。
3. `server_http.py`：Streamable HTTP（`/mcp`）+ `/healthz` + 可选纯 ASGI Bearer（`LCG_BEARER_TOKEN`，兼容 SSE 流式）；`create_mcp()` 工厂让 stdio 用单例、HTTP 每次构建独立实例。
4. 新增 `tests/test_stdio_mcp.py`、`tests/test_http.py` 协议级测试；pytest 增至 32 项；规则升 v1.2，评测增至 18 条全部通过。

## 已完成（v0.5.0 增量：规则规模化 / 行业插件化）
1. 规则库升级为「核心包 ＋ 行业插件包」：新增 `rules/plugins/food.json`、`cosmetics.json`（各 3 规则 / 8 替换，v1.0，法条条款号经权威库核实）；`rules_store` 聚合加载、逐包校验（插件 scope 必须为 `industry:<name>`）、行业隔离；核心包保持 v1.3、14/16 不变，聚合全局 20 规则 / 31 替换。
2. `models.INDUSTRIES` 增 `food`/`cosmetics`；`export_rules.py` 升级为逐文件规范化/校验 ＋ 聚合视图校验，CI `--check` 覆盖核心与全部插件。
3. 新增 `tests/test_plugins.py`（25 项，含合规话术零误报）；评测集加 b08–b15、a15–a22，规则层评测 37 条全过、干净误报 0%；pytest 增至 91 项。软件升 v0.5.0。

## 已完成（v0.4.0 增量：B4 高级归一化，规则库 v1.3）
1. `models` 新增常用繁体一对一转简体（等长）与 `normalize_compact` 紧凑层（剔除空格/零宽/emoji/装饰符，下标映射还原，保留中文标点不跨句合并）。
2. `engine` 新增紧凑补漏通道：等长层结果完全冻结，紧凑层只补未命中区间、按原文区间去重不重复计数；导流四平台正则收紧为“词首信号＋号码含数字”，修复英文 `voucher` 误报；`get_rules` 透出 `patterns_compact`。
3. 命中替换查找加紧凑键兜底（“最 好”按“最好”替换并复检 clean）。
4. 新增 `tests/test_normalize.py`（14 项）；对抗集加 a12–a14，规则层评测 21 条全过；语义待跑集收敛为 3 条；pytest 增至 66 项。规则数据升 v1.3（14 规则 / 16 替换不变）。

## 已完成（v0.3.0 增量：LLM 语义层）
1. 新增 `llm.py`：OpenAI 兼容客户端（硅基流动/魔搭/OpenRouter），环境配置、主备路由＋一次重试、JSON 强解析、Prompt 版本化（`detect-v1`/`rewrite-v1`）、调用预算与入参哈希缓存；`openai` 延迟导入，未装/无 key 不影响服务。
2. 新增 `pipeline.py`：`analyze()` 规则永远先跑且为硬底线（LLM 只能补充、不能降低），风险取最高、同区间去重、更严重判断保留；`smart_rewrite()` 中 LLM 自然改写复检 clean 才采用，否则回退规则替换并标 `needs_human_review`；六类故障统一降级 `mode=rules_only`。
3. `server_stdio` 工具由 4 增至 6：新增 `scan_smart` / `rewrite_smart`，返回 `mode`、逐命中 `source` 与 `llm` 审计元数据；`engine.Hit` 加 `source`（默认 `rule`，向后兼容）。
4. 新增 `tests/test_llm.py`（20 项，`FakeBackend` 无 key 确定性测试）与语义待跑集 `evals/cases/semantic.jsonl`（6 条，规则层已确认漏检）；pytest 增至 52 项。规则数据仍为 v1.2。

## 不可破坏的契约
- `tests/run_baseline.py`、`python -m pytest -q`、`evals/run_evals.py` 必须始终全绿。
- `docs/TOOL_SCHEMA.md` 的入参/出参字段不得擅自变更；要变就升版本并同步接入文档。
- 改规则后先 `python scripts/export_rules.py` 规范化，再跑全部验证。

## P1 待办
- LLM 语义层已真实联调（中文）：融合/降级/改写/预算/缓存已落地，在线评测 40/40 见 `reports/LLM_EVAL.md`。归一化仍待增强：中文标点插字、emoji 替字映射、谐音/拼音、拆字还原（谐音/拆字归 LLM）；规模化红队（promptfoo/DeepTeam，多模型/跨语言）待补。
- 远程部署与计费：把 `server_http` 部署到公网、接 OAuth/多租户与网关计量（见 deploy/README.md）。
- 法条条款号/版本/URL 元数据深化（B6）。
