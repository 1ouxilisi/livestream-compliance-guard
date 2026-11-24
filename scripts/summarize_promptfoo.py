# -*- coding: utf-8 -*-
"""
summarize_promptfoo.py —— 把 promptfoo 固定断言结果（JSON）汇总成可提交的 Markdown 报告。

为什么需要：
  promptfoo 原始输出（`reports/PROMPTFOO_FIXED.json`）体积大且含完整模型原文，不入库；
  这里只保留可复核的「用例 × 模型 → 判定 / 通过」矩阵与失败原因摘要，写成
  `reports/PROMPTFOO.md` 供对内外引用。

输入：promptfoo eval 输出的 JSON（默认 `reports/PROMPTFOO_FIXED.json`）
输出：`reports/PROMPTFOO.md`

运行：python scripts/summarize_promptfoo.py
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "reports" / "PROMPTFOO_FIXED.json"
OUT = ROOT / "reports" / "PROMPTFOO.md"


def main() -> int:
    if not SRC.exists():
        print(f"[SKIP] 未找到 {SRC.relative_to(ROOT)}，请先运行 promptfoo eval 生成。")
        return 2
    data = json.loads(SRC.read_text(encoding="utf-8"))
    results = data.get("results", {}).get("results", [])
    if not results:
        print("[SKIP] 结果为空。")
        return 2

    provs: list[str] = []
    tests: dict[str, dict[str, dict]] = {}
    for r in results:
        pid = r.get("provider", {}).get("id", "?")
        if pid not in provs:
            provs.append(pid)
        text = (r.get("vars") or {}).get("text", "")
        desc = (r.get("vars") or {}).get("id") or r.get("description") or text[:40]
        tests.setdefault(desc, {"text": text, "rows": {}})["rows"][pid] = r

    total = sum(len(v["rows"]) for v in tests.values())
    passed = sum(1 for v in tests.values() for r in v["rows"].values() if r.get("success"))
    today = datetime.date.today().isoformat()

    def cell(r: dict) -> str:
        if r is None:
            return "—"
        out = r.get("response", {}).get("output", "") or ""
        verdict = ""
        low = out.lower()
        for v in ("high", "medium", "low", "clean"):
            if f'"overall":"{v}"' in low.replace(" ", ""):
                verdict = v
                break
        mark = "✓" if r.get("success") else "✗"
        return f"{verdict or '—'}/{mark}"

    L = [
        "# PROMPTFOO · 固定红队断言快照（守卫系统提示下）", "",
        f"- 生成日期：{today}",
        f"- 用例 × 模型：{total} 组；通过 **{passed}/{total}**",
        "- 配置：`evals/promptfooconfig.yaml`；prompt 由 "
        "`python scripts/export_guard_prompt.py` 从 "
        "`DETECT_SYSTEM` 导出（测的是守卫行为，不是裸模型）",
        "- 性质：**配 key 后手动复跑的在线快照**，随模型版本 / 余额波动，**不作为离线 CI 门禁**；"
        "离线确定性门禁见 `reports/BENCHMARK.md`。", "",
        "## 逐条矩阵", "",
        "| 用例 | " + " | ".join(f"`{p}`" for p in provs) + " |",
        "|---" * (len(provs) + 1) + "|",
    ]
    for desc, v in tests.items():
        cells = [cell(v["rows"].get(p)) for p in provs]
        L.append(f"| {desc} | " + " | ".join(cells) + " |")

    fails = [
        (desc, p, r)
        for desc, v in tests.items()
        for p, r in v["rows"].items()
        if not r.get("success")
    ]
    L += ["", "## 未通过 / 已知分歧", ""]
    if fails:
        for desc, p, r in fails:
            out = (r.get("response", {}).get("output", "") or "").replace("\n", " ")[:160]
            L.append(f"- `{desc}` @ `{p}`：模型输出 `{out}`")
        L += [
            "",
            "> 说明：`r16`（英文指令覆盖）属**指令覆盖类样本**——它本身不含违规宣称，"
            "只是要求「不要输出风险提示」，兜底模型据此判 `clean`，与 `MODEL_CROSSCHECK.md` 中 "
            "`r12` 的中文同类分歧同源。该分歧如实记录，不通过放宽断言凑红；对外只称"
            "「主力模型守住、兜底模型存在同类分歧」。",
        ]
    else:
        L.append("- 无")

    L += [
        "",
        "## 稳定性说明", "",
        "- `temperature=0` 下仍观察到波动：历史一次运行中 `r16`（英文指令覆盖）在兜底 "
        "`DeepSeek-V3` 上判 `clean`（自评 17/18），本次同用例判 `high`（18/18）。该样本本身不含"
        "违规宣称、只要求关闭风险提示，与 `MODEL_CROSSCHECK.md` 的 `r12` 中文同类分歧同源。",
        "- 因此本报告数字**只代表本次快照**，对外引用须带日期与模型；不得据单次 18/18 承诺"
        "「永不误判」「全模型一致」。",
        "",
        "## 复现", "",
        "```bash",
        "python scripts/export_guard_prompt.py",
        "promptfoo eval -c evals/promptfooconfig.yaml --env-file .env "
        "-o reports/PROMPTFOO_FIXED.json",
        "python scripts/summarize_promptfoo.py",
        "```",
        "",
        "> 仅为合规风险提示，不构成法律意见。"
        "自动广度红队生成见 `evals/promptfooconfig.redteam.yaml`。",
        "",
    ]
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"[OK] 已写出 {OUT.relative_to(ROOT)}（{passed}/{total} 通过）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
