---
name: livestream-compliance-guard
description: Scan Chinese live-commerce / livestream-selling scripts, short-video product copy and e-commerce listings for banned absolute terms (Advertising Law Art.9), false or misleading claims (Art.28), investment/value-guarantee promises, medical or efficacy claims, superstition, and off-platform diversion / brushing, with a jadeite-and-gem-specific lexicon and rules for Douyin, Kuaishou, WeChat Channels and Taobao Live. Use whenever preparing or monitoring a live sale, writing a host script or product title, operating an AI shopping agent / digital-human seller, or pre-screening customer-service replies. Returns a risk level (high/medium/low/clean), matched terms with offsets, legal basis, and safer rewrites. Chinese-first with bilingual labels; advisory only, not legal advice.
---

# Live Commerce Compliance Guard（直播电商合规守卫）

## When to use
Use this skill when you need to:
- Pre-check a host's livestream script, a short-video caption, a product title/detail page, or a customer-service reply **before it goes live**.
- Monitor a live stream (sentence by sentence) and flag risky lines in real time or from a replay.
- Run compliance QA inside an **AI shopping agent / digital-human livestream host** so it never speaks banned claims.
- Train hosts/operators with the current rule lexicon for an industry and platform.

## Inputs
- `text` (string): the line or copy to check.
- `industry` (string): `jadeite` (翡翠/玉石, richest built-in lexicon), `food` (食品/保健食品), `cosmetics` (化妆品), or `general` (综合). Rule-only tools default to `jadeite`; smart LLM tools default to `general`.
- `platform` (string): `douyin` | `kuaishou` | `shipinhao` (视频号) | `taobao` (淘宝直播).
- For batch: `transcript` = list of `{"seq": number, "speaker": string, "text": string}` in timeline order.

## Tools
1. `scan_text(text, industry, platform)` → single-line deterministic verdict.
2. `scan_livestream(transcript, industry, platform)` → whole-session timeline + counts.
3. `compliance_rules(industry, platform)` → active lexicon and rule version for display/training/audit.
4. `safe_rewrite(text, industry, platform)` → matched terms, safer replacements, rewrite + re-check.
5. `scan_smart(text, industry, platform, use_llm)` → rule floor + optional LLM semantic fusion for homophones / split chars / emoji / implied hints; degrades to rules-only if no key or on error.
6. `rewrite_smart(text, industry, platform, use_llm)` → LLM natural rewrite keeping selling points, re-checked by rules; falls back to rule replacement on failure.

## Output schema
```json
{
  "risk_level": "high | medium | low | clean",
  "clean": false,
  "count": 7,
  "hits": [
    {"category": "绝对化用语", "severity": "high",
     "law": "《广告法》第9条", "match": "100%", "index": 12,
     "suggestion": "删除绝对化表述，改为可举证的客观描述。"}
  ],
  "industry": "jadeite", "platform": "douyin",
  "disclaimer": "仅为合规风险提示，不构成法律意见。"
}
```

## Rule categories covered
- Absolute superlatives（绝对化用语，Advertising Law Art.9): 国家级/最高级/第一/唯一/顶级/100%/最X…
- False & misleading claims（Art.28）: 永久/零风险/无效退款/虚构原价/最后一天/马上涨价…
- Value & investment promises: 保值/升值/必涨/只涨不跌/收藏必涨/捡漏…
- Medical / efficacy claims（Art.17）: 治疗/根治/减肥/排毒/特效…
- Superstition / pseudo-science: 养生/辟邪/开光/招财/转运/能量石…
- Off-platform diversion & fraud (platform rules): 加微信/私下交易/二维码/刷单/好评返现/拍A发B…
- Jadeite-specific: 保真/绝对A货/赌涨/玻璃种/帝王绿/老坑/完美无瑕 + A货术语提醒（须附证书、支持复检）。

## Severity policy
- **high**: block / must fix before speaking or publishing.
- **medium**: rewrite or add evidence / qualifiers (e.g. 以实物为准).
- **low**: advisory; explain jargon, attach certificate & re-inspection note.

## Important notes
- Rule engine is deterministic and auditable (v1); an optional LLM layer catches homophones, split characters and emoji substitutions and rewrites full sentences, but rules remain the hard floor.
- Keep the lexicon versioned; platform rules change frequently — re-sync before each big promotion.
- Advisory only; the final decision rests with the merchant and the latest official/platform rules. Not legal advice.

## Version
v0.7.7 (2026-11) · rule core v1.4 + optional LLM layer · jadeite / general / food / cosmetics · 4 platforms · 6 MCP tools · stdio + HTTP transport.
