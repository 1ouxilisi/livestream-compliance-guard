# -*- coding: utf-8 -*-
"""
LLM 语义层与融合编排测试。

全部通过注入 FakeBackend 在**无网络、无模型 key** 的环境下确定性验证：
  - 规则硬底线：LLM 永远不能降低规则结论，只能补充；
  - 自动降级：禁用 / 无 key / 超时异常 / 脏 JSON / 超预算都回退纯规则；
  - 融合：语义命中补充、span 定位、重复抑制、更严重升级保留；
  - 缓存与预算：同文不重复计费、预算耗尽即降级；主模型失败切备用；
  - 改写闭环：LLM 自然改写复检 clean 才采用，否则回退规则替换并标人工复核。
"""
from lcg import engine
from lcg.llm import PROMPT_VERSION, FakeBackend, LLMConfig, LLMJudge
from lcg.pipeline import analyze, smart_rewrite

# ---- 固定语料（规则层判定已经探针核实）-------------------------------------
A = "这款摆件越往后越稀罕，留着不会亏，晚点转手能多拿一笔"   # general 规则 clean，语义疑似升值
B = "懂的都懂，这种好东西以后只会越来越值钱"                 # general 规则 clean
C = "这只手镯100%保真，买到就是升值！"                       # jadeite high
D = "这款手镯为天然翡翠材质，附检测证书，支持复检，欢迎按需挑选。"  # jadeite clean（合规改写）
E = "这只手镯还是全网最好，100%保真！"                        # jadeite high（LLM 若给出仍须拒绝）
F = "这是全网最好的一款，100%升值"                            # general high
G = "这是最好的一款"                                          # general high（规则已命中“最好”）
H = "喜欢的扣1，家人们"                                       # general low（诱导性话术）


def make_cfg(**kw) -> LLMConfig:
    base = dict(enabled=True, provider="fake", model_primary="fake-model",
                model_fallback="", base_url="", api_key="fake-key",
                timeout=5.0, max_calls=100, temperature=0.0)
    base.update(kw)
    return LLMConfig(**base)


def make_judge(fake: FakeBackend, **kw) -> LLMJudge:
    return LLMJudge(make_cfg(**kw), backend=fake)


def high_payload(span="留着不会亏", category="暗示升值投资承诺", severity="high"):
    return {"overall": severity, "findings": [
        {"category": category, "severity": severity, "span": span,
         "reason": "暗示保值增值、稳赚不赔", "law_hint": "《广告法》第25条"}]}


# ---------- 降级路径（C6）----------
def test_analyze_disabled_never_calls_llm():
    fake = FakeBackend(detect_payload=high_payload())
    r = analyze(A, "general", "douyin", judge=make_judge(fake, enabled=False))
    assert r["mode"] == "rules_only"
    assert r["llm"]["status"] == "disabled"
    assert r["risk_level"] == "clean"
    assert fake.calls == 0


def test_analyze_no_key_falls_back_to_rules():
    j = LLMJudge(LLMConfig(enabled=True, api_key="", model_primary="",
                           model_fallback=""), backend=None)
    r = analyze(A, "general", "douyin", judge=j)
    assert r["mode"] == "rules_only"
    assert r["llm"]["status"] == "no_key"
    assert r["risk_level"] == "clean"


def test_analyze_parse_error_falls_back():
    fake = FakeBackend(detect_payload="我觉得这句话没什么问题啊")
    r = analyze(A, "general", "douyin", judge=make_judge(fake))
    assert r["mode"] == "rules_only"
    assert r["llm"]["status"] == "parse_error"
    assert r["risk_level"] == "clean"


def test_analyze_backend_exception_falls_back():
    fake = FakeBackend(raise_exc=TimeoutError("boom"))
    r = analyze(F, "general", "douyin", judge=make_judge(fake))
    assert r["mode"] == "rules_only"
    assert r["llm"]["status"] == "error"
    assert "boom" in r["llm"]["error"]
    assert r["risk_level"] == "high"   # 规则仍兜住高危句


def test_budget_zero_disables_llm():
    fake = FakeBackend(detect_payload=high_payload())
    r = analyze(A, "general", "douyin", judge=make_judge(fake, max_calls=0))
    assert r["llm"]["status"] == "budget"
    assert r["mode"] == "rules_only"
    assert fake.calls == 0


def test_budget_exhausted_then_fallback():
    fake = FakeBackend(detect_payload=high_payload())
    j = make_judge(fake, max_calls=1)
    r1 = analyze(A, "general", "douyin", judge=j)
    assert r1["mode"] == "rules_plus_llm"
    r2 = analyze(B, "general", "douyin", judge=j)   # 不同文本，绕开缓存
    assert r2["mode"] == "rules_only"
    assert r2["llm"]["status"] == "budget"


# ---------- 硬底线与融合（C5）----------
def test_llm_fuses_semantic_high_missed_by_rules():
    assert engine.detect(A, "general", "douyin")["clean"]   # 前置：规则层确实漏
    fake = FakeBackend(detect_payload=high_payload())
    r = analyze(A, "general", "douyin", judge=make_judge(fake))
    assert r["mode"] == "rules_plus_llm"
    assert r["risk_level"] == "high"
    lh = [h for h in r["hits"] if h["source"] == "llm"]
    assert len(lh) == 1 and lh[0]["category"] == "暗示升值投资承诺"
    assert lh[0]["index"] >= 0 and lh[0]["match"] == "留着不会亏"   # span 精确定位
    assert r["llm"]["status"] == "ok" and r["llm"]["model"] == "fake-model"
    assert r["llm"]["prompt_version"] == PROMPT_VERSION


def test_hard_floor_llm_cannot_downgrade_rules():
    assert engine.detect(F, "general", "douyin")["risk_level"] == "high"
    fake = FakeBackend(detect_payload={"overall": "clean", "findings": []})
    r = analyze(F, "general", "douyin", judge=make_judge(fake))
    assert r["risk_level"] == "high"                  # LLM 说 clean 也不能拉低
    assert any(h["source"] == "rule" for h in r["hits"])
    assert r["mode"] == "rules_plus_llm"


def test_duplicate_llm_hit_at_same_span_suppressed():
    base = engine.detect(G, "general", "douyin")
    assert base["risk_level"] == "high"
    fake = FakeBackend(detect_payload=high_payload(
        span="最好", category="绝对化用语", severity="high"))
    r = analyze(G, "general", "douyin", judge=make_judge(fake))
    assert r["count"] == base["count"]                # 同区间同级不新增
    assert not any(h["source"] == "llm" for h in r["hits"])


def test_llm_upgrade_more_severe_at_same_span_kept():
    assert engine.detect(H, "general", "douyin")["risk_level"] == "low"
    fake = FakeBackend(detect_payload=high_payload(
        span="喜欢的扣1", category="诱导站外互动", severity="high"))
    r = analyze(H, "general", "douyin", judge=make_judge(fake))
    assert r["risk_level"] == "high"                  # 更严重的 LLM 判断保留
    assert any(h["source"] == "llm" and h["severity"] == "high" for h in r["hits"])
    assert any(h["source"] == "rule" and h["severity"] == "low" for h in r["hits"])


def test_llm_overall_high_without_evidence_not_upgraded():
    payload = {"overall": "high",
               "findings": [{"category": "x", "severity": "clean"},
                            {"category": "y", "severity": "extreme"}]}
    fake = FakeBackend(detect_payload=payload)
    r = analyze(A, "general", "douyin", judge=make_judge(fake))
    assert r["risk_level"] == "clean"                 # 无有效 finding 不凭空升级
    assert r["count"] == 0


def test_llm_span_not_found_gets_minus_one():
    fake = FakeBackend(detect_payload=high_payload(
        span="原文里根本不存在的片段zzz", category="语义风险", severity="medium"))
    r = analyze(A, "general", "douyin", judge=make_judge(fake))
    lh = [h for h in r["hits"] if h["source"] == "llm"]
    assert lh and lh[0]["index"] == -1


# ---------- 缓存 / 主备路由（C3/C8）----------
def test_detect_cache_avoids_second_call():
    fake = FakeBackend(detect_payload=high_payload())
    j = make_judge(fake)
    r1 = analyze(A, "general", "douyin", judge=j)
    r2 = analyze(A, "general", "douyin", judge=j)
    assert fake.calls == 1
    assert r2["llm"]["cached"] is True
    assert r1["risk_level"] == r2["risk_level"] == "high"


def test_fallback_model_after_primary_failure():
    fake = FakeBackend(detect_payload=high_payload(), fail_models={"bad-model"})
    j = LLMJudge(make_cfg(model_primary="bad-model", model_fallback="good-model"),
                 backend=fake)
    r = analyze(A, "general", "douyin", judge=j)
    assert r["llm"]["status"] == "ok"
    assert r["llm"]["model"] == "good-model"
    assert fake.calls == 2
    assert fake.models_seen == ["bad-model", "good-model"]


# ---------- 自然改写闭环（C9）----------
def test_smart_rewrite_llm_clean_adopted():
    fake = FakeBackend(rewrite_text=D)
    r = smart_rewrite(C, "jadeite", "douyin", judge=make_judge(fake))
    assert r["rewrite_mode"] == "rules_plus_llm"
    assert r["rewritten"] == D.strip()
    assert r["rewritten_clean"] is True
    assert r["needs_human_review"] is False
    assert r["llm"]["status"] == "ok"


def test_smart_rewrite_llm_still_violating_rejected():
    fake = FakeBackend(rewrite_text=E)
    r = smart_rewrite(C, "jadeite", "douyin", judge=make_judge(fake))
    assert r["rewrite_mode"] == "llm_rejected_needs_review"
    assert r["needs_human_review"] is True
    assert r["llm_candidate"] == E.strip()
    assert "100%" not in r["rewritten"]               # 回退采用规则机械版
    assert r["rewritten_clean"] is True


def test_smart_rewrite_no_key_uses_rules():
    j = LLMJudge(LLMConfig(enabled=True, api_key="", model_primary=""), backend=None)
    r = smart_rewrite(C, "jadeite", "douyin", judge=j)
    base = engine.suggest_rewrite(C, "jadeite", "douyin")
    assert r["rewrite_mode"] == "rules_only"
    assert r["rewritten"] == base["rewritten"]
    assert r["llm"]["status"] == "no_key"


def test_smart_rewrite_clean_text_skips_llm():
    fake = FakeBackend(rewrite_text="不该被调用")
    r = smart_rewrite(D, "jadeite", "douyin", judge=make_judge(fake))
    assert r["rewrite_mode"] == "rules_only"
    assert r["llm"]["status"] == "not_needed"
    assert r["rewritten"] == D.strip()
    assert fake.calls == 0


# ---------- 配置（C1）----------
def test_config_from_env(monkeypatch):
    monkeypatch.setenv("LCG_LLM_PROVIDER", "siliconflow")
    monkeypatch.setenv("SILICONFLOW_API_KEY", "sk-xxx")
    monkeypatch.setenv("LCG_MODEL_PRIMARY", "model-aaa")
    monkeypatch.setenv("LCG_LLM_TIMEOUT", "8")
    monkeypatch.setenv("LCG_LLM_MAX_CALLS", "7")
    c = LLMConfig.from_env()
    assert c.api_key == "sk-xxx"
    assert c.model_primary == "model-aaa"
    assert c.base_url == "https://api.siliconflow.cn/v1"
    assert c.timeout == 8.0 and c.max_calls == 7


def test_config_disabled(monkeypatch):
    monkeypatch.setenv("LCG_LLM_ENABLED", "0")
    assert LLMConfig.from_env().enabled is False


# ---------- token usage 计量与透传 ----------
def test_usage_collected_and_passthrough():
    fake = FakeBackend(detect_payload=high_payload(),
                       usage={"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150})
    r = analyze(A, "general", "douyin", judge=make_judge(fake))
    assert r["llm"]["status"] == "ok"
    assert r["llm"]["prompt_tokens"] == 120
    assert r["llm"]["completion_tokens"] == 30
    assert r["llm"]["total_tokens"] == 150


def test_usage_carried_on_cache_hit():
    fake = FakeBackend(detect_payload=high_payload(),
                       usage={"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150})
    j = make_judge(fake)
    analyze(A, "general", "douyin", judge=j)
    r2 = analyze(A, "general", "douyin", judge=j)
    assert r2["llm"]["cached"] is True and fake.calls == 1
    # 缓存命中沿用基准那次的 token 量，不重复计费也不归零
    assert r2["llm"]["total_tokens"] == 150
    assert r2["llm"]["prompt_tokens"] == 120


def test_usage_accumulated_across_fallback():
    fake = FakeBackend(detect_payload=high_payload(), fail_models={"bad-model"},
                       usage={"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120})
    j = LLMJudge(make_cfg(model_primary="bad-model", model_fallback="good-model"),
                 backend=fake)
    r = analyze(A, "general", "douyin", judge=j)
    assert r["llm"]["status"] == "ok" and fake.calls == 2
    # 仅成功调用计 token；主模型异常那次不计费，usage 只来自备用成功调用
    assert r["llm"]["prompt_tokens"] == 100
    assert r["llm"]["completion_tokens"] == 20
    assert r["llm"]["total_tokens"] == 120


def test_rewrite_usage_passthrough():
    fake = FakeBackend(rewrite_text=D,
                       usage={"prompt_tokens": 90, "completion_tokens": 25, "total_tokens": 115})
    r = smart_rewrite(C, "jadeite", "douyin", judge=make_judge(fake))
    assert r["llm"]["status"] == "ok"
    assert r["llm"]["prompt_tokens"] == 90
    assert r["llm"]["completion_tokens"] == 25
    assert r["llm"]["total_tokens"] == 115


def test_config_price_from_env(monkeypatch):
    monkeypatch.setenv("LCG_PRICE_INPUT_PER_MTOK", "2.5")
    monkeypatch.setenv("LCG_PRICE_OUTPUT_PER_MTOK", "8.0")
    c = LLMConfig.from_env()
    assert c.price_input_per_mtok == 2.5
    assert c.price_output_per_mtok == 8.0


# ---------- token 用量回填到请求归属租户 ----------
def test_backfill_tokens_to_request_tenant():
    from lcg import request_ctx
    from lcg.tenant import Tenant, UsageMeter

    fake = FakeBackend(detect_payload=high_payload(),
                       usage={"prompt_tokens": 120, "completion_tokens": 30,
                              "total_tokens": 150})
    meter = UsageMeter()
    meter.store.register(Tenant(id="t1", name="一号"))
    token = request_ctx.set_request(
        request_ctx.RequestContext(tenant_id="t1", meter=meter))
    try:
        r = analyze(A, "general", "douyin", judge=make_judge(fake))
        assert r["llm"]["total_tokens"] == 150
    finally:
        request_ctx.reset(token)
    snap = meter.snapshot()["t1"]
    assert snap["tokens"] == 150
    # calls 由 HTTP 鉴权层记一次；回填只补 token，不重复计 calls
    assert snap["calls"] == 0


def test_no_request_ctx_skips_backfill():
    from lcg import request_ctx
    from lcg.tenant import Tenant, UsageMeter

    request_ctx.set_request(None)
    fake = FakeBackend(detect_payload=high_payload(),
                       usage={"prompt_tokens": 1, "completion_tokens": 1,
                              "total_tokens": 150})
    meter = UsageMeter()
    meter.store.register(Tenant(id="t1", name="一号"))
    analyze(A, "general", "douyin", judge=make_judge(fake))
    snap = meter.snapshot()["t1"]
    # 无请求归属时不回填 token，也不重复计 calls
    assert snap["tokens"] == 0
    assert snap["calls"] == 0
