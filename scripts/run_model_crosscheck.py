# -*- coding: utf-8 -*-
"""
run_model_crosscheck.py —— 多模型交叉在线评测（需配置模型 key，手动复跑，不进离线 CI）。

与 `scripts/run_llm_evals.py`（单模型主备容错快照）互补：把 redteam / semantic 用例
分别交给配置里的主力与兜底模型各跑一遍，对比两个模型在同一批变体 / 红队 / 语义样本上的
判定是否一致、各自通过率如何，暴露模型间语义判断分歧。

  · 规则硬底线不依赖模型，两模型一致；分歧只可能来自 LLM 语义层；
  · 每个模型用独立 LLMJudge，关闭主备切换，确保结果归属到指定模型；
  · 结果写入 reports/MODEL_CROSSCHECK.md（带日期 / 模型 / 调用数 / token 的快照），
    模型输出存在波动，不作为离线 CI 硬门禁。

运行：
  1) 复制 .env.example 为 .env，填 SILICONFLOW_API_KEY 与 LCG_MODEL_PRIMARY / FALLBACK；
  2) python scripts/run_model_crosscheck.py
"""
from __future__ import annotations

import dataclasses
import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from lcg import pipeline  # noqa: E402
from lcg.llm import LLMConfig, LLMJudge  # noqa: E402

CASES = ROOT / "evals" / "cases"
REPORTS = ROOT / "reports"
SEV = {"clean": 0, "low": 1, "medium": 2, "high": 3}


def load(name: str):
    p = CASES / name
    out = []
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(json.loads(line))
    return out


def main() -> int:
    cfg = LLMConfig.from_env()
    if not cfg.api_key or not (cfg.model_primary or cfg.model_fallback):
        print("[SKIP] 未配置 LLM：请在 .env 设置 SILICONFLOW_API_KEY 与模型后重跑。")
        print("       规则层离线评测请运行：python evals/run_evals.py（无需 key）。")
        return 2

    models = [m for m in (cfg.model_primary, cfg.model_fallback) if m]
    # 去重并保持顺序
    seen: set[str] = set()
    models = [m for m in models if not (m in seen or seen.add(m))]

    cases = []
    for c in load("redteam.jsonl"):
        c["_source"] = "redteam"
        c.setdefault("expect_risk", "high")
        cases.append(c)
    for c in load("semantic.jsonl"):
        c["_source"] = "semantic"
        cases.append(c)

    # 每个模型独立 judge，关闭主备切换，结果归属指定模型
    judges: dict[str, LLMJudge] = {}
    for m in models:
        mc = dataclasses.replace(cfg, model_primary=m, model_fallback="")
        judges[m] = LLMJudge(mc)

    rows = []
    for c in cases:
        text = c["text"]
        industry = c.get("industry", "general")
        platform = c.get("platform", "douyin")
        expect = c.get("expect_risk", "high")
        row = {"id": c.get("id", ""), "source": c["_source"],
               "attack": c.get("attack", "semantic"), "expect": expect, "results": {}}
        for m in models:
            r = pipeline.analyze(text, industry, platform, judge=judges[m])
            actual = r["risk_level"]
            ok = SEV[actual] >= SEV[expect]
            meta = r["llm"]
            row["results"][m] = {
                "actual": actual, "ok": ok, "model": meta.get("model", ""),
                "status": meta.get("status", ""), "tokens": meta.get("total_tokens", 0),
                "error": (meta.get("error") or "")[:120],
            }
        rows.append(row)

    def rate(m: str):
        xs = [r["results"][m] for r in rows]
        p = sum(1 for x in xs if x["ok"])
        return p, len(xs)

    today = datetime.date.today().isoformat()
    total_calls = sum(j.calls for j in judges.values())
    total_tokens = sum(x["tokens"] for r in rows for x in r["results"].values())

    # 分歧：任一模型判定层级不同，或一过一不过
    diverge = []
    for r in rows:
        actuals = {m: r["results"][m]["actual"] for m in models}
        oks = {m: r["results"][m]["ok"] for m in models}
        if len(set(actuals.values())) > 1 or len(set(oks.values())) > 1:
            diverge.append(r)

    def pct(n: int, t: int) -> str:
        return f"{n / t:.0%}" if t else "-"

    L = [
        "# MODEL CROSSCHECK · 多模型在线交叉评测快照", "",
        f"- 生成日期：{today}",
        f"- Provider：`{cfg.provider}`；交叉模型：{', '.join(f'`{m}`' for m in models)}",
        f"- 用例：{len(rows)} 条（红队 {sum(1 for r in rows if r['source'] == 'redteam')}，"
        f"语义 {sum(1 for r in rows if r['source'] == 'semantic')}）；"
        f"本次模型调用 {total_calls} 次，合计 {total_tokens} tokens",
        "- 性质：**配 key 后手动复跑的在线快照**，模型输出存在波动，**不作为离线 CI 硬门禁**；"
        "规则硬底线两模型一致，分歧仅来自 LLM 语义层。",
        "- 复现：配置 `.env` 后运行 `python scripts/run_model_crosscheck.py`。", "",
        "## 各模型通过率", "",
        "| 模型 | 通过 | 总数 | 通过率 |",
        "|---|---|---|---|",
    ]
    for m in models:
        p, t = rate(m)
        L.append(f"| `{m}` | {p}/{t} | {t} | {pct(p, t)} |")

    L += ["", "## 逐条交叉矩阵", "",
          "| ID | 来源 | 类型 | 期望 | " + " | ".join(f"{m} 判定/通过" for m in models) + " |",
          "|---|---|---|---|" + "---|" * len(models)]
    for r in rows:
        cells = []
        for m in models:
            x = r["results"][m]
            mark = "✓" if x["ok"] else "✗"
            cells.append(f"{x['actual']}/{mark}")
        L.append(f"| {r['id']} | {r['source']} | {r['attack']} | {r['expect']} | "
                 + " | ".join(cells) + " |")

    L += ["", f"## 模型分歧（{len(diverge)} 条）", ""]
    if diverge:
        L += ["| ID | 期望 | " + " | ".join(f"{m} 判定" for m in models) + " | 说明 |",
              "|---|---|" + "---|" * len(models)]
        for r in diverge:
            cells = [f"{r['results'][m]['actual']}" for m in models]
            note = "；".join(f"{m}:{r['results'][m]['status']}" for m in models)
            L.append(f"| {r['id']} | {r['expect']} | " + " | ".join(cells) + f" | {note} |")
    else:
        L.append("两模型在本批用例上判定一致。")

    L += [
        "",
        "> 仅为合规风险提示，不构成法律意见；单模型在线快照见 `reports/LLM_EVAL.md`，"
        "规则侧变体基线见 `reports/VARIANT_BASELINE.md`。",
        "",
    ]

    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "MODEL_CROSSCHECK.md").write_text("\n".join(L), encoding="utf-8")

    for m in models:
        p, t = rate(m)
        print(f"  {m}: {p}/{t} ({pct(p, t)})")
    print(f"  分歧 {len(diverge)}/{len(rows)}；调用 {total_calls} 次，{total_tokens} tokens")
    print("[OK] 已写出 reports/MODEL_CROSSCHECK.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
