# -*- coding: utf-8 -*-
"""反馈闭环：提交/读回/CSV 导出/类型校验/损坏行容错。"""
import csv

import pytest

from lcg import feedback


def test_submit_and_load_roundtrip(tmp_path):
    p = tmp_path / "feedback.jsonl"
    ok = feedback.submit(
        text="这款精华帮助祛痘控油，温和不刺激。", industry="cosmetics",
        platform="douyin", reported_risk="medium", feedback="false_positive",
        note="合规妆效被误报", category="化妆品-医疗作用宣称", path=str(p))
    assert ok is True
    rows = feedback.load(str(p))
    assert len(rows) == 1
    row = rows[0]
    assert row["feedback"] == "false_positive"
    assert row["reported_risk"] == "medium"
    assert row["industry"] == "cosmetics"
    assert row["text"].startswith("这款精华")


def test_submit_disabled_without_path(monkeypatch):
    monkeypatch.delenv("LCG_FEEDBACK_LOG", raising=False)
    assert feedback.submit(text="x", industry="general", platform="douyin",
                           reported_risk="clean", feedback="review") is False


def test_invalid_feedback_type_raises(tmp_path):
    with pytest.raises(ValueError):
        feedback.submit(text="x", industry="general", platform="douyin",
                        reported_risk="clean", feedback="wrong_type",
                        path=str(tmp_path / "f.jsonl"))


def test_export_csv(tmp_path):
    p = tmp_path / "feedback.jsonl"
    feedback.submit(text="话术一", industry="food", platform="douyin",
                    reported_risk="high", feedback="false_negative", path=str(p))
    feedback.submit(text="话术二", industry="general", platform="taobao",
                    reported_risk="clean", feedback="review", path=str(p))
    out = tmp_path / "feedback.csv"
    n = feedback.export_csv(feedback.load(str(p)), str(out))
    assert n == 2
    with out.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 2
    assert rows[0]["feedback"] == "false_negative"
    assert rows[1]["reported_risk"] == "clean"


def test_load_skips_corrupt_lines(tmp_path):
    p = tmp_path / "feedback.jsonl"
    p.write_text('{"feedback":"review"}\n坏行\n{"feedback":"false_positive"}\n',
                 encoding="utf-8")
    assert len(feedback.load(str(p))) == 2
