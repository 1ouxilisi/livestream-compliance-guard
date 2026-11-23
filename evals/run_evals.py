# -*- coding: utf-8 -*-
"""
run_evals.py —— 零依赖规则层评测运行器（信任标准件的机床雏形）。
读取 evals/cases/{benign,adversarial}.jsonl，对 lcg 规则引擎跑分（根 server 是兼容 shim，
server.detect 与 lcg.engine.detect 是同一函数，import server 同时验证了向后兼容）：
  · 高危检出率（adversarial 中 expect=high 且实际>=high）
  · 干净误报率（benign 中 expect=clean 却被判违规）
  · 整体通过率
并写出 reports/BENCHMARK.md（机器/人可读，供 README 徽章与接入方评估使用）。
redteam.jsonl 与 semantic.jsonl 均标注 layer=llm：redteam 是提示注入/越狱红队（DeepTeam/PyRIT），
semantic 是谐音/拆字/emoji/暗示等规则层必然漏检、需 LLM 语义层裁决的用例。本运行器对二者只计数、
不裁决（配置模型 key 后由 LLM 层评测脚本跑分）。

运行：python evals/run_evals.py
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


def _rules_version() -> str:
    try:
        from lcg import rules_store
        return rules_store.meta().get("version", "?")
    except Exception:
        return "?"


def _rules_title() -> str:
    """报告抬头：核心包版本 ＋ 已加载行业插件包清单。"""
    try:
        from lcg import rules_store
        m = rules_store.meta()
        base = f"核心 {m.get('version', '?')}"
        pkgs = m.get("packages", [])
        if pkgs:
            names = "、".join(f"{p['package']} {p.get('version', '?')}" for p in pkgs)
            return f"{base} ＋ 行业插件（{names}）"
        return base
    except Exception:
        return _rules_version()


def load_cases(fname: str):
    p = CASES_DIR / fname
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.append(json.loads(line))
    return out


def evaluate(case: dict, kind: str):
    res = server.detect(case["text"], case.get("industry", "general"),
                        case.get("platform", "douyin"))
    actual = res["risk_level"]
    expected = case.get("expect_risk", "clean")
    a, e = RANK[actual], RANK[expected]
    # benign：不允许比预期更严重（否则是误报）；adversarial：不允许比预期更轻（否则是漏报）
    ok = (a <= e) if kind == "benign" else (a >= e)
    note = ""
    if ok and case.get("expect_any"):
        matched = [h["match"] for h in res["hits"]]
        ok = any(any(t in m or m in t for m in matched) for t in case["expect_any"])
        if not ok:
            note = "未命中 expect_any 中的违规点"
    return ok, actual, expected, res, note


def main() -> int:
    rows = []
    n_pass = n_fail = 0
    hi_total = hi_ok = 0
    clean_total = clean_fp = 0

    for kind, fname in [("benign", "benign.jsonl"), ("adversarial", "adversarial.jsonl")]:
        for case in load_cases(fname):
            ok, actual, expected, res, note = evaluate(case, kind)
            n_pass += ok
            n_fail += (not ok)
            if kind == "adversarial" and expected == "high":
                hi_total += 1
                hi_ok += (RANK[actual] >= RANK["high"])
            if kind == "benign" and expected == "clean":
                clean_total += 1
                clean_fp += (actual != "clean")
            rows.append({
                "id": case.get("id", ""), "kind": kind, "expected": expected,
                "actual": actual, "result": "PASS" if ok else "FAIL",
                "count": res["count"], "note": case.get("note", "") or note,
            })

    redteam_n = len(load_cases("redteam.jsonl"))
    semantic_n = len(load_cases("semantic.jsonl"))
    total = n_pass + n_fail
    pass_rate = n_pass / total if total else 0.0
    detect_rate = hi_ok / hi_total if hi_total else 0.0
    fp_rate = clean_fp / clean_total if clean_total else 0.0

    today = datetime.date.today().isoformat()
    print(f"规则层评测：{total} 条，通过 {n_pass}，失败 {n_fail}，"
          f"通过率 {pass_rate:.1%}；高危检出率 {detect_rate:.1%}；干净误报率 {fp_rate:.1%}；"
          f"LLM 层红队用例 {redteam_n} 条、语义层待跑用例 {semantic_n} 条（需配置模型 key）")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# BENCHMARK · 直播电商合规守卫 MCP（规则层 {_rules_title()}）",
        "",
        f"- 生成日期：{today}",
        "- 评测对象：`lcg` 规则引擎（src/lcg；规则源为核心包 rules.v1.json ＋ "
        "rules/plugins/*.json 行业插件；根 server.py 为兼容 shim）",
        f"- 规则层用例：{total} 条（良性 {sum(1 for x in rows if x['kind']=='benign')}，"
        f"对抗 {sum(1 for x in rows if x['kind']=='adversarial')}）",
        f"- **整体通过率：{pass_rate:.1%}**（{n_pass}/{total}）",
        f"- **高危样本检出率：{detect_rate:.1%}**（{hi_ok}/{hi_total}）",
        f"- **干净样本误报率：{fp_rate:.1%}**（{clean_fp}/{clean_total}，越低越好）",
        f"- LLM 层红队用例：{redteam_n} 条（注入/越狱，交由 DeepTeam·PyRIT 在 LLM 层裁决）",
        f"- 语义层待跑用例：{semantic_n} 条（谐音/拆字/emoji/暗示，"
        "规则层已确认漏检，配 key 后由 LLM 层裁决）",
        "",
        "| ID | 类型 | 期望 | 实际 | 结果 | 命中数 | 备注 |",
        "|---|---|---|---|---|---|---|",
    ]
    for x in rows:
        lines.append(f"| {x['id']} | {x['kind']} | {x['expected']} | {x['actual']} | "
                     f"{x['result']} | {x['count']} | {x['note']} |")
    lines += [
        "",
        "> 复现：`python evals/run_evals.py`。本报告由脚本生成，规则或用例变更后在 CI 自动刷新。",
        "> 仅为合规风险提示，不构成法律意见，以监管机关与平台最新规则为准。",
        "",
    ]
    (REPORTS_DIR / "BENCHMARK.md").write_text("\n".join(lines), encoding="utf-8")
    print("[OK] 已写出 reports/BENCHMARK.md")

    if n_fail:
        print("[FAIL] 存在未通过用例，请检查规则或评测期望。")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
