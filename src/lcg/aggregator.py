# -*- coding: utf-8 -*-
"""
lcg.aggregator —— 整场直播检测结果的聚合统计（纯本地、零第三方依赖）。

输入为 ``engine.scan_batch`` 的返回（或同构的 ``results`` 列表），输出：
  · 风险等级分布（clean / low / medium / high 分段计数）；
  · 命中类别与严重度分布；
  · 按主播（speaker）聚合的最高风险、分段数与 high 命中数；
  · 待整改清单（所有非 clean 分段及其命中类别）。

本模块只做统计与归类，不改变任何判定结论；供周报、看板与人工复核使用。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .models import RISK_LEVELS, SEV_ORDER


def _results_of(batch: Any) -> List[Dict[str, Any]]:
    if isinstance(batch, dict):
        return batch.get("results", []) or []
    if isinstance(batch, list):
        return batch
    return []


def summarize(batch: Any) -> Dict[str, Any]:
    results = _results_of(batch)

    distribution = {level: 0 for level in RISK_LEVELS}
    severity_hits = {"high": 0, "medium": 0, "low": 0}
    category_count: Dict[str, int] = {}
    speakers: Dict[str, Dict[str, Any]] = {}
    review_list: List[Dict[str, Any]] = []

    for seg in results:
        if not isinstance(seg, dict):
            continue
        risk = seg.get("risk_level", "clean")
        distribution[risk] = distribution.get(risk, 0) + 1
        speaker = str(seg.get("speaker", "") or "未知")
        hits = seg.get("hits", []) or []

        sp = speakers.setdefault(speaker, {"max_risk": "clean", "segments": 0,
                                          "high_hits": 0})
        sp["segments"] += 1
        if SEV_ORDER.get(risk, 0) > SEV_ORDER.get(sp["max_risk"], 0):
            sp["max_risk"] = risk

        categories: List[str] = []
        for h in hits:
            sev = str(h.get("severity", ""))
            if sev in severity_hits:
                severity_hits[sev] += 1
            if sev == "high":
                sp["high_hits"] += 1
            cat = str(h.get("category", "") or "未分类")
            category_count[cat] = category_count.get(cat, 0) + 1
            categories.append(cat)

        if risk != "clean":
            review_list.append({
                "seq": seg.get("seq"),
                "speaker": speaker,
                "text": seg.get("text", ""),
                "risk_level": risk,
                "categories": sorted(set(categories)),
            })

    top_categories = sorted(category_count.items(), key=lambda kv: (-kv[1], kv[0]))

    overall = "clean"
    if any(seg.get("risk_level") == "high" for seg in results if isinstance(seg, dict)):
        overall = "high"
    elif any(seg.get("risk_level") == "medium" for seg in results if isinstance(seg, dict)):
        overall = "medium"
    elif any(seg.get("risk_level") == "low" for seg in results if isinstance(seg, dict)):
        overall = "low"

    return {
        "overall_risk": overall,
        "segments": len(results),
        "flagged_segments": sum(1 for r in review_list),
        "risk_distribution": distribution,
        "severity_hits": severity_hits,
        "categories": [{"category": c, "count": n} for c, n in top_categories],
        "speakers": [
            {"speaker": name, **stats}
            for name, stats in sorted(speakers.items(), key=lambda kv: kv[0])
        ],
        "review_list": review_list,
    }
