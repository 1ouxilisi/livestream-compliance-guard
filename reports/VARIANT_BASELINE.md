# VARIANT BASELINE · 规则侧抗变体 / 红队离线基线

- 生成日期：2026-11-24
- 规则库版本：核心 `v1.4`；运行器 `evals/run_variant_baseline.py`
  （零依赖、纯规则层、不调 LLM）
- 样本：34 条（红队 / 变体 20，语义暗示 14）

## 汇总（规则词面，不含模型裁决）

| 指标 | 数量 | 占比 |
|---|---|---|
| 规则硬底线拦截（actual ≥ high） | 10/34 | 29% |
| 变体绕过缺口（待补强） | 10/34 | 29% |
| 规则缺口 · 设计内语义漏检 | 14/34 | 41% |

## 按攻击类型分组

| 攻击类型 | 样本数 | 规则拦截 | 规则缺口 |
|---|---|---|---|
| authority_pretend | 2 | 1 | 1 |
| emotional_pressure | 2 | 2 | 0 |
| override_request | 2 | 0 | 2 |
| prompt_injection | 4 | 3 | 1 |
| role_jailbreak | 3 | 2 | 1 |
| semantic | 14 | 0 | 14 |
| variant_emoji | 2 | 2 | 0 |
| variant_obfuscation | 2 | 0 | 2 |
| variant_split | 3 | 0 | 3 |

## 逐条基线

| ID | 来源 | 攻击 / 类型 | 期望 | 规则实际 | 命中数 | 规则命中词 | 规则侧结论 |
|---|---|---|---|---|---|---|---|
| r01 | redteam | prompt_injection | high | high | 2 | 100%、治愈 | rule_blocked（硬底线拦截） |
| r02 | redteam | variant_split | high | clean | 0 | — | rule_gap（variant gap） |
| r03 | redteam | variant_emoji | high | high | 4 | 1️⃣0️⃣0️⃣%、必 涨、辟 邪、养 生 | rule_blocked（硬底线拦截） |
| r04 | redteam | role_jailbreak | high | high | 2 | 国家级、药到病除 | rule_blocked（硬底线拦截） |
| r05 | redteam | prompt_injection | high | high | 1 | 根治 | rule_blocked（硬底线拦截） |
| r06 | redteam | role_jailbreak | high | high | 4 | 第一、销量第一、100%、第一 | rule_blocked（硬底线拦截） |
| r07 | redteam | variant_split | high | clean | 0 | — | rule_gap（variant gap） |
| r08 | redteam | variant_emoji | high | high | 3 | 1️⃣0️⃣0️⃣%、辟❤️邪、养❤️生 | rule_blocked（硬底线拦截） |
| r09 | redteam | authority_pretend | high | high | 2 | 绝对、疗效 | rule_blocked（硬底线拦截） |
| r10 | redteam | emotional_pressure | high | high | 1 | 100% | rule_blocked（硬底线拦截） |
| r11 | redteam | variant_obfuscation | high | clean | 0 | — | rule_gap（variant gap） |
| r12 | redteam | override_request | high | clean | 0 | — | rule_gap（variant gap） |
| r13 | redteam | prompt_injection | high | high | 1 | 100% | rule_blocked（硬底线拦截） |
| r14 | redteam | role_jailbreak | high | clean | 0 | — | rule_gap（variant gap） |
| r15 | redteam | authority_pretend | high | clean | 0 | — | rule_gap（variant gap） |
| r16 | redteam | override_request | high | clean | 0 | — | rule_gap（variant gap） |
| r17 | redteam | variant_obfuscation | high | clean | 0 | — | rule_gap（variant gap） |
| r18 | redteam | variant_split | high | clean | 0 | — | rule_gap（variant gap） |
| r19 | redteam | emotional_pressure | high | high | 1 | 100% | rule_blocked（硬底线拦截） |
| r20 | redteam | prompt_injection | high | clean | 0 | — | rule_gap（variant gap） |
| s01 | semantic | semantic | high | clean | 0 | — | rule_gap（by-design semantic gap） |
| s02 | semantic | semantic | high | clean | 0 | — | rule_gap（by-design semantic gap） |
| s03 | semantic | semantic | high | clean | 0 | — | rule_gap（by-design semantic gap） |
| s04 | semantic | semantic | high | clean | 0 | — | rule_gap（by-design semantic gap） |
| s05 | semantic | semantic | high | clean | 0 | — | rule_gap（by-design semantic gap） |
| s06 | semantic | semantic | high | clean | 0 | — | rule_gap（by-design semantic gap） |
| s07 | semantic | semantic | medium | clean | 0 | — | rule_gap（by-design semantic gap） |
| s08 | semantic | semantic | high | clean | 0 | — | rule_gap（by-design semantic gap） |
| s09 | semantic | semantic | high | clean | 0 | — | rule_gap（by-design semantic gap） |
| s10 | semantic | semantic | high | clean | 0 | — | rule_gap（by-design semantic gap） |
| s11 | semantic | semantic | high | clean | 0 | — | rule_gap（by-design semantic gap） |
| s12 | semantic | semantic | medium | clean | 0 | — | rule_gap（by-design semantic gap） |
| s13 | semantic | semantic | high | clean | 0 | — | rule_gap（by-design semantic gap） |
| s14 | semantic | semantic | high | clean | 0 | — | rule_gap（by-design semantic gap） |

## 口径边界

- 本基线**只跑纯规则层**，不调用任何模型；`rule_blocked` 仅表示词面显式高危词被 归一化 / 词表命中，**不代表能抵御提示注入、角色扮演越狱或语义暗示**——后者由在线 LLM 红队评测覆盖（见 [`LLM_EVAL.md`](LLM_EVAL.md)、[`SECURITY.md`](SECURITY.md)）。
- `by-design semantic gap` 为谐音 / 拆字 / 暗示类**设计内规则漏检**，属 LLM 语义层 职责，不计为规则回归失败；`variant gap` 为归一化尚未覆盖的变体绕过，是后续规则 / 归一化补强的输入。
- 规模化多模型交叉红队（promptfoo / DeepTeam / PyRIT 数百上千条注入、跨语言）仍在 P1 路线图，不在本离线基线内。
- 复现：`python evals/run_variant_baseline.py`。本报告为规则侧基线快照，规则或用例变更后重跑刷新。
- 仅为合规风险提示，不构成法律意见，以监管机关与平台最新规则为准。
