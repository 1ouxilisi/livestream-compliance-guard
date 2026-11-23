# -*- coding: utf-8 -*-
"""可插拔输入源：协议、静态源、桩源与统一加载。"""
from lcg import sources


def test_list_source_normalizes_items():
    src = sources.ListSource([{"speaker": "A", "text": "第一条"}, "第二条"])
    out = src.fetch()
    assert [r["text"] for r in out] == ["第一条", "第二条"]
    assert out[0]["speaker"] == "A"


def test_list_source_accepts_callable():
    src = sources.ListSource(lambda: [{"text": "由回调产出"}])
    assert src.fetch()[0]["text"] == "由回调产出"


def test_stub_source_add_and_fetch():
    stub = sources.StubSource([{"text": "初始片段"}])
    stub.add({"speaker": "B", "text": "追加片段"})
    out = stub.fetch()
    assert len(out) == 2
    assert out[1]["speaker"] == "B"


def test_load_source_accepts_source_instance():
    src = sources.StubSource([{"text": "桩片段"}])
    out = sources.load_source(src)
    assert out[0]["text"] == "桩片段"


def test_load_source_accepts_plain_list():
    out = sources.load_source(["纯文本片段"])
    assert out == [{"seq": 0, "speaker": "", "text": "纯文本片段"}]


def test_load_source_accepts_callable():
    out = sources.load_source(lambda: [{"text": "回调片段"}])
    assert out[0]["text"] == "回调片段"


def test_load_source_empty():
    assert sources.load_source(None) == []
    assert sources.load_source(sources.StubSource([])) == []


def test_protocol_runtime_checkable():
    assert isinstance(sources.StubSource(), sources.TranscriptSource)
    assert isinstance(sources.ListSource([]), sources.TranscriptSource)
