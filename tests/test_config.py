# -*- coding: utf-8 -*-
"""LLMConfig 配置清洗：非法 env 回退安全默认并记录 warnings，不抛异常。"""
from lcg.llm import LLMConfig


def test_valid_values_preserved():
    cfg = LLMConfig.from_env({
        "LCG_LLM_PROVIDER": "modelscope",
        "LCG_LLM_TIMEOUT": "8.5",
        "LCG_LLM_MAX_CALLS": "50",
        "LCG_PRICE_INPUT_PER_MTOK": "1.2",
        "LCG_PRICE_OUTPUT_PER_MTOK": "3.4",
    })
    assert cfg.provider == "modelscope"
    assert cfg.timeout == 8.5
    assert cfg.max_calls == 50
    assert cfg.price_input_per_mtok == 1.2
    assert cfg.price_output_per_mtok == 3.4
    assert cfg.warnings == []


def test_unknown_provider_falls_back_without_custom_base():
    cfg = LLMConfig.from_env({"LCG_LLM_PROVIDER": "nope-provider"})
    assert cfg.provider == "siliconflow"
    assert any("未知 provider" in w for w in cfg.warnings)


def test_unknown_provider_kept_when_custom_base_url():
    cfg = LLMConfig.from_env({
        "LCG_LLM_PROVIDER": "my-gateway",
        "LCG_LLM_BASE_URL": "https://example.com/v1",
    })
    assert cfg.provider == "my-gateway"
    assert cfg.base_url == "https://example.com/v1"
    assert cfg.warnings == []


def test_nonpositive_timeout_falls_back():
    cfg = LLMConfig.from_env({"LCG_LLM_TIMEOUT": "0"})
    assert cfg.timeout == 20.0
    assert any("TIMEOUT" in w for w in cfg.warnings)


def test_negative_prices_and_budget_fall_back():
    cfg = LLMConfig.from_env({
        "LCG_PRICE_INPUT_PER_MTOK": "-1",
        "LCG_PRICE_OUTPUT_PER_MTOK": "-2.5",
        "LCG_LLM_MAX_CALLS": "-3",
    })
    assert cfg.price_input_per_mtok == 0.0
    assert cfg.price_output_per_mtok == 0.0
    assert cfg.max_calls == 200
    assert len(cfg.warnings) == 3


def test_malformed_numeric_env_falls_back():
    cfg = LLMConfig.from_env({
        "LCG_LLM_TIMEOUT": "abc",
        "LCG_LLM_MAX_CALLS": "xyz",
    })
    assert cfg.timeout == 20.0
    assert cfg.max_calls == 200
