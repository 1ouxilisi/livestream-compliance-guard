# DEMO_SCRIPT.md · 演示录屏分镜与口播脚本

> 配合 [`scripts/demo_walkthrough.py`](../scripts/demo_walkthrough.py) 使用：一条命令跑通规则层、行业插件、批量检测、改写闭环、LLM 融合/降级与性能快照，照着本分镜录制即可。
>
> **口径红线（对外演示必须遵守）**：本项目为**个人作品集 / demo**，不是付费客户案例；在线 LLM 结果随模型版本与账户余额波动，以 `reports/LLM_EVAL.md` 最新快照为准；性能数字为本机进程内相对值，不代表生产 SLA；工具仅作合规风险提示，不构成法律意见。

## 1. 成片规格建议

| 项 | 建议 |
|---|---|
| 时长 | 3.5–5 分钟（可按平台剪成 60s 短片 + 完整版） |
| 画幅 | 16:9 终端录制；字号调大，确保命中词与法条可读 |
| 语言 | 中文主稿；每镜附一句 English voiceover，供 Fiverr / Upwork 海外版复用 |
| 素材 | 终端 + 浏览器 README 页面；不出现 `.env`、API key、私域联系方式 |
| 复现 | 所有数字均可由仓库命令复现，见文末命令清单 |

## 2. 录制前准备

```bash
# 零依赖规则自测（确认环境正常）
python server.py --selftest

# 离线演示（不调用模型、不耗额度，秒出）—— 规则段优先用这条录
python scripts/demo_walkthrough.py --offline

# 在线演示（需 .env 配好 key 且有余额；第 7 节走真实融合，含网络延迟与 token 消耗）
python scripts/demo_walkthrough.py
```

- 关闭系统通知与无关弹窗；终端主题用高对比配色。
- 在线段录制前确认 `.env` 已配置 `LCG_MODEL_PRIMARY`；**不要在画面里露出 key**。
- 若只录规则能力，全程 `--offline` 即可；LLM 融合段可单独录制后剪辑拼接。

## 3. 分镜表

### 镜头 0 · 开场（0:00–0:20）
- **屏幕动作**：终端打开仓库根目录，切到浏览器展示 README 标题与 6 个 MCP 工具表。
- **口播（中）**：这是一个直播电商合规守卫 MCP，在话术出口或内容发布之前，拦截极限词、虚假宣传、升值承诺、医疗功效、迷信表述和站外导流，并给出法条依据与改写建议。
- **EN**：A compliance-guard MCP for live commerce. Before a script goes out, it catches absolute claims, false promises, investment guarantees, medical claims, superstition and off-platform diversion, with legal references and rewrite suggestions.

### 镜头 1 · 合规话术放行（0:20–0:50）
- **命令**：`python scripts/demo_walkthrough.py --offline`（对应第 1 节）。
- **预期画面**：食品、化妆品、带鉴定证书的翡翠三条合规话术判 `clean` 或仅 `low` 术语提示，**不误报**。
- **口播（中）**：先看正常话术——普通食品口感、化妆品保湿、配证书支持复检的翡翠，都被放行，或只对行业术语给低风险提示。
- **EN**：First, legitimate scripts pass: ordinary food descriptions, cosmetic moisturizing claims, and certified jadeite with re-inspection are released, or flagged only as low-risk terminology hints.

### 镜头 2 · 规则高危拦截（0:50–1:20）
- **预期画面**：第 2 节翡翠多重违规句，判 🔴 `high`，逐条列出命中类别、命中词、法条依据与处置建议。
- **口播（中）**：同一句话叠了绝对化用语、升值承诺、迷信功效和站外导流，规则逐条命中，每条都挂了对应法条和可执行的改写建议。
- **EN**：One sentence stacks absolute terms, investment promises, superstition and off-platform diversion. The rule core flags each hit with its legal basis and an actionable fix.

### 镜头 3 · 变体绕过识别（1:20–1:50）
- **预期画面**：第 3 节——全角 `ｖｘ：ａｂｃ１２３４５`、插空格“最 好”、emoji 阻断“微❤️ abc12345”，均被归一化后命中。
- **口播（中）**：两层归一化能识别全角字符、插空格、emoji 阻断等常见绕过写法，而正常英文词不会被误伤。
- **EN**：Two-layer normalization catches full-width characters, inserted spaces and emoji-obscured contact info, while normal English words stay untouched.

### 镜头 4 · 行业插件（1:50–2:15）
- **预期画面**：第 4 节——食品疾病治疗宣称、化妆品药妆/速效宣称，均判 🔴 `high`。
- **口播（中）**：食品和化妆品是可插拔的插件词库，核心规则包不变，新增一个行业只需加一份 JSON，不动引擎代码。
- **EN**：Food and cosmetics are pluggable lexicon packs. To add an industry you drop in one JSON file; the core engine stays untouched.

### 镜头 5 · 整场批量检测（2:15–2:40）
- **预期画面**：第 5 节——5 条主播话术时间线，3 条标记风险、14 处 high 命中，总体 `high`。
- **口播（中）**：除了单句检测，还支持整场直播逐句批量扫描，输出分段时间线和高风险计数，适合实时或回放风控。
- **EN**：Beyond single-sentence checks, it scans a whole livestream segment by segment and returns a timeline with high-risk counts, for both real-time and replay moderation.

### 镜头 6 · 改写 ＋ 复检闭环（2:40–3:05）
- **预期画面**：第 6 节——原文命中词 → 安全替换 → 改写后文案 → 复检 🟢 `clean`。
- **口播（中）**：命中词给出安全替代表达，改写后的句子会再次过规则复检，只有复检通过才采用；仍违规的候选会被拦下并标记人工复核。
- **EN**：Hits get safe replacements. The rewritten sentence is re-checked by the rules; it's adopted only if clean, otherwise rejected for human review.

### 镜头 7 · LLM 融合 ／ 自动降级（3:05–3:40）
- **命令**：在线模式 `python scripts/demo_walkthrough.py`（第 7 节）；若不想耗额度，录离线模式展示 `status=disabled` 的降级路径即可。
- **预期画面**：`mode=rules_plus_llm` 或 `rules_only`；展示 `llm.status`、`model`、`calls`、`total_tokens`；高危句在任何路径下都仍是 `high`。
- **口播（中）**：规则是不可被降低的硬底线，LLM 只补充谐音、拆字、近义暗示和自然整句改写；没有 key、超时、超预算或返回脏 JSON 时自动降级纯规则，服务不中断。token 用量会随结果透传，便于核算成本。
- **EN**：Rules are a hard floor the LLM can never lower. The model only adds homophone/split-char/implied-hint detection and natural rewriting. With no key, timeout, budget exhaustion or malformed JSON, it falls back to rules-only without breaking. Token usage is passed through for cost tracking.

### 镜头 8 · 性能与测试基线（3:40–4:00）
- **命令**：演示脚本第 8 节性能快照；再依次跑 `python evals/run_evals.py` 与 `python -m pytest -q`。
- **预期画面**：规则层本机约 1.9ms/句、P95 约 2.5ms、数百句/秒；规则评测 72/72；单测 140 项通过。
- **口播（中）**：规则层是零第三方依赖的纯本地判断，本机单句约两毫秒；离线评测 72 条全绿、高危检出 100%、干净误报 0%，单元测试 140 项通过。
- **EN**：The rule core runs locally with zero third-party dependencies, about two milliseconds per sentence on this machine. Offline evals pass 72/72 with 100% high-risk recall and zero clean false positives; 140 unit tests pass.

### 镜头 9 · 批量聚合与反馈闭环（4:00–4:15，离线）
- **命令**：演示脚本第 9 节（批量聚合 · 输入适配 · 反馈闭环 · 审计事件）；反馈写临时 JSONL、审计仅构造样例，不落业务文件。
- **预期画面**：第 9 节——异构片段（dict/纯文本）归一为检测契约；输出风险等级分布、命中类别计数、按主播的最高风险与 high 命中数、待整改清单；一条反馈写入本地 JSONL 并读回；展示一条可脱敏的审计事件样例。
- **口播（中）**：除了逐句检测，还能把整场结果聚合成风险分布、按主播分级并列出待整改清单；人工复核发现的误报、漏报可沉淀为本地反馈记录，作为规则迭代与评测扩充的输入；每次检测可留结构化审计痕迹，支持不记录原始话术的脱敏模式。
- **EN**: Beyond per-sentence checks, results aggregate into a risk distribution, per-speaker levels and a remediation list. False positives/negatives are logged locally to feed rule iteration, and each check leaves a redactable audit trail.

### 收尾（4:15–4:30）
- **屏幕动作**：回到 README，展示仓库地址与 Roadmap。
- **口播（中）**：项目开源在 GitHub，规则词库、评测集、基准报告和部署方式都在仓库里；在线规模化红队、更多行业插件和英文跨境规则在路线图上。
- **EN**：The project is open source on GitHub, with the rule lexicon, eval set, benchmarks and deployment docs in the repo. Scaled red-team testing, more industry packs and cross-border English rules are on the roadmap.

## 4. 剪辑与上架口径

- **标题/简介**：写清 “MCP · live-commerce compliance · China Advertising Law + platform rules · rule core + optional LLM layer”；附仓库链接与复现命令。
- **不要写**：付费客户案例、上线成交数据、具体客户名；性能说成生产 SLA；把规则提示表述成法律结论。
- **字幕**：关键级别词（high / medium / low / clean）、`mode`、`tokens` 建议上字幕，方便静音观看。
- **版本对齐**：成片引用的评测条数、测试项数、性能数字以仓库 `reports/BENCHMARK.md`、`reports/PERF.md` 与 `pytest` 实际输出为准，录完核对一遍。

## 5. 复现命令清单

```bash
python server.py --selftest                 # 规则自测
python scripts/demo_walkthrough.py --offline  # 离线演示（录屏主用）
python scripts/demo_walkthrough.py          # 在线演示（含 LLM 融合，需 key）
python scripts/demo_walkthrough.py --json   # 结构化 JSON 输出
python evals/run_evals.py                   # 规则层评测（BENCHMARK.md）
python scripts/bench_perf.py                # 性能与成本基准（PERF.md）
python -m pytest -q                         # 单元测试
```
