# -*- coding: utf-8 -*-
"""批量聚合：风险分布、类别/严重度计数、主播聚合与待整改清单。"""
from lcg import aggregator


def _batch():
    return {
        "overall_risk": "high",
        "segments": 3,
        "results": [
            {"seq": 0, "speaker": "主播A", "text": "304不锈钢内胆，48小时发货。",
             "risk_level": "clean", "hits": []},
            {"seq": 1, "speaker": "主播B", "text": "全网最好，销量第一。",
             "risk_level": "high",
             "hits": [{"category": "绝对化用语", "severity": "high", "match": "最好"}]},
            {"seq": 2, "speaker": "主播B", "text": "吊打同类大牌。",
             "risk_level": "medium",
             "hits": [{"category": "贬低同类", "severity": "medium", "match": "吊打"}]},
        ],
    }


def test_distribution_and_counts():
    s = aggregator.summarize(_batch())
    assert s["segments"] == 3
    assert s["flagged_segments"] == 2
    assert s["risk_distribution"] == {"clean": 1, "low": 0, "medium": 1, "high": 1}
    assert s["severity_hits"] == {"high": 1, "medium": 1, "low": 0}
    cats = {c["category"]: c["count"] for c in s["categories"]}
    assert cats == {"绝对化用语": 1, "贬低同类": 1}


def test_speaker_aggregation():
    s = aggregator.summarize(_batch())
    by_name = {x["speaker"]: x for x in s["speakers"]}
    assert by_name["主播A"]["max_risk"] == "clean"
    assert by_name["主播A"]["segments"] == 1
    assert by_name["主播B"]["max_risk"] == "high"
    assert by_name["主播B"]["segments"] == 2
    assert by_name["主播B"]["high_hits"] == 1


def test_review_list():
    s = aggregator.summarize(_batch())
    assert len(s["review_list"]) == 2
    seqs = [r["seq"] for r in s["review_list"]]
    assert seqs == [1, 2]
    assert s["review_list"][0]["categories"] == ["绝对化用语"]


def test_overall_risk_from_results():
    clean_only = {"results": [{"risk_level": "clean", "hits": []}]}
    assert aggregator.summarize(clean_only)["overall_risk"] == "clean"
    medium_only = {"results": [{"risk_level": "medium", "hits": []}]}
    assert aggregator.summarize(medium_only)["overall_risk"] == "medium"


def test_accepts_plain_list():
    rows = [{"speaker": "S", "text": "x", "risk_level": "low", "hits": []}]
    s = aggregator.summarize(rows)
    assert s["segments"] == 1
    assert s["overall_risk"] == "low"
