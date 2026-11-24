# GIG 上架物料清单（Assets & Deliverables）

> 配套 [`GIG_LISTING.md`](GIG_LISTING.md)（海外 Fiverr / Upwork）与 [`REMOTE_LISTING.md`](REMOTE_LISTING.md)（国内远程渠道）。
> 本文件沉淀**可公开**的定稿标题、素材清单与三档交付范围；**定价金额不写进本仓**（私有归档，发布人自行填写）。
> 所有评测数字以 `reports/` 最新快照为准；样例数据均为虚构示例，不代表真实客户或场次。

## 1. 标题定稿

### 1.1 海外（Fiverr / Upwork，英文主标题）

**主标题（PRIMARY）**
> `Custom content moderation MCP: banned words, prohibited claims and safe rewrite for e-commerce scripts`

**备选标题（按关键词 A/B 用）**
1. `Policy compliance filter for scripts, product copy and replies with safe rewrite`
2. `Deterministic rule-based content safety checker integrated as an MCP tool for your agent`
3. `Pluggable rule lexicon + optional LLM review for live-commerce and e-commerce copy`

> 关键词覆盖：content moderation、compliance、banned words / prohibited claims、MCP、e-commerce / live-commerce script、safe rewrite、rule-based + optional LLM。

### 1.2 国内远程渠道（中文主标题）

**主标题（PRIMARY）**
> `直播话术合规筛查与改写：极限词 / 虚假宣传 / 升值承诺 / 医疗功效 / 站外导流检测`

**一句话简介（中英定稿，复用至 Gig 简介首段）**

- 中：发布前筛查直播口播、短视频文案、商品标题与客服回复，返回风险等级、命中词、依据提示与合规改写建议；确定性规则核心可解释、零第三方依赖，可选 LLM 语义层补充谐音 / 拆字 / emoji 规避，无 key 时自动降级纯规则，规则硬底线不被模型降低。
- EN: A deterministic, auditable rule core with an optional LLM layer that checks scripts, short-video copy, product titles and replies before publication — returning a risk level, matched terms, policy basis and a compliant rewrite. Degrades to rules-only when no model key is available; the rule floor can never be lowered by the LLM. The lexicon is pluggable and adaptable to your industry, platform or policy wording.

## 2. 素材清单（截图 / 录屏 / 凭证）

> 录制与截图前关闭系统通知与无关弹窗；画面不得出现 `.env`、API key、私域联系方式。样例产物在 `samples/`，由脚本离线生成、可复现。

### 2.1 静态截图（Gig 主图 / 附图）

| # | 素材 | 来源 / 命令 | 画面要点 | 用途 |
|---|---|---|---|---|
| S1 | 能力总览 | 浏览器打开 `README.md`，截取 6 个 MCP 工具表与覆盖平台/行业段 | 工具名、四级风险、4 平台 4 行业 | Gig 首图 / 能力概览 |
| S2 | 整场合规周报 | 浏览器打开 `samples/batch_report.html`（`python scripts/export_report.py` 重新生成） | 总体风险、风险分布、按主播分级、待整改清单、分段明细 | 主附图：批量检测成品形态 |
| S3 | 批量明细 CSV | 表格软件打开 `samples/batch_report.csv` | 序号 / 主播 / 话术 / 风险级别 / 命中类别 | 附图：逐条判定明细 |
| S4 | 改写前后对照 | 表格软件打开 `samples/rewrite_before_after.csv` | 原文 → 替换映射 → 改写后全文 → 复检 clean | 附图：改写闭环 |
| S5 | 反馈导出样例 | 表格软件打开 `samples/feedback_example.csv` | 误报 / 漏报 / 存疑三类反馈记录 | 附图：反馈闭环（B 档能力，如实标注本地留痕） |
| S6 | 信任凭证 | `reports/BENCHMARK.md`、`reports/LLM_EVAL.md`、`reports/MODEL_CROSSCHECK.md`、`reports/PERF.md` 关键段截图 | 95/95、73/73、双模型交叉、性能基准 | 附图：可复现评测背书 |

### 2.2 录屏（演示视频，3.5–5 分钟；可剪 60s 短片）

分镜与口播见 [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md)，离线主录命令：

```bash
python scripts/demo_walkthrough.py --offline   # 规则段主用，不耗模型额度
python scripts/demo_walkthrough.py --json      # 需要结构化输出画面时
```

| 镜头 | 内容 | 对应产物 |
|---|---|---|
| 0 | 开场：仓库 README 与 6 工具 | S1 |
| 1 | 合规话术放行（食品 / 化妆品 / 带证书翡翠） | 不误报证据 |
| 2 | 规则高危拦截（叠加绝对化 / 升值 / 迷信 / 导流） | 命中类别 + 依据 + 建议 |
| 3 | 变体绕过识别（全角 / 插空格 / emoji 阻断） | 两层归一化 |
| 4 | 行业插件（食品 / 化妆品可插拔 JSON） | 插件化词库 |
| 5 | 整场批量扫描时间线与 high 计数 | S2 / S3 |
| 6 | 改写 + 复检闭环（复检不 clean 不采用） | S4 |
| 7 | LLM 融合 / 自动降级（可选，需 key；可只录 `rules_only` 降级路径） | mode / status / tokens |
| 8 | 性能与测试基线（规则层本机毫秒级，详见 PERF 快照；95/95；230 单测） | S6 |
| 9 | 批量聚合 + 反馈闭环 + 可脱敏审计样例 | S5 |

> LLM 融合段为可选：若不想耗额度，录离线降级路径即可；在线结果随模型版本与余额波动，视频与简介中须注明。

### 2.3 截图取景细则（以 `samples/batch_report.html` 为例）

页面由 `scripts/export_report.py` 离线生成，截图前先浏览器打开核对数字与 `reports/` 一致。

**S2 主图（首屏全景，一屏内）**
- 必入镜：标题「直播合规周报（演示样例）」、meta 行（行业 / 平台 / 离线生成 / 示例数据）、4 张汇总卡片（总体风险 high、分段数 5、风险分段 3、high 命中 14）、风险分布表与命中类别表。
- 取景要点：卡片数字与级别徽章清晰可读；不要裁掉 meta 行的「示例数据」标注。

**S2-b 附图（主播分级 + 待整改）**
- 必入镜：「按主播分级」表（A low / B high·14 / C clean）与「待整改清单」3 条；体现可定位到人、可逐条整改。

**S2-c 附图（分段明细）**
- 必入镜：「分段明细」表的命中列（命中类别·命中词）；高危行命中词完整可见，clean 行留空命中列可作为不误报对照。

**口径红线（所有截图）**
- 保留页脚免责声明「仅为合规风险提示与改写建议，不构成法律意见」；不得裁去或替换。
- 不出现真实品牌、主播名、客户名；画面不露出 `.env`、API key、终端私域联系方式。
- 浏览器地址栏只显示本地文件路径或仓库 README，不贴带 token 的链接。

## 3. 三档交付范围对照（结构 only — 价格另议）

> 档位价格由发布人按平台行情自行设定，本表不含金额。范围严格对应 A 档已闭环能力；B 档骨架须带限定；C 档一律不承诺。

| 维度 | Basic · 排查 | Standard · 定制 | Premium · 接入 |
|---|---|---|---|
| 输入 | 买家提供一批话术 / 文案 / 标题 / 回复（文本） | 同 Basic，指定单一行业 × 平台 | 同 Standard，对接现有系统 / 流程 |
| 规则检测 | ✅ 单条 + 批量风险分级（high / medium / low / clean）、命中词与类别、依据提示 | ✅ 同 Basic | ✅ 同 Basic |
| 改写建议 | ✅ 命中词安全替换 + 复检对照表 | ✅ 同 Basic | ✅ 同 Basic |
| 交付报告 | ✅ 风险报告（HTML / CSV）、命中点 + 依据、改写前后 CSV、待复核清单 | ✅ 同 Basic | ✅ 同 Basic |
| 词库定制 | ❌ 沿用内置通用 / 翡翠 / 食品 / 化妆品词库 | ✅ 单一行业 / 平台词库调整，以可插拔插件 JSON 交付，不改核心引擎 | ✅ 同 Standard |
| 批量复核 | 按买家稿件批量出报告 | ✅ 一批稿件批量复核 + 待整改清单 | ✅ 同 Standard |
| MCP 服务接入 | ❌ | ❌ | ✅ stdio / Streamable HTTP 服务配置，可选 LLM 层接线 |
| 工程产物 | 报告文件 | 报告 + 插件词库 | 报告 + 插件词库 + 可运行服务配置、README / 运行说明、测试与评测用例 |
| 反馈 / 审计留痕 | 报告内标注待复核项 | 本地反馈记录样例（CSV / JSONL） | 本地反馈 + 可脱敏审计事件样例；内存 / 可选本机 SQLite 骨架 |

### 3.1 各档明确不含（C 档，写入 Gig 边界）

- 不提供法律意见、律师合规意见书或平台审核结论；不承诺“包过审 / 平台认可 / 法律背书”。
- 不核验营业执照、备案、许可证、证书真伪；不担保商品真实性、质量与来源。
- 不做语音（ASR）、图像文字（OCR）、视频、弹幕、评论区原始内容识别；只处理已转写文本。
- 不含生产服务器、域名、TLS、支付结算、SLA、多实例扩展与灾备；由部署方在目标环境落地。
- 医疗、金融理财、保险、教培、酒水、跨境 / 进口商品、英文及 TikTok Shop / Amazon Live 规则仅有空占位骨架，不提供实词库定制。

### 3.2 B 档能力表述限定（若在 Gig 提及，必须带限定词）

- 身份 / Key 映射、角色门禁、配额计量、审计 / 反馈留痕、缓存、输入源适配：均为**单进程本地骨架 / 协议预留**，可选本机 SQLite 持久化；无注册登录、密码哈希、Key 签发轮换、外置数据库、Redis 分布式缓存与跨进程共享，不是生产级多租户账号体系。
- LLM 语义层为**可选依赖**：需买家提供模型 key 与余额；在线快照随模型版本波动，非确定性门禁。

## 4. 发布前最终核对

- [ ] 标题 / 简介无占位符；三档交付物与实际能交付的一致。
- [ ] 复跑离线回归：`ruff check`、`scripts/export_rules.py --check`、`pytest -q`、`evals/run_evals.py` 全绿，附件数字与 `reports/` 一致。
- [ ] 在线快照（`reports/LLM_EVAL.md`、`reports/MODEL_CROSSCHECK.md`）为最新，或明确只引用离线规则层成绩。
- [ ] 仓库公开匿名可访问；`.env`、密钥、定价台账与内部文档不可见。
- [ ] 边界条款（3.1 / 3.2）在 Gig 描述中可见；无“包过审 / 法律背书 / 资质保真 / 识别语音图片”字样。
- [ ] 沟通、报价、收款留在 Fiverr / Upwork 等第三方平台站内；不站外私信、不拉群、不转介绍、不接直客。
- [ ] 样例截图 / 视频标注为虚构示例数据；性能数字注明本机相对测量，不表述为生产 SLA。
