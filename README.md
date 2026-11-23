# livestream-compliance-guard · 直播电商合规守卫 MCP

> Real-time banned-word / absolute-term / false-claim detection for **live commerce** hosts, AI shopping agents and digital-human sellers — China Advertising Law + major platform rules, with built-in **jadeite** rules plus pluggable **food/health-food** and **cosmetics** lexicons on a shared language-neutral rule core.
> 直播话术、短视频带货文案、商品标题、客服回复的**实时合规检测**：广告法极限词、虚假宣传、升值承诺、医疗功效、迷信、站外导流；核心包内置**翡翠**行业规则，**食品/保健食品、化妆品**为可插拔插件词库，另含抖音/快手/视频号/淘宝直播平台规则。

[![CI](https://github.com/1ouxilisi/livestream-compliance-guard/actions/workflows/ci.yml/badge.svg)](https://github.com/1ouxilisi/livestream-compliance-guard/actions/workflows/ci.yml) [![MCP](https://img.shields.io/badge/MCP-ready-blue)]() [![license](https://img.shields.io/badge/license-MIT-green)]() [![version](https://img.shields.io/badge/version-v0.7.2-orange)]()

> 仓库地址：`github.com/1ouxilisi/livestream-compliance-guard`；CI 徽章在仓库公开并由 GitHub Actions 跑通后对外显示。

## Why（解决什么痛）
直播带货因一句“最/第一/保真/升值/加微信/养生辟邪”就可能被**警告、断播、扣分、罚款、清退**；数字人/AI 主播 7×24 小时说话，风险更高。本工具把合规检查做成一个可被任意 agent（Claude / Cursor / Dify / 数字人后台）调用的 **MCP 工具**，在话出口/内容发布**之前**拦截并给出改写建议。

- **Narrow, high-frequency, verifiable output, buyer already exists** — the exact shape that monetizes on MCP marketplaces.
- Deterministic, auditable rule core（可解释、可复核）＋ optional LLM layer for homophones/emoji variants and full-sentence rewrite.

## Tools（6 个工具）
| Tool | 作用 |
|---|---|
| `scan_text` | 单段话术/文案**纯规则**检测，返回风险等级+命中词+法规依据+建议（确定性） |
| `scan_livestream` | 整场直播逐句批量检测，输出时间线与高风险计数（实时/回放风控） |
| `compliance_rules` | 返回某行业×平台当前生效词库（培训/展示/审计） |
| `safe_rewrite` | 命中词的安全替代表达（纯规则机械替换＋复检） |
| `scan_smart` | **规则硬底线＋LLM 语义融合**：识别谐音/拆字/emoji/近义暗示等规避表达；无 key 自动降级纯规则，返回 `mode` 与逐命中 `source` |
| `rewrite_smart` | 优先 **LLM 自然整句改写**并规则复检，复检不过或模型不可用则回退规则替换 |

`risk_level`: **high（必拦）/ medium（需改）/ low（提示）/ clean**。

## Quick start
```bash
# 1) 不装依赖，先自测规则（规则核心 src/lcg 零第三方依赖）
python server.py --selftest

# 1.5) 离线演示走查（录屏 / 作品集用；--offline 不调用模型、不耗额度）
python scripts/demo_walkthrough.py --offline

# 2) 规则校验 + 行为基线 + 单元测试 + 评测
python scripts/export_rules.py --check
python tests/run_baseline.py
python -m pip install -r requirements-dev.txt
python -m pytest -q
python evals/run_evals.py

# 2.5) 可选：LLM 语义层在线评测（先复制 .env.example 为 .env，填 SILICONFLOW_API_KEY 与 LCG_MODEL_PRIMARY）
python scripts/run_llm_evals.py     # 在线快照：语义召回/红队阻断/LLM零误报（需 key 且账户有余额，非 CI；结果随模型版本波动，以 reports/LLM_EVAL.md 最新快照为准）

# 3) 作为标准 MCP Server（stdio）
pip install -r requirements.txt
python server.py

# 4) 作为远程 MCP Server（Streamable HTTP，端点 /mcp，探活 /healthz）
pip install ".[http]"
LCG_BEARER_TOKEN=sk-xxx python -m lcg.server_http   # 不设 token 则本机开放
```
MCP 客户端配置（示例）：
```json
{
  "mcpServers": {
    "livestream-compliance-guard": {
      "command": "python",
      "args": ["/path/to/server.py"]
    }
  }
}
```

## 架构与规则源
规则引擎位于 `src/lcg/`：`models`（常量/入参校验/等长归一化/序数消歧）、`rules_store`（规则加载）、`engine`（检测/聚合/改写纯逻辑，规则硬底线）、`llm`（OpenAI 兼容语义客户端，可选依赖、故障可降级）、`pipeline`（规则＋LLM 硬底线融合 `analyze`/`smart_rewrite`）、`ingest`（上游 ASR/字幕/表格异构片段归一为检测契约，不做 ASR/OCR）、`aggregator`（整场结果的风险分布、类别/主播聚合与待整改清单）、`feedback`（误报/漏报/存疑的本地 JSONL 记录与 CSV 导出，可选启用）、`audit`（可选本地 JSONL 审计留痕，默认关闭、可脱敏）、`server_stdio`（FastMCP stdio 薄封装）、`server_http`（Streamable HTTP + healthz + 可选 Bearer；工具注册集中在 `create_mcp()` 工厂，stdio 用单例、HTTP 每次独立实例）。规则事实源为**核心包 `rules/rules.v1.json` ＋ 行业插件包 `rules/plugins/*.json`**（核心 v1.4：14 规则/16 替换，其中 3 条翡翠规则以 `industry:jadeite` scope 隔离内置在核心包；食品、化妆品为外部插件包，各 3 规则/8 替换，聚合 20 规则/31 替换），由 `rules_store` 启动时聚合加载、逐包校验、行业隔离，Python 与未来 TS/Cloudflare 运行时共用同一份 JSON；根 `server.py` 只是保持向后兼容的薄 shim。新增/修改规则与用例的流程见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## Coverage（核心规则 v1.4 ＋ 行业插件 v1.0）
- 《广告法》第9条 绝对化用语；第17条 医疗/功效；第25/28条 投资承诺与虚假宣传；《反不正当竞争法》；价格欺诈。
- 平台：抖音、快手、视频号小店、淘宝直播（站外导流、私下交易、刷单、好评返现、拍A发B）。
- 行业（按 `industry` 选择）：翡翠/玉石 `jadeite`（内置核心包，scope 隔离：保真、A货/证书复检、赌涨捡漏、种水夸饰、养生开光）；食品/保健食品 `food`、化妆品 `cosmetics`（外部插件包，见 `rules/plugins/`：疾病治疗宣称、功效安全性断言、医疗代言与健康恐惧；药妆/医疗作用、速效与安全性断言、贬低同类）；其他行业用 `general`。合规表述刻意放行：保健食品备案目录内功能＋“本品不能代替药物”、化妆品普通功效与祛斑美白/防晒等注册特证功效、“敏感肌/祛痘/修护屏障/提亮”等肤质妆效。
- 引擎能力：两层归一化——**等长层**（全角转半角、英文小写、常用繁→简，识别 `１００％`、全角联系方式、`全網第一` 等绕过）与**紧凑层**（剔除空格/中点/emoji 阻断，拦“最 好”“NO·1”“微❤️abc12345”，保留中文标点不跨句合并）；“第一”序数消歧（第一步/第一款放行，销量第一/第一名仍 high）；导流正则要求词首信号＋号码含数字（英文 `voucher` 等正常词不误报）；命中词替换并对改写结果复检（B7 闭环，紧凑命中也能映射替换）。**v0.3.0 起叠加 LLM 语义层**：规则是不可被降低的硬底线，LLM 只补充谐音/拆字/暗示命中并做自然整句改写，无 key / 超时 / 超预算 / 脏返回时自动降级 `mode=rules_only`。规则层评测 72 条 100% 通过（高危检出 100%、干净误报 0%；良性 30、对抗 42，含食品/化妆品良性防误报与行业对抗召回）。性能基准见 [`reports/PERF.md`](reports/PERF.md)（规则层单句平均约 1.9ms、P95 约 2.7ms、约 520 句/秒，本机测量仅供相对比较）。**v0.6.0 起 LLM 语义层已对接硅基流动 OpenAI 兼容接口**（主力 Qwen/Qwen3-14B、兜底 DeepSeek-V3，检测 prompt detect-v3）：历史联调快照在线评测 **24/24**（语义召回 3/3、红队阻断 6/6、LLM 零误报 15/15）；在线结果依赖账户余额、随模型版本波动，**以 [`reports/LLM_EVAL.md`](reports/LLM_EVAL.md) 最新快照为准**，余额不足 / 无 key 时自动降级纯规则；LLM 调用采集并透传 token usage（输入/输出/总 token，可按配置单价估算成本）；安全口径见 [`reports/SECURITY.md`](reports/SECURITY.md)；pytest 123 项全绿（含两层归一化、行业插件聚合与隔离、语义融合与六类降级、token usage 采集透传、输入适配、整场聚合、反馈闭环、审计留痕、stdio/HTTP 协议握手与 Bearer 鉴权）。

## 商业支持 / Commercial support
- 开源核心可自由自托管；定制词库、行业插件、私有化部署等承接仅通过 Fiverr / Upwork 等第三方外包平台站内沟通与交易，不在站外私下接洽或转介绍。
- 相关文档：[合规依据对照表](docs/COMPLIANCE_MAPPING.md) · [承接范围与能力边界](docs/SCOPE_BOUNDARY.md) · [部署与平台化演进](docs/DEPLOYMENT.md) · [MCP 分发与上架说明](docs/MCP_MARKETPLACE.md) · [演示录屏脚本](docs/DEMO_SCRIPT.md)

## Roadmap
- [x] LLM 层真实联调（中文）：谐音/暗示召回 ＋ 注入/越狱抗性 ＋ 整句合规改写，已随 v0.6.0 上线（历史快照 24/24，最新结果见 `reports/LLM_EVAL.md`）；英文与多模型规模化红队（promptfoo/DeepTeam）仍在 P1。
- [ ] ASR 实时接入：直播语音转写→逐句实时告警。
- [x] 更多行业（插件化）：食品/保健食品、化妆品已随 v0.5.0 上线（`rules/plugins/`）。
- [ ] 更多行业：医疗器械、教育培训、金融理财、酒水（医疗/金融涉资质与“有无资质”判断，法条逐条核实后再做）。
- [ ] 合规周报：命中热力图 + 主播风险评分 + 整改跟踪。
- [ ] English / cross-border version（TikTok Shop / Amazon Live 合规）。

## Disclaimer
本项目仅提供**合规风险提示与技术辅助**，不构成法律意见；规则可能滞后，请以监管机关与各平台最新规则为准，重要场景请咨询法务。使用者对其发布内容负责。

## License
MIT（规则词库与法规引用仅供学习与合规自查）。
