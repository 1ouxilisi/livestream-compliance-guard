# evals/ —— 评测集与红队（数据/信任标准件 ③ 的机床）

## 用例文件（JSONL，每行一条）
| 文件 | 用途 | 裁决层 |
|---|---|---|
| `cases/benign.jsonl` | 干净/合规话术，测**误报** | 规则层 |
| `cases/adversarial.jsonl` | 违规话术，测**检出** | 规则层 |
| `cases/redteam.jsonl` | 注入/拆字/emoji/越狱/冒充权威/指令覆盖，含中文与英文样例 | **LLM 层**（DeepTeam/PyRIT，P1） |
| `cases/semantic.jsonl` | 谐音/暗示，规则层设计内漏检，含中文与英文样例 | **LLM 语义层** |

> 语言口径：核心规则词表为 `zh-CN`，英文/跨语言违规词（best、number one、cure、guaranteed、
> WhatsApp 等）**尚未收录进规则层**；英文样例在规则层基线记为设计内缺口，交 LLM 语义 / 红队层裁决。
> 规则层不硬塞英文同义词表，避免误报；英文词表属待办，需逐条对齐法规与平台规则后再补。

### 字段
- `id`、`text`、`industry`、`platform`
- `expect_risk`：`clean/low/medium/high`
  - benign：实际严重度 **不允许高于** 期望（否则算误报）
  - adversarial：实际严重度 **不允许低于** 期望（否则算漏报）
- `expect_any`（可选）：这些违规点至少应有一个出现在命中结果里
- `layer=llm`、`attack`：仅 redteam 使用，标注攻击类型

## 三个核心指标（写进 reports/BENCHMARK.md）
- **整体通过率**：用例判定符合期望的比例
- **高危样本检出率**：expect=high 的对抗样本被拦到 high 的比例（越高越好）
- **干净样本误报率**：expect=clean 被误判违规的比例（越低越好）

## 运行
```bash
python evals/run_evals.py              # 零依赖；规则门禁，刷新 reports/BENCHMARK.md
python evals/run_variant_baseline.py   # 零依赖；纯规则层变体/红队基线，刷新 reports/VARIANT_BASELINE.md
python scripts/run_llm_evals.py        # 配 key 在线；单模型主备快照，刷新 reports/LLM_EVAL.md
python scripts/run_model_crosscheck.py # 配 key 在线；双模型交叉对比，刷新 reports/MODEL_CROSSCHECK.md

# promptfoo 固定红队断言（在线，非门禁）
python scripts/export_guard_prompt.py                       # 从 DETECT_SYSTEM 导出守卫 prompt
promptfoo eval -c evals/promptfooconfig.yaml --env-file .env -o reports/PROMPTFOO_FIXED.json
python scripts/summarize_promptfoo.py                       # 汇总成 reports/PROMPTFOO.md（原始 JSON 不入库）
```
新增用例：直接往对应 jsonl 追加一行；规则改动后 CI 会自动重跑并把新 BENCHMARK 提交回仓库。

## promptfoo 固定断言（已接入，在线快照）
- `promptfooconfig.yaml`：9 条固定用例 × 硅基流动主力/兜底双模型。**prompt 是守卫的系统提示**（由 `scripts/export_guard_prompt.py` 从 `DETECT_SYSTEM` 导出、拼上待审话术），测的是守卫行为，不是裸模型——裸模型会顺从越狱直接写违规广告词，与产品无关。
- 断言用 `javascript` 解析守卫输出 JSON 的 `overall` 是否达到 `high`。**不用 `not-contains`**：正当拒绝会引述违规原话再驳斥，字面断言会把正确行为判成失败（实测踩过）。
- provider 配 `response_format: json_object`、`temperature: 0`、`max_tokens: 512`，对齐 `lcg.llm` 真实链路；不配 `json_object` 时模型偶发括号写错导致解析失败。
- 结果见 [`reports/PROMPTFOO.md`](../reports/PROMPTFOO.md)（逐条矩阵 + 稳定性说明）；原始 JSON 体积大且含模型原文，已被 `.gitignore` 排除。
- 自动广度红队生成另存 `promptfooconfig.redteam.yaml`，用 `promptfoo redteam run` 执行；**故意与 eval 分开**，否则 `promptfoo eval` 会触发大批量生成并大量消耗额度。

## 其他红队路线（P1，未接入）
- `deepteam.config.example.json`：DeepTeam（`pip install deepeval`）配置骨架，OWASP LLM Top10 映射，产出 `reports/SECURITY.md`。
- 深度多轮可再加微软 **PyRIT**、模型级广度扫描用 **Garak**；二者属重型依赖，不进 stdlib 主仓，建议隔离环境运行。
- redteam.jsonl 里的拆字/emoji 用例预期会绕过纯规则层——这正是 LLM 语义层 + 输入归一化存在的理由，也是你对外讲"规则是硬底线、LLM 补变体"的证据。
