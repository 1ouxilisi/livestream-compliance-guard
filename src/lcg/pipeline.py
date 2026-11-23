# -*- coding: utf-8 -*-
"""
lcg.pipeline —— 规则硬底线 ＋ LLM 语义层的融合编排。

两条铁律：

1. **规则永远先跑、是硬底线**：LLM 只能“补充”语义命中与提供更自然的改写，
   **永远不能降低或撤销**任何规则命中。最终 risk_level 取规则与 LLM 的最高严重度；
   LLM 即使返回 clean，规则判 high 的句子依然 high。
2. **永远可用、可降级、可审计**：未装 openai / 无 key / 未配模型 / 超时 / 超预算 /
   LLM 返回脏 JSON 时，自动回退纯规则结果，``mode="rules_only"`` 并在 ``llm.status``
   说明原因，服务不因模型侧故障而中断。

对外函数：
  analyze(text, industry, platform, ...)        -> 规则＋LLM 融合检测
  smart_rewrite(text, industry, platform, ...)  -> 优先 LLM 自然改写、复检不过则回退规则替换
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import audit, engine, request_ctx, rules_store
from .llm import PROMPT_VERSION, REWRITE_PROMPT_VERSION, LLMConfig, LLMFinding, LLMJudge
from .models import SEV_ORDER, normalize_text, validate_context

_DISCLAIMER = engine._DISCLAIMER

# 进程内单例：让调用预算与语义缓存跨多次 MCP 请求生效；测试通过 judge= 注入，不依赖它。
_GLOBAL_JUDGE: Optional[LLMJudge] = None


def _default_judge() -> LLMJudge:
    global _GLOBAL_JUDGE
    if _GLOBAL_JUDGE is None:
        _GLOBAL_JUDGE = LLMJudge(LLMConfig.from_env())
    return _GLOBAL_JUDGE


def reset_judge() -> None:
    """重置全局 Judge（配置热更 / 测试隔离用）。"""
    global _GLOBAL_JUDGE
    _GLOBAL_JUDGE = None


def _blank_meta() -> Dict[str, Any]:
    return {"status": "disabled", "model": "",
            "prompt_version": PROMPT_VERSION,
            "rewrite_prompt_version": REWRITE_PROMPT_VERSION,
            "cached": False, "calls": 0, "error": "",
            "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def _backfill_tokens(total_tokens: int) -> None:
    """把本次调用的 LLM token 用量回填到当前请求归属租户；无归属或用量为 0 则跳过。"""
    ctx = request_ctx.current()
    if ctx is None or total_tokens <= 0:
        return
    try:
        ctx.meter.record(ctx.tenant_id, calls=0, tokens=total_tokens)
    except Exception:
        # 计量回填异常不阻断主流程，与计量层容错口径一致
        pass


def _audit_identity() -> "tuple[str, str]":
    """从请求上下文取审计到人字段（key_id / operator）；无上下文返回空串。"""
    ctx = request_ctx.current()
    if ctx is None:
        return "", ""
    return ctx.key_id, ctx.operator


def _categories(industry: str, platform: str):
    return sorted({r["category"] for r in rules_store.active_rules(industry, platform)})


def _make_llm_hit(f: LLMFinding, orig: str) -> Dict[str, Any]:
    """把 LLM 发现转成与规则 Hit 同构的 dict；能在原文定位 span 就给 index，否则 -1。"""
    index, match = -1, (f.span or f.category)
    if f.span:
        n_orig, n_span = normalize_text(orig), normalize_text(f.span)
        if n_span:
            pos = n_orig.find(n_span)
            if pos != -1:
                index, match = pos, orig[pos:pos + len(f.span)]
    return {
        "category": f.category,
        "severity": f.severity,
        "law": f.law_hint or "LLM 语义判断（需结合最新法规与平台规则人工核验）",
        "match": match,
        "suggestion": f.reason or "建议删除或改为客观、可举证表述",
        "index": index,
        "source": "llm",
    }


def _is_duplicate_or_weaker(llm_hit: Dict[str, Any], rule_hits) -> bool:
    """LLM 命中与某条规则命中落在同一文本区间、且并不更严重 → 视为重复，丢弃。"""
    nm = normalize_text(llm_hit["match"])
    if not nm:
        return False
    for rh in rule_hits:
        rm = normalize_text(rh.get("match", ""))
        if rm and (rm in nm or nm in rm) \
                and SEV_ORDER[llm_hit["severity"]] <= SEV_ORDER[rh["severity"]]:
            return True
    return False


def analyze(text: str, industry: str = "general", platform: str = "douyin", *,
            judge: Optional[LLMJudge] = None, use_llm: bool = True) -> Dict[str, Any]:
    """规则硬底线 ＋ LLM 语义融合检测。"""
    validate_context(industry, platform)
    orig = text if isinstance(text, str) else ""
    rule_res = engine.detect(orig, industry, platform)

    hits: List[Dict[str, Any]] = [dict(h, source=h.get("source", "rule"))
                                  for h in rule_res["hits"]]
    rule_hits = [h for h in hits if h.get("source") == "rule"]
    level = rule_res["risk_level"]
    meta = _blank_meta()
    mode = "rules_only"

    if use_llm:
        j = judge or _default_judge()
        jr = j.semantic_detect(orig, industry, platform, _categories(industry, platform))
        meta.update(status=jr.status, model=jr.model, cached=jr.cached,
                    calls=jr.calls, error=jr.error, prompt_version=jr.prompt_version,
                    prompt_tokens=jr.prompt_tokens, completion_tokens=jr.completion_tokens,
                    total_tokens=jr.total_tokens)
        if jr.status == "ok":
            for f in jr.findings:
                lh = _make_llm_hit(f, orig)
                if _is_duplicate_or_weaker(lh, rule_hits):
                    continue
                hits.append(lh)
            for h in hits:  # 规则 ∪ LLM 取最高严重度（LLM 不能拉低规则）
                if SEV_ORDER[h["severity"]] > SEV_ORDER[level]:
                    level = h["severity"]
            mode = "rules_plus_llm"
        # status 非 ok：保持纯规则结果，mode 维持 rules_only，原因见 meta["status"]

    hits.sort(key=lambda h: -SEV_ORDER[h["severity"]])
    res = {
        "risk_level": level,
        "clean": level == "clean",
        "count": len(hits),
        "hits": hits,
        "industry": industry,
        "platform": platform,
        "mode": mode,
        "llm": meta,
        "disclaimer": _DISCLAIMER,
    }
    _key_id, _operator = _audit_identity()
    audit.record(action="detect", result=res, text=orig,
                 key_id=_key_id, operator=_operator)
    _backfill_tokens(res["llm"].get("total_tokens", 0))
    return res


def smart_rewrite(text: str, industry: str = "general", platform: str = "douyin", *,
                  judge: Optional[LLMJudge] = None, use_llm: bool = True) -> Dict[str, Any]:
    """优先 LLM 自然整句改写；LLM 不可用或改写后复检仍违规，则回退规则机械替换。"""
    validate_context(industry, platform)
    orig = text if isinstance(text, str) else ""
    base = engine.suggest_rewrite(orig, industry, platform)  # 已含规则替换＋复检
    meta = _blank_meta()

    rewritten = base["rewritten"]
    rewrite_mode = "rules_only"

    if not use_llm:
        meta["status"] = "disabled"
    elif base["risk_level"] == "clean":
        meta["status"] = "not_needed"          # 原文无风险，无需调用模型（省预算）
        rewritten = orig
    else:
        j = judge or _default_judge()
        summary = [{"category": r.get("category", ""), "severity": base["risk_level"],
                    "match": r.get("from", "")} for r in base.get("replacements", [])]
        # natural_rewrite 返回 (text, status, model_or_error, usage)
        cand, status, info, usage = j.natural_rewrite(orig, summary)
        meta["status"] = status
        meta["prompt_tokens"] = usage.get("prompt_tokens", 0)
        meta["completion_tokens"] = usage.get("completion_tokens", 0)
        meta["total_tokens"] = usage.get("total_tokens", 0)
        if status == "ok":
            meta["model"] = info
            if cand and cand.strip():
                recheck = engine.detect(cand.strip(), industry, platform)
                if recheck["clean"]:
                    rewritten = cand.strip()
                    rewrite_mode = "rules_plus_llm"
                else:
                    # LLM 改写仍含违规：绝不采用，保留规则版并标记需人工复核
                    rewrite_mode = "llm_rejected_needs_review"
                    base["llm_candidate"] = cand.strip()
                    base["llm_candidate_risk"] = recheck["risk_level"]
        else:
            meta["error"] = info or status

    recheck = engine.detect(rewritten, industry, platform)
    out = dict(base)
    out.update({
        "rewritten": rewritten,
        "rewrite_mode": rewrite_mode,
        "rewritten_risk": recheck["risk_level"],
        "rewritten_clean": recheck["clean"],
        "needs_human_review": rewrite_mode == "llm_rejected_needs_review",
        "industry": industry,
        "platform": platform,
        "llm": meta,
    })
    _key_id, _operator = _audit_identity()
    audit.record(action="rewrite", result=out, text=orig,
                 key_id=_key_id, operator=_operator)
    _backfill_tokens(out["llm"].get("total_tokens", 0))
    return out
