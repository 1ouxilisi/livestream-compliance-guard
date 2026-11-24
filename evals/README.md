# evals/ —— 评测集与红队（数据/信任标准件 ③ 的机床）

## 用例文件（JSONL，每行一条）
| 文件 | 用途 | 裁决层 |
|---|---|---|
| `cases/benign.jsonl` | 干净/合规话术，测**误报** | 规则层 |
| `cases/adversarial.jsonl` | 违规话术，测**检出** | 规则层 |
| `cases/redteam.jsonl` | 注入/拆字/emoji/越狱 | **LLM 层**（DeepTeam/PyRIT，P1） |
| `cases/semantic.jsonl` | 谐音/暗示，规则层设计内漏检 | **LLM 语义层** |

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
```
新增用例：直接往对应 jsonl 追加一行；规则改动后 CI 会自动重跑并把新 BENCHMARK 提交回仓库。

## 接入 LLM 层红队（P1）
- `promptfooconfig.yaml`：providers 已指向硅基流动主力/兜底双模型（key 走 `SILICONFLOW_API_KEY` 环境变量）；`npm i -g promptfoo` 后 `promptfoo eval -c evals/promptfooconfig.yaml`，对 LLM 改写/变体识别做广度红队与回归。双模型基础交叉已由 `scripts/run_model_crosscheck.py` 覆盖，无需 npm。
- `deepteam.config.example.json`：DeepTeam（`pip install deepeval`）配置骨架，OWASP LLM Top10 映射，产出 `reports/SECURITY.md`。
- 深度多轮可再加微软 **PyRIT**、模型级广度扫描用 **Garak**。
- redteam.jsonl 里的拆字/emoji 用例预期会绕过纯规则层——这正是 LLM 语义层 + 输入归一化存在的理由，也是你对外讲"规则是硬底线、LLM 补变体"的证据。
