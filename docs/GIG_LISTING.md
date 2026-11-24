# Gig Listing Draft · Fiverr / Upwork

> 公开文案草稿。**定价、套餐档位价格、成交口径与线索台账不写进本仓**（见私有归档）。
> 本文件只沉淀可公开的能力描述、交付结构与边界声明；发布前按末尾 Checklist 核对占位与在线快照。
> 不出现虚构客户名、评价、销量或"包过审"承诺。

## 1. Title candidates

> 定稿主标题、备选与素材清单见 [`GIG_ASSETS.md`](GIG_ASSETS.md)。

**English**
- ⭐ PRIMARY: `Custom content moderation MCP: banned words, prohibited claims and safe rewrite for e-commerce scripts`
- `Policy compliance filter for scripts, product copy and replies with safe rewrite`
- `Deterministic rule-based content safety checker integrated as an MCP tool for your agent`
- `I will build a live-commerce compliance guard MCP for banned words, claims and diversion`
- `I will deliver a pluggable rule lexicon + optional LLM review for e-commerce scripts`

**中文（备用）**
- ⭐ PRIMARY: `直播话术合规筛查与改写：极限词 / 虚假宣传 / 升值承诺 / 医疗功效 / 站外导流检测`

## 2. One-line summary

A deterministic, auditable rule core with an optional LLM layer that checks scripts, short-video copy, product titles and replies before publication — returning a risk level, matched terms, policy basis and a compliant rewrite. Degrades to rules-only when no model key is available; the rule floor can never be lowered by the LLM. The lexicon is pluggable and can be adapted to your own industry, platform or policy wording.

## 3. What's included (capabilities)

- **Single-message check** (`scan_text`): risk level `high / medium / low / clean`, matched terms, regulatory reference, suggestion.
- **Whole-stream batch scan** (`scan_livestream`): per-segment timeline, high-risk count, per-speaker breakdown and a review list.
- **Compliance rules lookup** (`compliance_rules`): active lexicon for a chosen industry × platform.
- **Safe rewrite** (`safe_rewrite` / `rewrite_smart`): rule-based replacement with recheck; optional LLM natural full-sentence rewrite, re-checked by rules before adoption.
- **Semantic fusion** (`scan_smart`): optional LLM supplements homophone / split-character / emoji / near-synonym evasion; returns mode and per-hit source; auto-falls back to rules-only on missing key, timeout, budget cap or dirty output.
- **Normalization**: full-width/half-width, case, traditional→simplified, space/middle-dot/emoji blockers; ordinal disambiguation for "first".
- **Governance artifacts**: input adaptation for heterogeneous ASR/subtitle segments, batch aggregation, local feedback log (false positive/negative/review) with CSV export, optional redactable audit trail, token usage with cost estimate. Pluggable input-source protocol, in-memory quota/usage and identity/key mapping skeletons are included as scaffolding only (single-process memory; no signup/login, password hash, role-based access enforcement, external persistence or cross-process sharing).
- **Transports**: stdio MCP and remote Streamable HTTP MCP (healthz probe, optional Bearer token).
- **Pluggable lexicons**: built-in general + jadeite; food/health-food and cosmetics as pluggable plugins; new industry packs added via a template. Rule source and review status tracked in `docs/COMPLIANCE_MAPPING.md`.

### Covered today
- Platforms: Douyin, Kuaishou, WeChat Channels shop, Taobao Live.
- Industries: general, jadeite, food/health-food, cosmetics.
- Rule layer: 95 offline cases, 100% pass (100% high-risk recall, 0% clean false positives; 232 unit tests; aggregated 20 rules / 31 replacements).
- Online LLM snapshot: 73/73 latest (recall 14/14, red-team 22/22, zero false-positive 37/37; results fluctuate with model version and balance; latest snapshot in `reports/LLM_EVAL.md`).

## 4. Deliverable tiers (structure only — price TBD)

> 档位价格由发布人按平台与需求另行设定，此处不记录金额。

| Tier | Scope | Deliverables |
|---|---|---|
| Basic | Rule-only check on a provided script/copy set | Risk report (HTML/CSV), matched terms + basis, safe-rewrite table |
| Standard | Basic + custom lexicon adjustments for one industry/platform, batch review of a script set | Above + plugin lexicon, before/after rewrite CSV, review list |
| Premium | Standard + integrated MCP server (stdio/HTTP), optional LLM layer wiring, sample report | Above + deployable server config, samples, README/runbook, test + eval cases |

## 5. Tech & integration

- Python ≥ 3.10; rule core has **zero third-party dependencies**; LLM layer is an optional OpenAI-compatible client.
- Exposed as MCP tools; configurable for any agent/client that speaks MCP, or callable directly as a Python module.
- Rule lexicon lives in shared JSON; a future TS/Cloudflare runtime can reuse the same source.
- Sample outputs: [`samples/`](../samples/README.md) (HTML report, batch CSV, rewrite before/after, feedback export).
- Reproducible walkthrough: `python scripts/demo_walkthrough.py --offline`.

## 6. Boundaries (must appear in the Gig)

- Risk advisory and rewrite suggestions only; **not legal advice**, not a platform audit decision, no endorsement of product authenticity or qualifications.
- Does not verify license/filing/certificate authenticity; does not perform ASR (speech) or OCR (image) recognition.
- High-risk hits must be reviewed by a human before going live.
- Not covered yet: medical devices, finance/insurance, education, alcohol, cross-border/imported goods, English/TikTok Shop/Amazon Live rules; these exist only as placeholder skeletons with no real word lexicon. Identity, quota, audit and cache are in-process memory skeletons, not a production multi-tenant account system.
- Rule layer has inherent false negatives/positives; online results fluctuate with model version and account balance.
- Capability split for listing copy: see `docs/CAPABILITY_TIERS.md` (A: sellable; B: skeleton/optional; C: not promised).

## 7. Engagement terms

- All requirements, communication and payment stay **within the marketplace** (Fiverr / Upwork). No off-platform solicitation, private referrals or direct-customer deals.
- Deliverables are based on materials provided by the buyer; strong-regulated industries (medical/financial) require their own legal review.
- Custom work starts from a scoped brief; source-code ownership and licensing are agreed in the marketplace contract.

## 8. Pre-publish checklist

- [ ] Replace any placeholder in title/summary; confirm the tier deliverables match what you will actually deliver.
- [ ] Re-run offline evals and tests; attach the latest `reports/` snapshot numbers.
- [ ] Verify the repository is public and anonymously accessible (code/README/LICENSE/ docs 200; `.env` and internal materials 404).
- [ ] Keep boundary section 6 visible in the Gig description; do not claim "guaranteed approval" or legal certification.
- [ ] Confirm name/profile and payout account are consistent across platforms.
