# Tool I/O Schema · 直播电商合规守卫 MCP（软件 v0.9.0 / 核心规则 v1.4 ＋ 行业插件 v1.0）

传输：stdio（`python server.py`）或 Streamable HTTP（`python -m lcg.server_http`，MCP 端点 `/mcp`、健康检查 `/healthz`、可选 `Authorization: Bearer <LCG_BEARER_TOKEN>`，详见 `examples/mcp-client.http.md`）。两种传输暴露同一组 6 个工具：4 个纯规则确定性工具（scan_text / scan_livestream / compliance_rules / safe_rewrite）与 2 个规则＋LLM 融合工具（scan_smart / rewrite_smart）。

所有工具共用入参：
- `industry`：`jadeite`（翡翠/玉石，旧四工具默认）｜ `general`（通用行业，scan_smart 等新工具默认）｜ `food`（食品/保健食品）｜ `cosmetics`（化妆品）。行业规则以插件包形式置于 `rules/plugins/`，按行业隔离加载。
- `platform`：`douyin`（默认）｜ `kuaishou`｜ `shipinhao`（视频号）｜ `taobao`
- 风险等级 `risk_level`：`high`（必拦）｜ `medium`（需改）｜ `low`（提示）｜ `clean`
- 入参校验：`industry`/`platform` 取非法值时抛 `ValueError`，经 MCP 返回工具调用错误（`isError=true`），不会静默落到默认词库。
- 输入归一化（规则层，两层）：①**等长层** `normalize_text`：全角字母/数字/符号转半角、英文小写、常用繁体一对一转简体（如 `１００％`→`100%`、`ｖｘ：ａｂｃ１２３`→`vx:abc123`、`全網第一`→`全网第一`），1→1 不增删字符，故 `Hit.index` 与 `Hit.match` 始终对应原文位置与原文字面；②**紧凑层** `normalize_compact`（仅补漏）：在等长结果上剔除空格 / 零宽 / emoji / 插入装饰符，拦“最 好”“NO·1”“微❤️abc12345”等阻断变体，经紧凑下标映射无损还原原文区间；刻意保留中文标点与句子边界、不跨句合并。谐音、拆字、emoji 替字、近义暗示等仍需上下文判断的变体归 LLM 层。
- “第一”序数消歧（规则层）：表达次序时（第一步、第一款、第一期、第一件、第一产业、第一人称等）不判排名绝对化；表达排名/榜首时（销量第一、行业第一、全国第一、第一名等）仍判 high。

命中对象 `Hit`：
```json
{ "category": "绝对化用语", "severity": "high", "law": "《广告法》第9条",
  "match": "100%", "index": 12, "source": "rule",
  "suggestion": "删除绝对化表述，改为可举证的客观描述。" }
```
- `Hit.source`：`rule`＝规则硬底线命中；`llm`＝LLM 语义层补充命中（仅融合工具可能出现；LLM 无法精确定位时 `index=-1`、`match` 取其描述片段）。

## 1. scan_text(text, industry, platform)
单段话术/商品文案/客服回复检测。
```json
// ->
{ "risk_level": "high", "clean": false, "count": 7, "hits": [ Hit ],
  "industry": "jadeite", "platform": "douyin",
  "disclaimer": "仅为合规风险提示，不构成法律意见，以监管机关与平台最新规则为准。" }
```

## 2. scan_livestream(transcript, industry, platform)
整场直播逐句批量检测与聚合。`transcript = [{ "seq": 0, "speaker": "主播", "text": "..." }]`（按时间序）。
```json
// ->
{ "overall_risk": "high", "segments": 20, "flagged_segments": 6, "high_risk_hits": 9,
  "results": [ { "seq": 0, "speaker": "主播", "text": "...", "risk_level": "high", "hits": [Hit] } ] }
```

## 3. compliance_rules(industry, platform)
返回当前生效词库，用于展示、培训与审计。
```json
// ->
{ "industry": "jadeite", "platform": "douyin",
  "rules": [ { "category": "...", "severity": "high", "law": "...",
               "words": ["..."], "patterns": ["..."] } ] }
```

## 4. safe_rewrite(text, industry, platform)
命中词的安全替代表达；LLM 增强模式可输出整句合规话术。
```json
// ->
{ "original": "这是最好的，保真", "risk_level": "high",
  "replacements": [ { "from": "最好", "to": "比较受欢迎 / 本店热销" },
                    { "from": "保真", "to": "配鉴定证书、支持复检" } ],
  "rewritten": "按命中区间替换拼回的改写全文（规则层为机械替换，LLM 层可更自然）",
  "rewritten_risk": "clean", "rewritten_clean": true,
  "note": "规则替换为参考；改写全文已做规则复检（B7 闭环），正式使用前仍建议人工复核，完整话术可在 LLM 增强模式下生成。" }
```

## 5. scan_smart(text, industry, platform, use_llm=true)
规则硬底线 ＋ LLM 语义融合检测：在规则结果之外，由 LLM 识别谐音、拆字、空格/emoji 阻断、近义暗示等规则层拦不住的表达。规则永远先跑且**不可被 LLM 降低**（LLM 判 clean，规则判 high 依然 high）；LLM 只补充命中，同区间且不更严重的重复判断被去重，更严重的判断保留。未配置 key、未装 SDK、超时、超预算或模型返回脏 JSON 时自动回退纯规则。
```json
// ->（成功融合）
{ "risk_level": "high", "clean": false, "count": 3, "hits": [ Hit(rule…), Hit(llm…) ],
  "industry": "general", "platform": "douyin", "mode": "rules_plus_llm",
  "llm": { "status": "ok", "model": "…", "prompt_version": "detect-v4",
           "rewrite_prompt_version": "rewrite-v1", "cached": false, "calls": 1, "error": "",
           "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0 },
  "disclaimer": "…" }
// ->（降级，结果与 scan_text 一致）
{ "…": "…", "mode": "rules_only",
  "llm": { "status": "no_key|no_model|disabled|budget|error|parse_error", "error": "…" } }
```
`llm.status` 取值：`ok`（已融合）、`disabled`（use_llm=false 或开关关）、`no_key`、`no_model`、`budget`（超 `LCG_LLM_MAX_CALLS`）、`error`（网络/超时/鉴权，已尝试主备）、`parse_error`（模型返回无法解析）。

## 6. rewrite_smart(text, industry, platform, use_llm=true)
优先用 LLM 生成保留卖点的自然合规话术，并对改写结果做规则复检；复检 clean 才采用，否则保留规则机械替换版，把模型候选放入 `llm_candidate` 并置 `needs_human_review=true`。原文无风险时不调用模型（`llm.status=not_needed`，省预算）；LLM 不可用时回退 `safe_rewrite` 的规则替换结果。
```json
// ->
{ "original": "…", "risk_level": "high", "replacements": [ … ],
  "rewritten": "最终采用的合规话术", "rewritten_risk": "clean", "rewritten_clean": true,
  "rewrite_mode": "rules_plus_llm | rules_only | llm_rejected_needs_review",
  "needs_human_review": false,
  "llm_candidate": "仅当 LLM 改写复检不通过时出现", "llm": { "…同 scan_smart…" } }
```

## 语义与免责
- 规则引擎（`src/lcg/engine`）确定性、可解释、可复核，以 `rules/rules.v1.json` 为唯一事实源，是不可绕过的硬底线；`lcg.pipeline` 叠加 `lcg.llm` 语义层处理谐音/拆字/emoji/暗示变体与自然整句改写，LLM 只能补充、不能降低规则结论，且任何故障都回退纯规则。
- 词库需版本化，平台规则频繁变化，大促前应重新同步。
- 仅为风险提示，最终责任在商家，不构成法律意见。
