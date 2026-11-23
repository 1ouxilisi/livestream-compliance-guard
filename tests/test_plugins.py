# -*- coding: utf-8 -*-
"""lcg 行业插件包测试（M5）。

覆盖：核心包+插件包聚合与自洽、行业隔离、食品/化妆品违规召回，
以及合规话术（法定声明、备案保健功能、合规妆效/特证、敏感肌、祛痘）零误报。
"""
import pytest

from lcg import engine, rules_store


# ---------- 包结构 / 聚合 / 来源 ----------
def test_packages_loaded():
    m = rules_store.meta()
    pkgs = {p["package"]: p for p in m["packages"]}
    assert set(pkgs) == {"food", "cosmetics"}
    for name in ("food", "cosmetics"):
        assert pkgs[name]["industry"] == name
        assert pkgs[name]["rule_count"] == 3
        assert pkgs[name]["replacement_count"] == 8
    assert m["rule_count"] == 14 + sum(p["rule_count"] for p in m["packages"])
    # 跨包共用“无副作用”一条替换，聚合去重后全局 31（16+8+8-1）
    assert m["replacement_count"] == len(rules_store.replacements()) == 31


def test_plugin_files_self_consistent():
    assert rules_store.plugin_paths(), "应至少加载 food/cosmetics 两个插件包"
    for path, data in rules_store.plugin_payloads():
        m = data["meta"]
        assert len(data["rules"]) == m["rule_count"]
        assert len(data["replacements"]) == m["replacement_count"]
        assert all(r["scope"] == f"industry:{m['industry']}" for r in data["rules"])
        # 每条规则必须挂法条，每个来源必须有入口 URL，禁止编造深链
        assert all(r["law"] for r in data["rules"])
        assert m.get("sources") and all(s.get("url") for s in m["sources"])


def test_industry_isolation():
    food_scopes = {r["scope"] for r in rules_store.active_rules("food", "douyin")}
    cos_scopes = {r["scope"] for r in rules_store.active_rules("cosmetics", "douyin")}
    jade_scopes = {r["scope"] for r in rules_store.active_rules("jadeite", "douyin")}
    assert "industry:food" in food_scopes and "industry:cosmetics" not in food_scopes
    assert "industry:cosmetics" in cos_scopes and "industry:food" not in cos_scopes
    assert "industry:food" not in jade_scopes and "industry:cosmetics" not in jade_scopes


# ---------- 食品：合规放行 ----------
@pytest.mark.parametrize("text", [
    "这款每日坚果配料干净，口感酥脆，新鲜日期发货，独立小包装方便携带。",
    "蓝帽认证保健食品，保健功能为增强免疫力，每日两粒温水送服，本品不能代替药物。",
    "农家土蜂蜜，冲水香甜，产地直发，拌饭抹面包都合适。",
    "这款酸奶生牛乳发酵，酸甜适中，冷藏口感更好，饭后喝一杯很解腻。",
])
def test_food_benign_clean(text):
    assert engine.detect(text, "food", "douyin")["risk_level"] == "clean"


def test_food_statutory_disclaimer_not_flagged():
    r = engine.detect("保健食品，每日两粒，本品不能代替药物。", "food", "douyin")
    assert r["risk_level"] == "clean"
    assert not any(("代替药物" in h["match"]) or ("替代药物" in h["match"]) for h in r["hits"])


# ---------- 食品：违规召回 ----------
@pytest.mark.parametrize("text", [
    "坚持喝三个月，高血压都降了，糖尿病也稳了，比吃药还管用！",
    "这个偏方食品包治百病，消炎止咳，吃了就能根治老胃病，无效退款！",
    "医生都在推荐的保健品，患者反馈吃了肿瘤小了，安全无毒副作用，可以替代药物！",
    "纯天然提取物，没有任何副作用，100%安全，老人小孩必须天天吃，不吃身体就垮了。",
])
def test_food_adversarial_high(text):
    assert engine.detect(text, "food", "douyin")["risk_level"] == "high"


def test_food_disease_category_hit():
    r = engine.detect("高血压都降了，比吃药还管用！", "food", "douyin")
    assert any(h["category"] == "食品-疾病治疗宣称" for h in r["hits"])


def test_food_safety_assurance_and_endorsement_hit():
    r = engine.detect("医生都在推荐，没有任何副作用，不吃身体就垮了。", "food", "douyin")
    cats = {h["category"] for h in r["hits"]}
    assert "食品-功效安全性断言保证" in cats
    assert "食品-医疗代言与健康恐惧" in cats


# ---------- 化妆品：合规放行 ----------
@pytest.mark.parametrize("text", [
    "这款面霜主打玻尿酸保湿补水，质地清爽不黏腻，干皮上脸很滋润。",
    "防晒霜SPF50+，持有美白防晒双特证，出门前15分钟涂抹，补涂更安心。",
    "氨基酸洁面温和清洁，泡沫绵密，洗完不紧绷，适合敏感肌日常清洁。",
    "这款精华含烟酰胺，长期使用帮助提亮肤色，让妆容更服帖。",
])
def test_cosmetics_benign_clean(text):
    assert engine.detect(text, "cosmetics", "douyin")["risk_level"] == "clean"


def test_acne_compliant_but_treat_is_medical():
    # 合规“祛痘/控油/温和”放行；“治疗痘痘/消除痤疮/根治”属医疗作用
    ok = engine.detect("这款精华帮助祛痘控油，温和不刺激。", "cosmetics", "douyin")
    assert ok["risk_level"] in ("clean", "low", "medium")
    bad = engine.detect("治疗痘痘，消除痤疮，七天根治。", "cosmetics", "douyin")
    assert bad["risk_level"] == "high"


def test_repair_barrier_compliant_but_scar_medical():
    # “修护/修复屏障”合规，“修复疤痕/红血丝”属医疗
    ok = engine.detect("修护肌肤屏障，舒缓泛红，提升耐受。", "cosmetics", "douyin")
    assert ok["risk_level"] in ("clean", "low", "medium")
    bad = engine.detect("修复红血丝和疤痕，临床治愈激素脸。", "cosmetics", "douyin")
    assert bad["risk_level"] == "high"


# ---------- 化妆品：违规召回 ----------
@pytest.mark.parametrize("text", [
    "这款药妆面霜消炎抗敏，专治湿疹皮炎，七天根治痘痘，比皮肤科药膏还管用！",
    "医学护肤精华，纯天然无副作用，一次祛斑永不反弹，3天美白两个度，无效退款！",
    "医用级面膜，临床治愈激素脸，修复红血丝和疤痕，用了立刻见效，100%不过敏。",
])
def test_cosmetics_medical_high(text):
    assert engine.detect(text, "cosmetics", "douyin")["risk_level"] == "high"


def test_cosmetics_medical_category_hit():
    r = engine.detect("这款药妆专治湿疹，修复疤痕。", "cosmetics", "douyin")
    assert any(h["category"] == "化妆品-医疗作用宣称" for h in r["hits"])


def test_cosmetics_disparagement_medium_not_high():
    r = engine.detect("这款精华吊打同类大牌，销量冠军，秒杀某小黑瓶，效果甩它们几条街。",
                      "cosmetics", "douyin")
    assert r["risk_level"] == "medium"
    assert any("贬低" in h["category"] for h in r["hits"])
