# reports/ —— 对外信任凭证（信任标准件 ④）

本目录存放**可供使用者、集成方与审计者复核**的可复现报告，**需要提交进 Git**（不被 .gitignore 忽略）。

| 文件 | 由谁生成 | 状态 |
|---|---|---|
| `BENCHMARK.md` | `python evals/run_evals.py`（离线、CI 自动刷新并提交） | ✅ 87 条 100% |
| `VARIANT_BASELINE.md` | `python evals/run_variant_baseline.py`（离线、纯规则层变体/红队基线） | ✅ 34 条基线 |
| `LLM_EVAL.md` | `python scripts/run_llm_evals.py`（配 key 在线复跑，非 CI 门禁） | 🟡 73/73（在线快照，随模型波动） |
| `MODEL_CROSSCHECK.md` | `python scripts/run_model_crosscheck.py`（配 key 双模型交叉，非 CI 门禁） | 🟡 Qwen 34/34、DeepSeek 33/34（在线快照，分歧 r12） |
| `PERF.md` | `python scripts/bench_perf.py`（规则层延迟/吞吐 + LLM 抽样；本机测量，仅供相对比较） | ✅ 已生成 |
| `SECURITY.md` | LLM 层红队评测报告（随 `run_llm_evals.py` 结果更新缓解说明） | ✅ 已生成 |
| 审计签名/报告样例 | 远程运行时对每次扫描输出签名审计凭证 | P2 |

用途：README 徽章、接入方评估与合规尽调可引用。所有数字必须来自脚本可复现结果，不手工美化。
