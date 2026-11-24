# rules/ —— 语言无关规则库（数据标准件 ②）

## 目录布局（M5 起插件化）

- **核心包 [`rules.v1.json`](./rules.v1.json)**：`scope=all` 的通用规则（广告法极限词 / 虚假误导 / 医疗功效 / 迷信 / 诱导）、平台导流规则，以及首个行业 `industry:jadeite`（翡翠）。核心包保持稳定，当前 **v1.5，14 条规则 / 16 条替换**（v1.5 仅在既有规则内追加英文同义违规词，条数不变）。
- **行业插件包 [`plugins/`](./plugins)`<name>.json`**：每个行业一个文件，只放核心包未覆盖的行业**增量**规则。当前内置：

  | 插件包 | 行业 | 版本 | 规则 / 替换 | 主要法规 |
  |---|---|---|---|---|
  | `plugins/food.json` | 食品 / 保健食品 | v1.0 | 3 / 8 | 广告法 17/18、食品安全法 73、广告审查办法 11 |
  | `plugins/cosmetics.json` | 化妆品 | v1.0 | 3 / 8 | 化妆品条例 37/43、广告审查标准 100、广告法 9/28 |

  聚合加载后全局 **20 条规则 / 31 条替换**（替换表按词去重：跨包共用词如“无副作用”只保留一条中性替换）。

- 所有 JSON 都是语言无关、机器可读的事实源，Python 与未来 TypeScript/Cloudflare 运行时共用同一份，由 `src/lcg/rules_store.py` 在启动时直接聚合加载，**禁止在运行时代码里另维护一套词库**。

## 核心包规则字段 schema（每条规则）

| 字段 | 含义 | 取值 |
|---|---|---|
| `scope` | 生效范围 | `all`（通用）/ `industry:<name>`（行业）/ `platform:<name>`（平台） |
| `category` | 违规分类 | 如 绝对化用语、医疗/功效宣称、站外导流 |
| `severity` | 严重度 | `high`（必拦）/ `medium`（需改）/ `low`（提示） |
| `law` | 法规/规则依据 | 如 《广告法》第9条、平台规则名 |
| `words` | 字面关键词 | 精确包含匹配 |
| `patterns` | 正则 | 变体、联系方式、数字写法、组合句式等 |
| `tip` | 整改建议 | 命中后给主播/文案的可执行建议 |

顶层另有 `replacements`（命中词 → 安全替代表达）与 `meta`（版本、格式、计数）。

## 行业插件包 schema

顶层结构与核心包一致（`meta` + `rules` + `replacements`），`meta` 额外要求：

| 字段 | 含义 |
|---|---|
| `package` | 包名，与文件名、`industry` 一致 |
| `format` | 固定 `lcg-plugin/1` |
| `industry` | 行业键，必须已存在于 `models.INDUSTRIES` |
| `version` | 本包版本，独立于核心包与软件包 |
| `sources[]` | 每项 `{law, article, url}`，列出本包法条来源；`url` 统一挂国家法律法规数据库入口 `https://flk.npc.gov.cn`，不编造深链 |

**硬约束**：插件包内每条规则的 `scope` 必须等于 `industry:<meta.industry>`，否则 `rules_store` 加载校验直接失败。

## 行业隔离与合规放行边界

- `detect(industry=...)` 只激活 `all` ＋ 该行业 ＋ 该平台的规则，行业包之间天然隔离、互不串扰。
- 行业包只放**增量**词与组合；核心包已覆盖的词（治疗、根治、消炎、100%、无效退款等）不要重复收录，避免同词跨类重复计数。
- 合规表述必须放行，规则层不得滥抓：
  - 保健食品：注册备案目录内的保健功能（如“增强免疫力”）＋ 法定声明“本品不能代替药物”；
  - 化妆品：清洁 / 保湿 / 补水 / 美容修饰等普通功效，祛斑美白 / 防晒 / 防脱发等需注册的特殊化妆品功效，以及“敏感肌 / 祛痘 / 修护屏障 / 提亮”等肤质与功效描述。
- 是否具备资质、备案功能范围、蓝帽 / 特证真伪等**条件性判断超出规则层能力**，交给 LLM 语义层与人工复核。

## 新增行业包流程

1. 用法律检索工具逐条核实法条条款号与原文（**禁止凭记忆编造条款号或深链**），`url` 统一挂 `https://flk.npc.gov.cn` 入口。
2. 新建 `plugins/<industry>.json`（`meta` ＋ 增量 `rules` ＋ `replacements`），规则 `scope` 全部用 `industry:<industry>`。
3. 在 `src/lcg/models.py` 的 `INDUSTRIES` 增加该行业键。
4. 在 `evals/cases/benign.jsonl`、`adversarial.jsonl` 增加该行业正反向用例（每条标 `industry`），并在 `tests/test_plugins.py` 增加正反向测试；**良性合规话术必须 clean**。
5. 依次跑 `python scripts/export_rules.py`（规范化）→ `--check`（守门）→ `pytest` → `evals/run_evals.py`，全绿后再同步主工程。

## 校验

- `python scripts/export_rules.py`：逐文件规范化并写回核心包与全部插件包。
- `python scripts/export_rules.py --check`：逐文件校验结构、计数、规范化是否与磁盘一致，并验证聚合视图可加载；CI 用它防止事实源漂移。

## 红线

- 规则与法规引用仅用于合规自查；规则可能滞后，大促 / 平台改版 / 新法施行前必须人工复核，不构成法律意见。
