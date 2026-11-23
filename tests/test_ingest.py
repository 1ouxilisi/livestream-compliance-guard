# -*- coding: utf-8 -*-
"""输入适配：dict / tuple / str 异构片段归一到 scan_batch 契约。"""
from lcg import ingest


def test_normalizes_mixed_shapes():
    items = [
        {"text": "第一条"},
        {"speaker": "主播A", "content": "第二条", "start": 1.5},
        ("主播B", "第三条"),
        "第四条",
        "",
        None,
    ]
    out = ingest.normalize_transcript(items)
    assert len(out) == 4
    assert out[0] == {"seq": 0, "speaker": "", "text": "第一条"}
    assert out[1]["speaker"] == "主播A"
    assert out[1]["text"] == "第二条"
    assert out[1]["start"] == 1.5
    assert out[2] == {"seq": 2, "speaker": "主播B", "text": "第三条"}
    assert out[3] == {"seq": 3, "speaker": "", "text": "第四条"}


def test_seq_renumbered_when_missing():
    out = ingest.normalize_transcript(["a", "b", "c"])
    assert [r["seq"] for r in out] == [0, 1, 2]


def test_preserves_explicit_seq():
    out = ingest.normalize_transcript([{"seq": 9, "text": "x"}, {"text": "y"}])
    assert out[0]["seq"] == 9
    assert out[1]["seq"] == 1


def test_empty_inputs():
    assert ingest.normalize_transcript(None) == []
    assert ingest.normalize_transcript([]) == []
    assert ingest.normalize_transcript(["   ", ""]) == []


def test_single_non_list_item():
    out = ingest.normalize_transcript("单独一句")
    assert out == [{"seq": 0, "speaker": "", "text": "单独一句"}]


def test_asr_alias_equivalent():
    seg = [{"spk": "S", "utterance": "语音转写文本", "start": 0.2}]
    out = ingest.from_asr_segments(seg)
    assert out[0]["speaker"] == "S"
    assert out[0]["text"] == "语音转写文本"
    assert out[0]["start"] == 0.2
