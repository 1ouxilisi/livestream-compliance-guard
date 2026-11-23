# -*- coding: utf-8 -*-
"""
lcg.audit 审计留痕测试（无网络、无 key，临时目录隔离）。

覆盖：默认关闭不落盘、JSONL 写入与读回、脱敏开关、损坏行跳过、事件字段提炼。
"""
from lcg import audit

RESULT = {
    "industry": "general",
    "platform": "douyin",
    "risk_level": "high",
    "mode": "rules_plus_llm",
    "count": 1,
    "hits": [{"category": "绝对化用语", "severity": "high",
              "source": "rule", "match": "最好"}],
    "llm": {"status": "ok", "model": "fake-model", "cached": False, "total_tokens": 120},
}
TEXT = "这是最好的一款，没有之一。"


def test_record_disabled_without_path(monkeypatch, tmp_path):
    monkeypatch.delenv("LCG_AUDIT_LOG", raising=False)
    assert audit.record(action="detect", result=RESULT, text=TEXT) is False
    assert list(tmp_path.iterdir()) == []


def test_record_writes_jsonl_and_reads_back(tmp_path):
    path = tmp_path / "audit.jsonl"
    ok = audit.record(action="detect", result=RESULT, text=TEXT, path=str(path))
    assert ok is True
    events = audit.load_events(str(path))
    assert len(events) == 1
    ev = events[0]
    assert ev["action"] == "detect"
    assert ev["risk_level"] == "high"
    assert ev["mode"] == "rules_plus_llm"
    assert ev["count"] == 1
    assert ev["hits"][0]["match"] == "最好"
    assert ev["llm"]["total_tokens"] == 120
    assert ev["text"] == TEXT
    assert ev["redacted"] is False


def test_redact_hides_raw_text(tmp_path):
    path = tmp_path / "audit.jsonl"
    audit.record(action="rewrite", result=RESULT, text=TEXT,
                 path=str(path), redact=True)
    ev = audit.load_events(str(path))[0]
    assert "text" not in ev
    assert ev["redacted"] is True
    assert ev["text_len"] == len(TEXT)


def test_load_events_skips_bad_lines(tmp_path):
    path = tmp_path / "audit.jsonl"
    path.write_text('{"action":"detect","risk_level":"high"}\n'
                    '这一行损坏了\n'
                    '{"action":"rewrite","risk_level":"clean"}\n',
                    encoding="utf-8")
    events = audit.load_events(str(path))
    assert len(events) == 2
    assert [e["action"] for e in events] == ["detect", "rewrite"]


def test_build_event_clips_long_match():
    long_match = "最" * 30
    res = {"hits": [{"category": "x", "severity": "high", "match": long_match}],
           "llm": {}}
    ev = audit.build_event(action="detect", result=res, text=TEXT)
    assert len(ev["hits"][0]["match"]) <= audit._MAX_MATCH + 1
    assert ev["hits"][0]["match"].endswith("…")


def test_audit_sqlite_roundtrip(tmp_path):
    db = str(tmp_path / "audit.db")
    assert audit.record(action="detect", result=RESULT, text=TEXT, path=db) is True
    events = audit.load_events(db)
    assert len(events) == 1
    ev = events[0]
    assert ev["action"] == "detect"
    assert ev["risk_level"] == "high"
    assert ev["hits"][0]["match"] == "最好"
    assert ev["llm"]["total_tokens"] == 120
    assert ev["text"] == TEXT


def test_audit_sqlite_redact_roundtrip(tmp_path):
    db = str(tmp_path / "audit.db")
    audit.record(action="rewrite", result=RESULT, text=TEXT,
                 path=db, redact=True)
    ev = audit.load_events(db)[0]
    assert "text" not in ev
    assert ev["redacted"] is True
    assert ev["text_len"] == len(TEXT)


def test_audit_sqlite_persists_across_reopen(tmp_path):
    from lcg import ledger

    db = str(tmp_path / "audit.db")
    audit.record(action="detect", result=RESULT, text=TEXT, path=db)
    ledger.close_all()
    assert len(audit.load_events(db)) == 1
