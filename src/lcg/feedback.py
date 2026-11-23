# -*- coding: utf-8 -*-
"""
lcg.feedback —— 误报 / 漏报反馈的本地记录与导出（零第三方依赖，可选启用）。

用途：把人工复核中发现的“误报（false_positive）/漏报（false_negative）/存疑（review）”
沉淀为本地 JSONL，作为规则库迭代与评测集扩充的输入；本模块只负责记录与导出，
不做自动改规则，也不上传。

启用：设置环境变量 ``LCG_FEEDBACK_LOG`` 为 JSONL 路径后落盘；未设置时 ``submit``
返回 False（禁用）。测试与脚本可显式传 ``path``。

导出：``export_csv`` 把反馈列表写成 CSV（UTF-8 BOM，便于表格软件打开）。
"""
from __future__ import annotations

import csv
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()

FEEDBACK_TYPES = ("false_positive", "false_negative", "review")
_FP, _FN, _REVIEW = FEEDBACK_TYPES


def _log_path() -> Optional[Path]:
    raw = (os.environ.get("LCG_FEEDBACK_LOG") or "").strip()
    return Path(raw) if raw else None


def submit(*, text: str, industry: str, platform: str, reported_risk: str,
           feedback: str, note: str = "", category: str = "",
           path: Optional[str] = None) -> bool:
    """记录一条反馈；反馈类型非法时抛 ValueError，未配置路径返回 False。"""
    if feedback not in FEEDBACK_TYPES:
        raise ValueError(
            f"非法 feedback={feedback!r}，可选：{', '.join(FEEDBACK_TYPES)}")
    target = Path(path) if path else _log_path()
    if target is None:
        return False
    event: Dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "feedback": feedback,
        "industry": industry,
        "platform": platform,
        "reported_risk": reported_risk,
        "category": category,
        "text": text or "",
        "note": note or "",
    }
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with _LOCK, target.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
        return True
    except OSError:
        return False


def load(path: str) -> List[Dict[str, Any]]:
    """读回反馈 JSONL；损坏行跳过。"""
    p = Path(path)
    if not p.is_file():
        return []
    events: List[Dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def export_csv(events: List[Dict[str, Any]], out_path: str) -> int:
    """把反馈列表写成 CSV，返回写出条数。"""
    fields = ["ts", "feedback", "industry", "platform", "reported_risk",
              "category", "text", "note"]
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for ev in events:
            writer.writerow(ev)
    return len(events)
