# -*- coding: utf-8 -*-
"""lcg 规则引擎单元测试（pytest）。

覆盖：核心判定、批量聚合、行业隔离、改写、等长归一化、入参校验、
边界输入、规则库加载，以及根 server.py shim 与 lcg.engine 的同一性。
零第三方依赖即可运行（server_stdio 相关用例在缺 mcp 时自动跳过）。
"""
import pytest

import server  # 根 shim（conftest 已把根与 src 加入 sys.path）
from lcg import engine, rules_store
from lcg.models import normalize_text

HIGH = "家人们这块玻璃种帝王绿，100%保真，戴了能养生辟邪，收藏必涨，加微信私下交易，今天最后一天！"
CLEAN_GENERAL = "本品采用优质不锈钢工艺，做工精细，支持七天无理由退货。"
CLEAN_JADE = "这是天然翡翠A货吊坠，配有鉴定证书，支持复检，喜欢可在直播间下单。"


# ---------- 核心判定 ----------
def test_high_risk_detected():
    r = engine.detect(HIGH, "jadeite", "douyin")
    assert r["risk_level"] == "high" and r["clean"] is False and r["count"] >= 5
    cats = {h["category"] for h in r["hits"]}
    assert {"绝对化用语", "迷信/伪科学功效", "升值/投资承诺",
            "站外导流/违规交易", "虚假/误导宣传"} <= cats
    assert all(h["index"] >= 0 for h in r["hits"])


def test_clean_general():
    r = engine.detect(CLEAN_GENERAL, "general", "taobao")
    assert r["risk_level"] == "clean" and r["clean"] is True and r["count"] == 0


def test_jadeite_compliant_is_low_only():
    r = engine.detect(CLEAN_JADE, "jadeite", "douyin")
    assert r["risk_level"] == "low"
    assert all(h["severity"] == "low" for h in r["hits"])


# ---------- shim 同一性（向后兼容）----------
def test_shim_reexports_same_engine():
    assert server.detect is engine.detect
    assert server.scan_batch is engine.scan_batch
    assert server.suggest_rewrite is engine.suggest_rewrite
    assert server.get_rules is engine.get_rules
    assert server.SEV_ORDER["high"] == 3


# ---------- 批量聚合 ----------
def test_scan_batch_aggregation():
    msgs = [
        {"speaker": "主播", "text": "欢迎来到直播间。"},
        {"speaker": "主播", "text": HIGH},
        "这款是冰种手镯，带证书。",
    ]
    r = engine.scan_batch(msgs, "jadeite", "douyin")
    assert r["segments"] == 3 and r["overall_risk"] == "high"
    assert r["flagged_segments"] >= 2 and r["high_risk_hits"] >= 1


# ---------- 行业隔离 ----------
def test_industry_isolation():
    assert engine.detect("冰种手镯肉质细腻", "general", "douyin")["risk_level"] == "clean"
    assert engine.detect("冰种手镯肉质细腻", "jadeite", "douyin")["risk_level"] == "low"


# ---------- 改写 ----------
def test_suggest_rewrite_a_goods():
    r = engine.suggest_rewrite(CLEAN_JADE, "jadeite", "douyin")
    pair = next(p for p in r["replacements"] if "A货" in p["from"])
    assert "证书" in pair["to"] and "复检" in pair["to"]


# ---------- 等长归一化（B4 第一批）----------
def test_normalize_is_length_preserving():
    for s in ["１００％ Ｖｘ：ａｂｃ１２３", "中文不变化ABC", "全角空格　与　标点！", "😀🎉"]:
        assert len(normalize_text(s)) == len(s)
    assert normalize_text("１００％ Ｖｘ") == "100% vx"


def test_fullwidth_contact_variant_is_high():
    # 句中不含任何中文高危词，只有全角 vx 号；归一化前漏报，归一化后必须 high
    r = engine.detect("想要优惠的加 ｖｘ：ａｂｃ１２３４５ 咨询。", "general", "douyin")
    assert r["risk_level"] == "high"
    assert any(h["category"] == "站外导流/违规交易" for h in r["hits"])


def test_fullwidth_percent_variant_is_high():
    r = engine.detect("这款吊坠含金量１００％，其余为合金。", "general", "douyin")
    assert r["risk_level"] == "high"
    assert any(h["category"] == "绝对化用语" for h in r["hits"])


# ---------- A6 泛化最高级正则回归 ----------
@pytest.mark.parametrize("text", ["这款最便宜", "这样买最划算", "技术最先进", "体验最好"])
def test_superlative_multiword_pattern(text):
    r = engine.detect(text, "general", "douyin")
    assert any(h["category"] == "泛化最高级" for h in r["hits"])
    assert r["risk_level"] in ("medium", "high")


def test_superlative_not_overtrigger_without_zui():
    r = engine.detect("性价比很高，质量不错，做工精细。", "general", "douyin")
    assert not any(h["category"] == "泛化最高级" for h in r["hits"])
    assert r["risk_level"] == "clean"


# ---------- 入参校验（B3）----------
def test_invalid_context_raises():
    with pytest.raises(ValueError):
        engine.detect("干净话", industry="illegal", platform="douyin")
    with pytest.raises(ValueError):
        engine.detect("干净话", industry="general", platform="wechat")
    with pytest.raises(ValueError):
        engine.get_rules("jadeite", "unknown_platform")


# ---------- 边界输入（B10）----------
@pytest.mark.parametrize("text", ["", None])
def test_empty_and_none_clean(text):
    assert engine.detect(text, "general", "douyin")["risk_level"] == "clean"


def test_boundary_inputs_do_not_crash():
    assert engine.detect("好" * 100000 + "国家级", "general", "douyin")["risk_level"] == "high"
    assert engine.detect("😀😀🎉🎉", "general", "douyin")["risk_level"] == "clean"
    assert engine.detect(
        "This is a normal stainless steel cup.", "general", "douyin")["risk_level"] == "clean"
    malformed = [{"speaker": "主播"}, "我是一句纯字符串消息", {"text": "保真"}, {}]
    r = engine.scan_batch(malformed, "general", "douyin")
    assert r["segments"] == 4


# ---------- 规则库加载 ----------
def test_rules_store_counts():
    m = rules_store.meta()
    # 核心包规则：v1.4（导流词扩充），14 规则 / 16 替换
    assert m["version"] == "v1.4"
    assert m["core_rule_count"] == 14
    assert m["core_replacement_count"] == 16
    # 聚合视图 = 核心 + 全部行业插件
    pkgs = {p["package"]: p for p in m["packages"]}
    assert set(pkgs) == {"food", "cosmetics"}
    extra_rules = sum(p["rule_count"] for p in m["packages"])
    extra_repl = sum(p["replacement_count"] for p in m["packages"])
    assert extra_repl == 16  # 食品/化妆品两个包文件内各 8 条替换
    assert len(rules_store.all_rules()) == 14 + extra_rules
    # 替换表按词聚合去重：两包共用“无副作用”同一条中性替换，全局 31（16+8+8-1）
    assert len(rules_store.replacements()) == m["replacement_count"] == 31
    # 通用行业不应激活翡翠专属规则
    cats_general = {r["category"] for r in rules_store.active_rules("general", "taobao")}
    assert "翡翠-术语提示" not in cats_general
    cats_jade = {r["category"] for r in rules_store.active_rules("jadeite", "douyin")}
    assert "翡翠-术语提示" in cats_jade
    # 行业插件互不串扰
    scopes_jade = {r["scope"] for r in rules_store.active_rules("jadeite", "douyin")}
    assert "industry:food" not in scopes_jade and "industry:cosmetics" not in scopes_jade
    assert any(r["scope"] == "industry:food" for r in rules_store.active_rules("food", "douyin"))


# ---------- stdio 入口（装了 mcp 才测）----------
def test_stdio_server_instantiates():
    pytest.importorskip("mcp")
    from lcg import server_stdio
    assert getattr(server_stdio.mcp, "name", None) == "livestream-compliance-guard"
    assert callable(server_stdio.run)


# ---------- B5 “第一”序数消歧 ----------
def test_ordinal_suffix_helper():
    from lcg.models import is_ordinal_first
    assert is_ordinal_first(normalize_text("第一步"), 2) is True
    assert is_ordinal_first(normalize_text("第一产业"), 2) is True
    assert is_ordinal_first(normalize_text("第一，"), 2) is False
    assert is_ordinal_first(normalize_text("第一名"), 2) is False


def test_ordinal_usage_is_clean_or_low():
    r = engine.detect("这是本店第一款上架的保温杯，第一步先清洗内胆，第一遍用温水冲洗。",
                      "general", "taobao")
    assert r["risk_level"] == "clean"
    r2 = engine.detect("这是我们店第一期上新，第一件是冰种福瓜吊坠，配证书支持复检。",
                       "jadeite", "douyin")
    assert r2["risk_level"] == "low"
    assert not any(h["category"] == "绝对化用语" for h in r2["hits"])


@pytest.mark.parametrize("text", ["我们技术行业第一", "全网销量第一", "品质第一名", "全国第一"])
def test_ranking_first_still_high(text):
    r = engine.detect(text, "general", "douyin")
    assert r["risk_level"] == "high"
    assert any(h["category"] == "绝对化用语" for h in r["hits"])


# ---------- B7 改写后再扫描闭环 ----------
def test_rewrite_closed_loop_removes_risk():
    r = engine.suggest_rewrite(HIGH, "jadeite", "douyin")
    assert r["rewritten"] and r["rewritten"] != HIGH
    assert "rewritten_risk" in r and "rewritten_clean" in r
    assert r["rewritten_risk"] == "clean"
    assert r["rewritten_clean"] is True


def test_rewrite_clean_text_unchanged():
    r = engine.suggest_rewrite(CLEAN_GENERAL, "general", "taobao")
    assert r["rewritten"] == CLEAN_GENERAL
    assert r["rewritten_clean"] is True
