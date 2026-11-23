# -*- coding: utf-8 -*-
"""
lcg.engine —— 纯检测逻辑（不依赖传输方式；规则来自 rules_store，归一化来自 models）。

对外四个纯函数（与 MCP 工具一一对应）：
  detect(text, industry, platform)           -> 单段检测
  scan_batch(messages, industry, platform)   -> 整场直播逐句聚合
  suggest_rewrite(text, industry, platform)  -> 命中词安全替代
  get_rules(industry, platform)              -> 生效规则词库

输出字段与 v1（根 server.py）保持完全一致，不得擅改（契约见 docs/TOOL_SCHEMA.md）。
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any, Dict, List

from . import rules_store
from .models import SEV_ORDER, is_ordinal_first, normalize_compact, normalize_text, validate_context

_DISCLAIMER = "仅为合规风险提示，不构成法律意见，以监管机关与平台最新规则为准。"


@dataclass
class Hit:
    category: str
    severity: str
    law: str
    match: str
    suggestion: str
    index: int = -1
    source: str = "rule"  # rule=规则硬底线命中；llm=LLM 语义层补充命中（见 lcg.pipeline）


@lru_cache(maxsize=1)
def _replacement_index() -> Dict[str, str]:
    """替换建议按「归一化后的命中词」建索引，兼容全角/大小写变体命中。"""
    return {normalize_text(k): v for k, v in rules_store.replacements().items()}


def detect(text: str, industry: str = "jadeite", platform: str = "douyin") -> Dict[str, Any]:
    """对单段文本做规则检测，返回结构化结果。"""
    validate_context(industry, platform)
    orig = text if isinstance(text, str) else ""
    norm = normalize_text(orig)
    compact, cidx = normalize_compact(orig)

    hits: List[Hit] = []
    seen = set()
    occupied: List[tuple] = []  # 已命中原文区间，供紧凑层去重；等长层内部计数行为不变

    def _overlaps(s: int, e: int) -> bool:
        return any(s < re_ and rs < e for rs, re_ in occupied)

    def _take_compact(category, severity, law, tip, s: int, e: int,
                      kind: str, token: str) -> bool:
        """紧凑层补漏：与既有命中区间重叠或同键重复则不再追加（不改变等长层结果）。"""
        key = (category, kind, token, s)
        if key in seen or _overlaps(s, e):
            return False
        seen.add(key)
        occupied.append((s, e))
        hits.append(Hit(category, severity, law, orig[s:e], tip, s))
        return True

    for r in rules_store.active_rules(industry, platform):
        category = r["category"]
        severity = r["severity"]
        law = r.get("law", "")
        tip = r.get("tip", "")

        # —— 等长层：关键词包含匹配（命中片段取原文等长区间）——
        for w in r.get("words", []):
            nw = normalize_text(w)
            if not nw:
                continue
            start = norm.find(nw)
            while start != -1:
                # “第一”序数消歧：第一步/第一款/第一产业等次序用法不判排名绝对化
                if w == "第一" and is_ordinal_first(norm, start + len(nw)):
                    start = norm.find(nw, start + len(nw))
                    continue
                key = (category, "w", nw, start)
                if key not in seen:
                    seen.add(key)
                    occupied.append((start, start + len(nw)))
                    hits.append(Hit(category, severity, law,
                                   orig[start:start + len(nw)], tip, start))
                start = norm.find(nw, start + len(nw))

        # —— 等长层：正则匹配 ——
        for p in r.get("patterns", []):
            for m in re.finditer(p, norm, flags=re.IGNORECASE):
                s, e = m.start(), m.end()
                key = (category, "p", m.group(0), s)
                if key not in seen:
                    seen.add(key)
                    occupied.append((s, e))
                    hits.append(Hit(category, severity, law, orig[s:e], tip, s))

        # —— 紧凑层：拦插空格/符号/emoji 阻断的关键词（仅补等长层漏掉的）——
        for w in r.get("words", []):
            cw = normalize_compact(w)[0]
            if not cw:
                continue
            cstart = compact.find(cw)
            while cstart != -1:
                cend = cstart + len(cw)
                # 紧凑文本上同样做“第一”序数消歧（第 一 步 合并后仍是次序）
                if not (w == "第一" and is_ordinal_first(compact, cend)):
                    s = cidx[cstart]
                    e = cidx[min(cend - 1, len(cidx) - 1)] + 1
                    _take_compact(category, severity, law, tip, s, e, "cw", cw)
                cstart = compact.find(cw, cend)

        # —— 紧凑层：正则（优先 patterns_compact 严格版，缺省回退 patterns）——
        for p in (r.get("patterns_compact") or r.get("patterns", [])):
            for m in re.finditer(p, compact, flags=re.IGNORECASE):
                cs, ce = m.start(), m.end()
                if ce <= cs:
                    continue
                s = cidx[cs]
                e = cidx[min(ce - 1, len(cidx) - 1)] + 1
                _take_compact(category, severity, law, tip, s, e, "cp", m.group(0))

    level = "clean"
    for h in hits:
        if SEV_ORDER[h.severity] > SEV_ORDER[level]:
            level = h.severity

    return {
        "risk_level": level,
        "clean": level == "clean",
        "count": len(hits),
        "hits": [asdict(h) for h in sorted(hits, key=lambda x: -SEV_ORDER[x.severity])],
        "industry": industry,
        "platform": platform,
        "disclaimer": _DISCLAIMER,
    }


def scan_batch(messages: List[Dict[str, Any]], industry: str = "jadeite",
               platform: str = "douyin") -> Dict[str, Any]:
    """messages: [{"speaker": "主播", "text": "..."}]，对直播流逐句检测并聚合。"""
    validate_context(industry, platform)
    results = []
    high = 0
    flagged = 0
    for i, msg in enumerate(messages):
        if isinstance(msg, dict):
            txt = msg.get("text", "")
            speaker = msg.get("speaker", "")
        else:
            txt, speaker = str(msg), ""
        res = detect(txt, industry, platform)
        if not res["clean"]:
            flagged += 1
            high += sum(1 for h in res["hits"] if h["severity"] == "high")
        results.append({"seq": i, "speaker": speaker, "text": txt,
                        "risk_level": res["risk_level"], "hits": res["hits"]})
    overall = "clean"
    if any(r["risk_level"] == "high" for r in results):
        overall = "high"
    elif any(r["risk_level"] == "medium" for r in results):
        overall = "medium"
    elif any(r["risk_level"] == "low" for r in results):
        overall = "low"
    return {"overall_risk": overall, "segments": len(messages),
            "flagged_segments": flagged, "high_risk_hits": high, "results": results}


def _replacement_for(match: str) -> str:
    """命中词对应的安全替换；兼容被空格/符号/emoji 阻断的紧凑命中（如“最 好”按“最好”替换）。"""
    index = _replacement_index()
    default = "（建议删除或改为客观、可举证表述）"
    return (index.get(normalize_text(match))
            or index.get(normalize_compact(match)[0])
            or default)


def _apply_replacements(orig: str, hits: List[Dict[str, Any]]) -> str:
    """按命中区间把原文替换为安全表达，拼出改写全文（B7 闭环用）。

    高严重度、长跨度命中优先占用区间，重叠区间不重复替换，未命中文字原样保留。
    """
    cands = []
    for h in hits:
        s = h["index"]
        e = s + len(h["match"])
        if s < 0:
            continue
        t = _replacement_for(h["match"])
        cands.append((s, e, t, h["severity"]))
    # 高严重度优先、长跨度优先、位置靠前优先
    cands.sort(key=lambda x: (-SEV_ORDER[x[3]], -(x[1] - x[0]), x[0]))

    occupied = [False] * len(orig)
    chosen = []
    for s, e, t, _sev in cands:
        if e > len(orig) or any(occupied[s:e]):
            continue
        chosen.append((s, e, t))
        for i in range(s, e):
            occupied[i] = True
    chosen.sort()

    parts: List[str] = []
    last = 0
    for s, e, t in chosen:
        parts.append(orig[last:s])
        parts.append(t)
        last = e
    parts.append(orig[last:])
    return "".join(parts)


def suggest_rewrite(text: str, industry: str = "jadeite",
                    platform: str = "douyin") -> Dict[str, Any]:
    """给出命中词替换建议、改写全文，并对改写结果复检（B7 闭环）。

    LLM 增强模式可在此基础上生成更自然的整句合规话术。
    """
    res = detect(text, industry, platform)
    replacements = []
    for h in res["hits"]:
        m = h["match"]
        replacements.append({"from": m, "to": _replacement_for(m)})
    rewritten = _apply_replacements(text if isinstance(text, str) else "", res["hits"])
    recheck = detect(rewritten, industry, platform)
    return {"original": text, "risk_level": res["risk_level"],
            "replacements": replacements,
            "rewritten": rewritten,
            "rewritten_risk": recheck["risk_level"],
            "rewritten_clean": recheck["clean"],
            "note": "规则替换为参考；改写全文已做规则复检，正式使用前仍建议人工复核，"
                    "完整话术改写可在 LLM 增强模式下生成。"}


def get_rules(industry: str = "jadeite", platform: str = "douyin") -> Dict[str, Any]:
    """返回当前生效规则（分类、严重度、法规、词条），供客户端展示与审计。"""
    validate_context(industry, platform)
    return {"industry": industry, "platform": platform,
            "rules": [{"category": r["category"], "severity": r["severity"],
                       "law": r.get("law", ""), "words": r.get("words", []),
                       "patterns": r.get("patterns", []),
                       "patterns_compact": r.get("patterns_compact", [])}
                      for r in rules_store.active_rules(industry, platform)]}
