# -*- coding: utf-8 -*-
"""
run_variant_baseline.py —— 规则侧「抗变体 / 红队」离线基线聚合（零依赖，不调 LLM）。

与 `evals/run_evals.py`（良性/对抗规则门禁）、`scripts/run_llm_evals.py`（在线 LLM 红队）互补：
  · 读取 `cases/redteam.jsonl`（提示注入 / 拆字 / emoji / 越狱）与 `cases/semantic.jsonl`
    （谐音 / 暗示，规则层设计内漏检）；
  · 只跑纯规则引擎 `server.detect`，记录规则层实际层级、命中数与命中词；
  · 把每条样本归入两类：
      - rule_blocked：规则硬底线已拦到 high（词面显式高危词仍被归一化/词表命中）；
      - rule_gap：规则层未到 high，属规则侧缺口，交 LLM 语义 / 红队层裁决；
  · 聚合拦截数 / 缺口数并按攻击类型分组，写出 `reports/VARIANT_BASELINE.md`。

口径边界（务必与对外说明一致）：
  · 本脚本不调用模型，结果只反映**规则词面**能力；规则命中显式词 ≠ 能抵御提示注入 /
    角色扮演接管，后者由在线 LLM 红队评测覆盖（见 `reports/LLM_EVAL.md`、`reports/SECURITY.md`）；
  · semantic 谐音 / 暗示是规则层**设计内漏检**，属 LLM 语义层职责，不计为规则回归失败；
  · 规模化多模型交叉红队（promptfoo / DeepTeam / PyRIT）仍在 P1 路线图，不在本离线基线内；
  · 规则缺口是分层设计的预期结果，本脚本退出码恒为 0，不作为离线 CI 硬门禁。

运行：python evals/run_variant_baseline.py
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import server  # noqa: E402  兼容 shim：server.detect is lcg.engine.detect

CASES_DIR = ROOT / "evals" / "cases"
REPORTS_DIR = ROOT / "reports"
RANK = server.SEV_ORDER

# 纳入规则侧基线的变体 / 红队 / 语义用例文件；标签用于报告分组
SOURCES = [
    ("redteam.jsonl", "redteam"),
    ("semantic.jsonl", "semantic"),
]


def _rules_version() -> str:
    try:
        from lcg import rules_store
        return rules_store.meta().get("version", "?")
    except Exception:
        return "?"


def load_cases(fname: str):
    p = CASES_DIR / fname
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(json.loads(line))
    return out


def classify(case: dict) -> dict:
    """对单条变体 / 红队样本跑规则引擎，返回规则侧基线记录。"""
    res = server.detect(case["text"], case.get("industry", "general"),
                        case.get("platform", "douyin"))
    actual = res["risk_level"]
    expected = case.get("expect_risk", "high")
    blocked = RANK[actual] >= RANK["high"]
    hits = [h["match"] for h in res["hits"]]
    source = case.get("_source", "")
    is_semantic = source == "semantic"
    attack = case.get("attack", "semantic" if is_semantic else "variant")
    # semantic 谐音 / 暗示为设计内规则缺口；其余缺口属待 LLM / 归一化补强的变体绕过
    gap_kind = "by-design semantic gap" if is_semantic else "variant gap"
    return {
        "id": case.get("id", ""),
        "source": source,
        "attack": attack,
        "expected": expected,
        "actual": actual,
        "count": res["count"],
        "hits": hits,
        "blocked": blocked,
        "gap_kind": gap_kind,
        "note": case.get("note", ""),
    }


def main() -> int:
    rows: list[dict] = []
    for fname, label in SOURCES:
        for case in load_cases(fname):
            case["_source"] = label
            rows.append(classify(case))

    total = len(rows)
    blocked = [r for r in rows if r["blocked"]]
    gaps = [r for r in rows if not r["blocked"]]
    by_design = [r for r in gaps if r["gap_kind"] == "by-design semantic gap"]
    variant_gaps = [r for r in gaps if r["gap_kind"] == "variant gap"]

    today = datetime.date.today().isoformat()
    ver = _rules_version()

    def pct(n: int) -> str:
        return f"{n / total:.0%}" if total else "-"

    # 按攻击类型分组聚合
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(r["attack"], []).append(r)

    lines = [
        "# VARIANT BASELINE · 规则侧抗变体 / 红队离线基线",
        "",
        f"- 生成日期：{today}",
        f"- 规则库版本：核心 `{ver}`；运行器 `evals/run_variant_baseline.py`",
        "  （零依赖、纯规则层、不调 LLM）",
        f"- 样本：{total} 条（红队 / 变体 {sum(1 for r in rows if r['source'] == 'redteam')}，"
        f"语义暗示 {len(by_design)}）",
        "",
        "## 汇总（规则词面，不含模型裁决）",
        "",
        "| 指标 | 数量 | 占比 |",
        "|---|---|---|",
        f"| 规则硬底线拦截（actual ≥ high） | {len(blocked)}/{total} | {pct(len(blocked))} |",
        f"| 变体绕过缺口（待补强） | {len(variant_gaps)}/{total} | {pct(len(variant_gaps))} |",
        f"| 规则缺口 · 设计内语义漏检 | {len(by_design)}/{total} | {pct(len(by_design))} |",
        "",
        "## 按攻击类型分组",
        "",
        "| 攻击类型 | 样本数 | 规则拦截 | 规则缺口 |",
        "|---|---|---|---|",
    ]
    for attack, items in sorted(groups.items()):
        b = sum(1 for x in items if x["blocked"])
        lines.append(f"| {attack} | {len(items)} | {b} | {len(items) - b} |")

    lines += [
        "",
        "## 逐条基线",
        "",
        "| ID | 来源 | 攻击 / 类型 | 期望 | 规则实际 | 命中数 | 规则命中词 | 规则侧结论 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        hits = "、".join(r["hits"]) if r["hits"] else "—"
        verdict = "rule_blocked（硬底线拦截）" if r["blocked"] else f"rule_gap（{r['gap_kind']}）"
        lines.append(
            f"| {r['id']} | {r['source']} | {r['attack']} | {r['expected']} | {r['actual']} "
            f"| {r['count']} | {hits} | {verdict} |"
        )

    lines += [
        "",
        "## 口径边界",
        "",
        "- 本基线**只跑纯规则层**，不调用任何模型；`rule_blocked` 仅表示词面显式高危词被 "
        "归一化 / 词表命中，**不代表能抵御提示注入、角色扮演越狱或语义暗示**——后者由在线 "
        "LLM 红队评测覆盖（见 [`LLM_EVAL.md`](LLM_EVAL.md)、[`SECURITY.md`](SECURITY.md)）。",
        "- `by-design semantic gap` 为谐音 / 拆字 / 暗示类**设计内规则漏检**，属 LLM 语义层 "
        "职责，不计为规则回归失败；`variant gap` 为归一化尚未覆盖的变体绕过，是后续规则 / "
        "归一化补强的输入。",
        "- 规模化多模型交叉红队（promptfoo / DeepTeam / PyRIT 数百上千条注入、跨语言）"
        "仍在 P1 路线图，不在本离线基线内。",
        "- 复现：`python evals/run_variant_baseline.py`。本报告为规则侧基线快照，"
        "规则或用例变更后重跑刷新。",
        "- 仅为合规风险提示，不构成法律意见，以监管机关与平台最新规则为准。",
        "",
    ]

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "VARIANT_BASELINE.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"[变体基线] 样本 {total}：规则拦截 {len(blocked)}，变体缺口 {len(variant_gaps)}，"
          f"设计内语义缺口 {len(by_design)}")
    print("[OK] 已写出 reports/VARIANT_BASELINE.md")
    # 缺口是分层设计的预期结果，不作为离线门禁失败，退出码恒 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
