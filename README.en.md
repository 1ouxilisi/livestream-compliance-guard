# livestream-compliance-guard · Live-Commerce Compliance Guard (MCP)

> Real-time banned-word / absolute-term / false-claim detection for **live-commerce** hosts, AI shopping agents and digital-human sellers — built on China Advertising Law plus major platform rules. A shared, language-neutral rule core ships built-in **jadeite** rules and pluggable **food/health-food** and **cosmetics** lexicons.

[![CI](https://github.com/1ouxilisi/livestream-compliance-guard/actions/workflows/ci.yml/badge.svg)](https://github.com/1ouxilisi/livestream-compliance-guard/actions/workflows/ci.yml) [![MCP](https://img.shields.io/badge/MCP-ready-blue)]() [![license](https://img.shields.io/badge/license-MIT-green)]() [![version](https://img.shields.io/badge/version-v0.7.6-orange)]()

Repository: `github.com/1ouxilisi/livestream-compliance-guard`

## Why

A single line like "best / number one / guaranteed authentic / value appreciation / add WeChat / health & blessing" can trigger a **warning, stream cutoff, score deduction, fine, or ban** in live commerce; AI/digital-human sellers talking 24/7 carry even higher risk. This tool exposes compliance checks as an **MCP tool** that any agent (Claude / Cursor / Dify / digital-human backend) can call to intercept risky wording **before it is spoken or published**, with rewrite suggestions.

- Narrow, high-frequency, verifiable output — the shape that works well on MCP marketplaces.
- A deterministic, auditable rule core (explainable and reviewable) plus an **optional** LLM layer for homophones, emoji variants and full-sentence rewriting.

## Tools (6)

| Tool | Purpose |
|---|---|
| `scan_text` | Single-message **rules-only** check: risk level + matched terms + regulatory basis + suggestion (deterministic) |
| `scan_livestream` | Batch scan of a whole stream, timeline + high-risk counts (live / replay risk control) |
| `compliance_rules` | Return the active lexicon for an industry × platform (training / display / audit) |
| `safe_rewrite` | Safe replacement wording for matched terms (rules-only mechanical replacement + recheck) |
| `scan_smart` | **Hard rule floor + LLM semantic fusion**: catches homophone / split-character / emoji / near-synonym evasion; falls back to rules-only with no key, returns `mode` and per-hit `source` |
| `rewrite_smart` | LLM natural full-sentence rewrite first, then rule recheck; falls back to rule replacement if recheck fails or the model is unavailable |

`risk_level`: **high (must block) / medium (must revise) / low (advisory) / clean**.

## Quick start

```bash
# 1) Self-test the rule core with no third-party dependencies
python server.py --selftest

# 1.5) Offline walkthrough (portfolio / recording; --offline calls no model, spends no quota)
python scripts/demo_walkthrough.py --offline

# 2) Rule validation + behavior baseline + unit tests + evals
python scripts/export_rules.py --check
python tests/run_baseline.py
python -m pip install -r requirements-dev.txt
python -m pytest -q
python evals/run_evals.py

# 2.5) Optional: online LLM eval (copy .env.example to .env, set SILICONFLOW_API_KEY and LCG_MODEL_PRIMARY)
python scripts/run_llm_evals.py

# 3) Standard MCP server (stdio)
pip install -r requirements.txt
python server.py

# 4) Remote MCP server (Streamable HTTP, endpoint /mcp, healthz /healthz)
pip install ".[http]"
LCG_BEARER_TOKEN=sk-xxx python -m lcg.server_http   # no token = open on localhost only
```

MCP client config (example):

```json
{
  "mcpServers": {
    "livestream-compliance-guard": {
      "command": "python",
      "args": ["/path/to/server.py"]
    }
  }
}
```

## Architecture

The engine lives in `src/lcg/`: `models` (constants / validation / equal-length normalization / ordinal disambiguation), `rules_store` (rule loading), `engine` (detection / batch aggregation / rewrite, pure logic, rule floor), `llm` (OpenAI-compatible semantic client, optional dependency, degradable), `pipeline` (rule + LLM fusion, `analyze` / `smart_rewrite`), `ingest` (normalize heterogeneous ASR/subtitle/table segments into the scan contract; no ASR/OCR), `aggregator` (batch distribution, category/per-speaker aggregation, review list), `feedback` (local JSONL false-positive/negative/review log + CSV export, optional), `audit` (optional redactable local JSONL trail, disabled by default), `sources` (pluggable input-source protocol + in-memory stub; no real ASR/OCR, no network calls), `tenant` (in-memory quota/usage skeleton; no persistence or auth), `server_stdio` (FastMCP stdio wrapper), `server_http` (Streamable HTTP + healthz + optional Bearer).

The rule source of truth is the core bundle `rules/rules.v1.json` plus plugin bundles `rules/plugins/*.json` (core v1.4: 14 rules / 16 replacements; food and cosmetics plugins: 3 rules / 8 replacements each; aggregated 20 rules / 31 replacements). They are aggregated and validated at startup with industry isolation; Python and future TS/Cloudflare runtimes share the same JSON.

## Coverage & benchmarks

- Regulations: Advertising Law Art. 9 (absolute terms), Art. 17 (medical/effect claims), Art. 25/28 (investment promises and false advertising), Anti-Unfair Competition Law, price fraud.
- Platforms: Douyin, Kuaishou, WeChat Channels shop, Taobao Live (off-platform diversion, private deals, order brushing, fake-review rebates, A-shipped-as-B).
- Industries: `jadeite` (built-in, scope-isolated), `food`, `cosmetics` (external plugins), `general` otherwise. Compliant phrasing is deliberately allowed (e.g. registered health-food functions with "this product cannot replace medicine", ordinary cosmetic effects, registered special claims).
- Two-layer normalization: equal-length layer (full-width to half-width, lowercase, common traditional→simplified) and compact layer (strip spaces / middle dots / emoji / slash / pipe / backslash blockers); ordinal disambiguation for "first"; diversion regex requires a signal word plus digits; replacements are rechecked after rewriting (closed loop).
- Rule layer: **75 offline cases, 100% pass** (100% high-risk recall, 0% clean false positives; 31 benign, 44 adversarial). Performance: ~1.9 ms/sentence average, P95 ~2.7 ms, ~520 sentences/s on this machine (relative comparison only).
- LLM layer: OpenAI-compatible (primary Qwen/Qwen3-14B, fallback DeepSeek-V3); historical online snapshot **40/40**. Online results depend on account balance and model version — see the latest snapshot in `reports/LLM_EVAL.md`; degrades to rules-only with no key. Token usage (input/output/total) is collected and passed through; cost can be estimated from configured per-MTok prices.
- **146 unit tests** passing. See [`reports/PERF.md`](reports/PERF.md), [`reports/LLM_EVAL.md`](reports/LLM_EVAL.md), [`reports/SECURITY.md`](reports/SECURITY.md).

## Boundaries

- Risk advisory and rewrite suggestions only; **not legal advice**.
- Does not verify license/filing/certificate authenticity; does not do speech (ASR) or image (OCR) recognition.
- Medical device, education, finance, alcohol and cross-border English rules are not yet covered (see Roadmap).
- Rule layer has inherent false negatives/positives; online results fluctuate with model version and balance.

## Commercial support

The open-source core can be self-hosted freely. Custom lexicons, industry plugins and private deployment are taken on **only through third-party freelance marketplaces such as Fiverr / Upwork**; all communication and payment stay within the marketplace — no off-platform outreach, private referrals or direct-customer solicitation.

Docs: [Compliance mapping](docs/COMPLIANCE_MAPPING.md) · [Scope & boundaries](docs/SCOPE_BOUNDARY.md) · [Deployment & platform evolution](docs/DEPLOYMENT.md) · [MCP listing notes](docs/MCP_MARKETPLACE.md) · [Recording storyboard](docs/DEMO_SCRIPT.md) · [Sample outputs](samples/README.md)

## Roadmap

- [x] Real LLM integration (Chinese): homophone/innuendo recall + injection/jailbreak resistance + full-sentence rewrite (v0.6.0, snapshot 40/40); English and multi-model scaled red-team (promptfoo/DeepTeam) still P1.
- [ ] Real-time ASR ingestion: speech-to-text → per-sentence live alerting.
- [x] More industries (plugin): food/health-food, cosmetics (v0.5.0).
- [ ] More industries: medical device, education, finance, alcohol (regulations verified item by item first).
- [ ] Compliance weekly report: hit heatmap + per-host risk score + remediation tracking.
- [ ] English / cross-border version (TikTok Shop / Amazon Live).

## Disclaimer

This project provides **compliance risk advisory and technical assistance only**, not legal advice. Rules may lag; rely on regulators and the latest platform rules, and consult legal counsel for important scenarios. The publisher remains responsible for their content.

## License

MIT (rule lexicon and regulatory references are for study and self-check only).
