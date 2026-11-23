# -*- coding: utf-8 -*-
"""
lcg.ingest —— 外部文本片段到直播检测契约的适配层（零第三方依赖）。

边界说明：本服务**不做语音识别（ASR）也不做图像文字识别（OCR）**；它只消费
上游 ASR / OCR / 字幕文件 / 表格已经转写好的**文本片段**，把形态各异的输入归一
为 ``engine.scan_batch`` 认可的契约：``[{"seq", "speaker", "text"}, ...]``。

兼容的元素形态：
  · dict：``{"text"|"content"|"utterance", "speaker"|"spk"|"author", 可选 "seq"/"start"}``
  · list / tuple：``[speaker, text]`` 或 ``[text]``
  · str：纯文本片段（speaker 留空）

空文本片段会被丢弃；``seq`` 缺省时按输入顺序从 0 重新编号。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

_TEXT_KEYS = ("text", "content", "utterance", "transcript")
_SPEAKER_KEYS = ("speaker", "spk", "author", "name")


def _first(d: Dict[str, Any], keys: Sequence[str]) -> str:
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _coerce(item: Any, index: int) -> Optional[Dict[str, Any]]:
    if item is None:
        return None

    if isinstance(item, str):
        text = item.strip()
        return {"seq": index, "speaker": "", "text": text} if text else None

    if isinstance(item, (list, tuple)):
        if len(item) >= 2:
            speaker, text = str(item[0]).strip(), str(item[1]).strip()
        elif len(item) == 1:
            speaker, text = "", str(item[0]).strip()
        else:
            return None
        return {"seq": index, "speaker": speaker, "text": text} if text else None

    if isinstance(item, dict):
        text = _first(item, _TEXT_KEYS)
        if not text:
            return None
        out: Dict[str, Any] = {
            "seq": item.get("seq", index),
            "speaker": _first(item, _SPEAKER_KEYS),
            "text": text,
        }
        if item.get("start") is not None:
            out["start"] = item["start"]
        return out

    # 其它类型（数字等）按字符串兜底，仍为空则丢弃
    text = str(item).strip()
    return {"seq": index, "speaker": "", "text": text} if text else None


def normalize_transcript(items: Any) -> List[Dict[str, Any]]:
    """把异构片段列表归一为 scan_batch 契约；返回新列表，不改原输入。"""
    if items is None:
        return []
    if not isinstance(items, (list, tuple)):
        items = [items]
    out: List[Dict[str, Any]] = []
    for i, item in enumerate(items):
        coerced = _coerce(item, i)
        if coerced is not None:
            out.append(coerced)
    # 缺省 seq 统一重排（保留显式传入的 seq 时不覆盖）
    for i, row in enumerate(out):
        if "seq" not in row or row["seq"] is None:
            row["seq"] = i
    return out


# 语义别名：强调输入来自上游 ASR 片段
def from_asr_segments(segments: Any) -> List[Dict[str, Any]]:
    """适配上游 ASR 输出的说话人片段（等价于 normalize_transcript）。"""
    return normalize_transcript(segments)
