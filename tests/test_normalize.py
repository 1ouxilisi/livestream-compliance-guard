# -*- coding: utf-8 -*-
"""B4 高级归一化测试：等层繁简映射 + 紧凑层阻断符合并（无 key、纯确定性）。

紧凑层只做“补漏”：把插在违规词中间的空格 / 中点 / emoji 去掉后再匹配，
并保留中文标点与句子边界，因此既抓得住“最 好 / NO·1 / 微❤️abc12345”，
又不会把“最后，好货”跨标点错并成“最好”，也不会把英文 voucher 误判成导流号。
"""
import pytest

from lcg import engine
from lcg.models import normalize_compact, normalize_text


# ---------- 繁简等长 ----------
@pytest.mark.parametrize("trad,simp", [
    ("全網銷量第一", "全网销量第一"),
    ("這絕對是業內最好的", "这绝对是业内最好的"),
    ("養生辟邪 穩賺不賠", "养生辟邪 稳赚不赔"),
])
def test_traditional_to_simplified_length_preserved(trad, simp):
    out = normalize_text(trad)
    assert out == simp and len(out) == len(trad)


def test_traditional_absolute_is_high():
    r = engine.detect("這絕對是業內最好的一款，全網銷量第一，百分百權威認證！",
                      "general", "douyin")
    assert r["risk_level"] == "high"
    assert "绝对化用语" in {h["category"] for h in r["hits"]}


# ---------- 紧凑层：下标映射 ----------
def test_compact_drops_space_and_maps_index():
    c, idx = normalize_compact("最 好")
    assert c == "最好" and idx == [0, 2]


def test_compact_drops_emoji_but_keeps_chinese_punct():
    c, _ = normalize_compact("最后，好货")
    assert c == "最后,好货"          # 中文逗号等长转半角但保留，不跨句合并
    assert "最好" not in c
    c2, _ = normalize_compact("微❤️ a1")
    assert c2.startswith("微a1")     # emoji 与空格剔除


# ---------- 紧凑层：阻断变体规则可抓 ----------
def test_space_splitting_word_is_high():
    r = engine.detect("这是最 好 的一款，没有之一。", "general", "douyin")
    assert r["risk_level"] == "high"
    h = next(x for x in r["hits"] if x["category"] == "绝对化用语")
    assert h["match"] == "最 好" and h["index"] >= 0


def test_space_splitting_pattern_superlative():
    r = engine.detect("这款最 便宜，别家没有。", "general", "douyin")
    assert any(x["category"] == "泛化最高级" for x in r["hits"])
    assert r["risk_level"] in ("medium", "high")


def test_middle_dot_no1_high():
    r = engine.detect("我们家这款是业内 NO·1 的存在", "general", "douyin")
    assert r["risk_level"] == "high"
    assert any(x["category"] == "绝对化用语" for x in r["hits"])


def test_emoji_blocked_contact_high():
    r = engine.detect("想领资料的宝子，看我主页 微❤️ abc12345 哈",
                      "general", "douyin")
    assert r["risk_level"] == "high"
    assert any("导流" in x["category"] for x in r["hits"])


# ---------- 防误报 ----------
def test_chinese_comma_insertion_not_merged():
    # 中文标点插字阻断交给 LLM；规则紧凑层不得跨中文标点错并
    r = engine.detect("最后，好货不多，喜欢可以下单。", "general", "douyin")
    assert r["risk_level"] == "clean"
    assert not any(x["category"] == "泛化最高级" for x in r["hits"])


def test_english_v_words_no_false_contact():
    r = engine.detect("we provide a voucher service team today",
                      "general", "douyin")
    assert r["risk_level"] == "clean"
    assert not any("导流" in x["category"] for x in r["hits"])


def test_compact_does_not_double_count():
    # 全角 vx 号等长层已命中，紧凑层不得对同一区间重复计数
    r = engine.detect("想要优惠的加 ｖｘ：ａｂｃ１２３４５ 咨询。", "general", "douyin")
    contact = [x for x in r["hits"] if "导流" in x["category"]]
    assert len(contact) == 1


# ---------- 紧凑命中参与改写闭环 ----------
def test_compact_hit_rewrite_closed_loop():
    r = engine.suggest_rewrite("这是最 好 的一款。", "general", "douyin")
    assert r["rewritten_clean"] is True
    assert "最 好" not in r["rewritten"]
