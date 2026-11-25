# 接入你自己的行业词表（5 分钟，不用改代码）

> 面向两类人：想把自家平台的违禁词表塞进来的客户；接手定制词库单子的自己。
> 规则层只有 20 条不是上限——核心 14 条通用 + 行业增量全走 `rules/plugins/*.json`。
> v0.10 起，落一个 JSON 就生效；以前要在 `models.INDUSTRIES` 和 MCP 工具签名里注册行业，现在不用了。

## 一、三条命令

```bash
# 1) 从词表直接生成插件包（词后加 @low/@medium/@high 可逐词定级，默认 high）
python scripts/new_plugin.py --industry skincare --name 护肤品 \
    --words "七天美白,永久脱毛@medium,医美级"

# 2) CI 同款守门：结构、计数、规范化逐字比对
python scripts/export_rules.py --check

# 3) 用一句真实话术验证命中
python -c "from lcg import engine;print(engine.detect('这款面霜七天美白，效果立竿见影。','skincare','douyin')['risk_level'])"
```

真实回显（本机 v0.10 跑出来的，不是示意）：

```text
[OK] 已写入 rules\plugins\skincare.json（3 条规则 / 3 条替换）
[OK] 聚合：核心 14 + 插件 3 个 → 全局 22 规则 / 33 替换
[OK] 自检命中：industry=skincare 探针句 → high（1 条）
```

`--dry-run` 只打印 JSON 不写盘，给客户看结构时用它；`--force` 覆盖已存在的同名包；`--list` 看当前加载了哪些包、哪些还是 `_` 前缀模板。

## 二、生成出来是什么

```json
{
  "meta": {
    "package": "skincare",
    "format": "lcg-plugin/1",
    "language": "zh-CN",
    "version": "v1.0",
    "industry": "skincare",
    "rule_count": 3,
    "replacement_count": 3,
    "note": "护肤品行业插件包（new_plugin.py 生成）……",
    "sources": [{"law": "《广告法》第4条、第28条（上线前须逐条核实）", "article": "", "url": "https://flk.npc.gov.cn"}]
  },
  "rules": [
    {
      "scope": "industry:skincare",
      "category": "护肤品-未举证功效宣称",
      "severity": "high",
      "law": "《广告法》第4条、第28条（上线前须逐条核实）",
      "words": ["七天美白"],
      "patterns": [],
      "patterns_compact": [],
      "tip": "命中「七天美白」属未举证的绝对化/功效宣称……"
    }
  ],
  "replacements": {"七天美白": "（改为客观、可举证的表述）"}
}
```

一个词一条规则：命中归因清楚，`severity` 可以逐词不同，改写建议也逐词可改。

## 三、四个字段怎么分工

| 字段 | 放什么 | 例子 |
|---|---|---|
| `words` | 精确词，逐字命中 | `最好`、`国家级`、`加微信` |
| `patterns` | 正则，同一句内字形变化 | `最\s*好`、`第\s*一\s*名` |
| `patterns_compact` | 正则，跨标点/插字符/emoji 变体 | `微.{0,3}信`、`最[/\s]好` |
| `replacements` | 命中后给的安全替代表达 | `最好 → 较好` |

先用 `words` 堆最确定的，`patterns` 只留给确有变体的词。**不要**把核心包已经覆盖的词（治疗、根治、消炎、100%、无效退款）再抄一遍，会造成同词跨类重复计数。

## 四、四个必踩的坑

1. **`scope` 必须等于 `industry:<industry>`**，否则 `rules_store` 加载时直接 `ValueError`，整个服务起不来。
2. **`meta.rule_count` / `replacement_count` 必须等于实际条数**——`export_rules.py` 会自动重算，手工改 JSON 后记得跑一次。
3. **文件名不能以下划线开头**（`_medical.json` 这类是模板/工作底稿，刻意不加载）。
4. **新行业要重启进程**：行业集合在 `models.registered_industries()` 里缓存了一次；`new_plugin.py` 写完已自动清缓存，但**已经跑着的 MCP 服务**要重启才会认新包。

## 五、强监管行业先别急着上

医疗、医疗器械、金融、教培、酒水这类，注册备案范围、资质真伪、适应症口径都超出规则层能力。正确做法是：先建一个 `_<industry>.json` 工作底稿，`rules: []`、`meta.status: "placeholder"`、`meta.pending_legal_review: true`，把待核方向写进 `risk_categories` / `candidate_sources` / `review_checklist`，**不要回填可执行判罚词**。法务复核、法条逐条可溯源之后再去掉下划线转正。

## 六、交付口径（报价用）

- 普通行业 20–50 词，纯词表：约 2 小时；
- 加变体正则 + 该行业良性防误报用例 + 评测：约半天；
- 对外只说「风险提示与改写建议」，**不承诺过审、不承诺固定准确率、不出具法律意见**；
- 报价参照：半天 800、一周试单 4000、项目制 40/40/20 里程碑。

## 七、交付前自检

- [ ] `python scripts/export_rules.py --check` 全绿
- [ ] `python -m pytest -q` 全绿
- [ ] 至少一条命中用例 + 一条同行业良性话术仍然 `clean`（误报比漏报更容易丢客户）
- [ ] `meta.sources` 每条都能点到原文，条款号没有一个是凭记忆写的
- [ ] 客户那份词表里，同义词、错别字、谐音是否已明确「这层不管，交 LLM 层」
