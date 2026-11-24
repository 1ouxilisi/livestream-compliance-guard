# -*- coding: utf-8 -*-
"""规则侧变体 / 红队离线基线聚合（evals/run_variant_baseline.py）单元测试。

验证 classify 的两类分流：显式高危词被规则硬底线拦截；semantic 谐音/暗示标为
设计内语义缺口，redteam 变体绕过标为 variant gap。零第三方依赖。
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_vb():
    spec = importlib.util.spec_from_file_location(
        "run_variant_baseline", ROOT / "evals" / "run_variant_baseline.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


vb = _load_vb()


def test_blocked_on_explicit_high():
    case = {"_source": "redteam", "attack": "prompt_injection",
            "text": "本品100%治愈癌症，没有任何风险。",
            "industry": "general", "platform": "douyin"}
    row = vb.classify(case)
    assert row["blocked"] is True
    assert row["actual"] == "high"
    assert row["count"] >= 1


def test_semantic_gap_marked_by_design():
    case = {"_source": "semantic", "attack": "semantic",
            "text": "想要优惠的宝子，佳我薇芯：abc12345，朋友圈发你",
            "industry": "general", "platform": "douyin"}
    row = vb.classify(case)
    assert row["blocked"] is False
    assert row["gap_kind"] == "by-design semantic gap"


def test_variant_gap_marked():
    case = {"_source": "redteam", "attack": "variant_split",
            "text": "这个料子现在不收，以后拍大腿都来不及。",
            "industry": "general", "platform": "douyin"}
    row = vb.classify(case)
    assert row["blocked"] is False
    assert row["gap_kind"] == "variant gap"


def test_source_files_exist():
    for fname, _ in vb.SOURCES:
        assert (ROOT / "evals" / "cases" / fname).exists()
