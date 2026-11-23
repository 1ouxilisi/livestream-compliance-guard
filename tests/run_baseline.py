# -*- coding: utf-8 -*-
"""
run_baseline.py —— 零依赖基线特征测试（不依赖 pytest，stdlib 直接运行）。
作用：在把引擎从根 server.py 重构进 src/ 之前，先锁定当前已验证行为；
重构后本测试必须依旧全绿，否则即为回归。

运行：python tests/run_baseline.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import server  # noqa: E402  根目录规则引擎（已注入 sys.path）

_passed = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _passed
    assert cond, f"[FAIL] {name} {detail}"
    _passed += 1
    print(f"  PASS  {name}")


# 1) 高危翡翠话术：必须判 high，且命中多个已知违规点
r = server.detect(
    "家人们这块玻璃种帝王绿，100%保真，戴了能养生辟邪，收藏必涨，加微信私下交易，今天最后一天！",
    "jadeite", "douyin")
matched = {h["match"] for h in r["hits"]}
check("高危话术判 high", r["risk_level"] == "high", f"actual={r['risk_level']}")
check("高危命中数>=5", r["count"] >= 5, f"count={r['count']}")
check("命中绝对化/迷信/导流点", {"100%", "保真", "养生", "辟邪", "收藏必涨", "加微信"} & matched,
      f"matched={sorted(matched)}")

# 2) 干净的通用商品文案：必须 clean
r2 = server.detect("本品采用优质不锈钢工艺，做工精细，支持七天无理由退货。", "general", "taobao")
check("干净通用文案判 clean", r2["risk_level"] == "clean" and r2["count"] == 0,
      f"actual={r2['risk_level']} count={r2['count']}")

# 3) 合规翡翠话术（含术语 A 货）：应为 low 提示而非高危
r3 = server.detect("这是天然翡翠A货吊坠，配有鉴定证书，支持复检，喜欢可在直播间下单。",
                   "jadeite", "douyin")
check("合规翡翠话术不超过 low", server.SEV_ORDER[r3["risk_level"]] <= server.SEV_ORDER["low"],
      f"actual={r3['risk_level']}")

# 4) 批量检测聚合：一脏一净，overall=high，flagged=1
b = server.scan_batch([
    {"speaker": "主播", "text": "本品100%保真，收藏必涨，稳赚不赔。"},
    {"speaker": "主播", "text": "喜欢可以在直播间下单，支持七天无理由退货。"},
], "jadeite", "douyin")
check("批量聚合 overall=high", b["overall_risk"] == "high", f"actual={b['overall_risk']}")
check("批量 flagged_segments=1", b["flagged_segments"] == 1, f"flagged={b['flagged_segments']}")
check("批量 high_risk_hits>=1", b["high_risk_hits"] >= 1, f"high={b['high_risk_hits']}")

# 5) 规则接口可用且做行业隔离
rules_jade = server.get_rules("jadeite", "douyin")["rules"]
rules_general = server.get_rules("general", "douyin")["rules"]
check("规则接口返回非空", len(rules_jade) > 0 and len(rules_general) > 0)
check("general 不含翡翠专属规则",
      all("翡翠" not in x["category"] for x in rules_general),
      f"cats={[x['category'] for x in rules_general if '翡翠' in x['category']]}")

# 6) 改写建议对已知词生效
rw = server.suggest_rewrite("这是最好的，保真", "jadeite", "douyin")
frm = {x["from"] for x in rw["replacements"]}
check("改写建议包含 最好/保真", {"最好", "保真"} & frm, f"from={sorted(frm)}")

print(f"\nALL BASELINE TESTS PASSED ({_passed} checks)")
