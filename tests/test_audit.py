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


def _result(industry="general", action="detect", risk="high"):
    return {**RESULT, "industry": industry, "platform": "douyin",
            "risk_level": risk, "action": action}


def test_audit_identity_fields_jsonl(tmp_path):
    path = tmp_path / "audit.jsonl"
    audit.record(action="detect", result=RESULT, text=TEXT, path=str(path),
                 operator="u-1", key_id="sk-aa11")
    events = audit.load_events(str(path))
    assert events[0]["operator"] == "u-1"
    assert events[0]["key_id"] == "sk-aa11"


def test_audit_query_filters(tmp_path):
    path = tmp_path / "audit.db"
    audit.record(action="detect", result=_result("food", "detect", "high"),
                 text=TEXT, path=str(path), operator="u-1", key_id="sk-1")
    audit.record(action="rewrite", result=_result("food", "rewrite", "medium"),
                 text=TEXT, path=str(path), operator="u-2", key_id="sk-2")
    audit.record(action="detect", result=_result("cosmetics", "detect", "low"),
                 text=TEXT, path=str(path), operator="u-1", key_id="sk-3")

    assert len(audit.query(str(path))) == 3
    assert len(audit.query(str(path), industry="food")) == 2
    assert len(audit.query(str(path), action="detect")) == 2
    assert len(audit.query(str(path), risk_level="medium")) == 1
    assert len(audit.query(str(path), operator="u-1")) == 2
    assert len(audit.query(str(path), key_id="sk-2")) == 1
    assert len(audit.query(str(path), limit=2)) == 2
    assert [e["key_id"] for e in audit.query(str(path), limit=2)] == ["sk-2", "sk-3"]


def test_audit_query_since_filter(tmp_path):
    path = tmp_path / "audit.jsonl"
    audit.record(action="detect", result=RESULT, text=TEXT, path=str(path))
    events = audit.load_events(str(path))
    ts = events[0]["ts"]
    assert audit.query(str(path), since=ts) == events
    assert audit.query(str(path), since=ts + "Z") == []


def test_audit_sqlite_legacy_columns_backfilled(tmp_path):
    from lcg import ledger

    db = str(tmp_path / "legacy.db")
    conn = ledger.connect(db)
    # 旧 schema：无 operator / key_id 列
    conn.execute(
        "CREATE TABLE audit_events ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, "
        "action TEXT NOT NULL, industry TEXT NOT NULL DEFAULT '', "
        "platform TEXT NOT NULL DEFAULT '', risk_level TEXT NOT NULL DEFAULT '', "
        "mode TEXT NOT NULL DEFAULT 'rule', count INTEGER NOT NULL DEFAULT 0, "
        "hits TEXT NOT NULL DEFAULT '[]', llm TEXT NOT NULL DEFAULT '{}', "
        "text_len INTEGER, redacted INTEGER NOT NULL DEFAULT 0, text TEXT)"
    )
    conn.commit()
    conn.close()

    audit.record(action="detect", result=RESULT, text=TEXT, path=db,
                 operator="u-9", key_id="sk-9")
    events = audit.load_events(db)
    assert events[0]["operator"] == "u-9"
    assert events[0]["key_id"] == "sk-9"
