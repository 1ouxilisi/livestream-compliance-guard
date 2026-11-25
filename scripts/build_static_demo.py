# -*- coding: utf-8 -*-
"""
build_static_demo.py —— 用真实规则引擎预计算一份「静态快照」演示页。

为什么是快照而不是实时推理：
  · 公开页面如果挂实时接口，要么被刷出 token 成本，要么被免费实例的冷启动拖垮；
  · 把 20+ 条真实样本（直接取自仓库自带评测集 evals/cases/*.jsonl）在构建时
    跑一遍，结果内嵌进单个 HTML，页面只做本地筛选，不发任何网络请求。

产物：docs/demo/index.html（单文件、无外链、可被 GitHub Pages 直接托管）
用法：python scripts/build_static_demo.py [--out docs/demo/index.html] [--per-file 16]

口径：这是 portfolio demo，样本全部是自建评测集，不是客户数据。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from lcg import engine, rules_store  # noqa: E402

# ruff: noqa: E501

SAMPLES = (("benign.jsonl", 8), ("adversarial.jsonl", 16), ("semantic.jsonl", 6))
REPO = "https://github.com/1ouxilisi/livestream-compliance-guard"


def _pick(item: dict, *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def load_cases() -> list[dict]:
    cases: list[dict] = []
    seen: set[str] = set()
    for name, limit in SAMPLES:
        path = ROOT / "evals" / "cases" / name
        if not path.exists():
            continue
        taken = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            text = _pick(item, "text", "prompt", "input")
            if not text:
                continue
            cid = str(item.get("id") or f"{name[:-6]}-{taken}")
            if cid in seen:
                continue
            seen.add(cid)
            cases.append({
                "id": cid,
                "text": text,
                "industry": _pick(item, "industry") or "general",
                "platform": _pick(item, "platform") or "douyin",
                "note": _pick(item, "note"),
                "expect": _pick(item, "expect_risk"),
                "source": name,
            })
            taken += 1
            if taken >= limit:
                break
    return cases


def build_records(cases: list[dict]) -> list[dict]:
    out: list[dict] = []
    for case in cases:
        res = engine.detect(case["text"], case["industry"], case["platform"])
        hits = [
            {
                "severity": h.get("severity", ""),
                "category": h.get("category", ""),
                "match": h.get("match", ""),
                "law": h.get("law", ""),
                "suggestion": h.get("suggestion", ""),
            }
            for h in res.get("hits", [])
        ]
        rec = dict(case)
        rec["risk"] = res.get("risk_level", "clean")
        rec["hits"] = hits
        rec["rewrite"] = None
        if hits:
            rw = engine.suggest_rewrite(case["text"], case["industry"], case["platform"])
            rec["rewrite"] = {
                "text": rw.get("rewritten", ""),
                "exchanges": [f"{x['from']} → {x['to']}" for x in rw.get("replacements", [])],
                "risk": rw.get("rewritten_risk", "clean"),
                "clean": bool(rw.get("rewritten_clean")),
            }
        out.append(rec)
    return out


HEAD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Compliance Guard — sample results</title>
<style>
  :root{--bg:#0e1116;--panel:#161b22;--line:#262d38;--fg:#e6edf3;--dim:#9aa4b2;
    --hi:#ff6b5e;--mid:#f0b429;--low:#4da3ff;--ok:#3fb950}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--fg);
    font:15px/1.6 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
  .wrap{max-width:1080px;margin:0 auto;padding:36px 20px 72px}
  h1{font-size:26px;margin:0 0 6px;letter-spacing:-.02em}
  .badge{display:inline-block;font-size:11px;padding:2px 8px;border-radius:999px;
    border:1px solid var(--line);color:var(--dim);margin-left:8px;vertical-align:2px}
  .sub{color:var(--dim);font-size:14px;margin:0 0 8px;max-width:860px}
  .sub b{color:var(--fg)}
  .bar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:22px 0 10px}
  input,select{font:inherit;border-radius:8px;border:1px solid var(--line);
    background:var(--panel);color:var(--fg);padding:9px 12px}
  input{flex:1;min-width:240px}
  .stats{display:flex;gap:18px;flex-wrap:wrap;color:var(--dim);font-size:13px;margin:6px 0 22px}
  .stats b{color:var(--fg);font-weight:600}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 16px 14px}
  .top{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:8px}
  .id{color:var(--dim);font-size:12px;font-family:ui-monospace,Consolas,monospace}
  .lv{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;
    padding:3px 9px;border-radius:999px;border:1px solid currentColor;white-space:nowrap}
  .lv.high{color:var(--hi)}.lv.medium{color:var(--mid)}.lv.low{color:var(--low)}.lv.clean{color:var(--ok)}
  .txt{font-size:14px;margin:0 0 10px}
  mark{background:#4a2d2d;color:#ffb3ab;padding:0 2px;border-radius:3px}
  .hits{width:100%;border-collapse:collapse;font-size:12px;margin-top:4px}
  .hits th,.hits td{text-align:left;padding:5px 6px;border-bottom:1px solid var(--line);vertical-align:top}
  .hits th{color:var(--dim);font-weight:600;font-size:11px;text-transform:uppercase}
  .hits tr:last-child td{border-bottom:none}
  .sg{display:block;color:var(--dim);margin-top:2px}
  .rw{border-top:1px dashed var(--line);margin-top:12px;padding-top:10px;font-size:13px}
  .rw .k{color:var(--dim);font-size:11px;text-transform:uppercase;letter-spacing:.04em}
  .rw .after{color:#b9e8c2}
  .rw .ex{color:var(--dim);font-size:12px;margin-top:4px}
  .note{color:var(--dim);font-size:12px;margin-top:8px}
  .foot{color:var(--dim);font-size:12px;line-height:1.8;margin-top:34px;
    border-top:1px solid var(--line);padding-top:16px}
  .foot a{color:#79b8ff;text-decoration:none}
  .empty{color:var(--dim);padding:40px 0}
</style>
</head>
<body>
<div class="wrap">
  <h1>Compliance Guard — sample results<span class="badge">static snapshot · rules-only</span></h1>
  <p class="sub">Every card below is a <b>real run of the engine</b> over a sample taken from this repo's
  own eval sets (<code>evals/cases/*.jsonl</code>), precomputed at build time. No model is called, nothing
  is typed live: the same rule pack ships in the repo, so every result here is reproducible with
  <code>python evals/run_evals.py</code>.</p>
  <p class="sub">这是构建时用真实规则引擎跑出来的快照，不是实时推理；样本全部来自仓库自带评测集，不含任何客户数据。</p>
  <div class="bar">
    <input id="q" placeholder="搜话术 / 命中词 / 类别…（search）">
    <select id="risk">
      <option value="">全部风险等级</option>
      <option value="high">high · 必拦</option>
      <option value="medium">medium · 需改</option>
      <option value="low">low · 提示</option>
      <option value="clean">clean · 放行</option>
    </select>
    <select id="ind"><option value="">全部行业</option></select>
  </div>
  <div class="stats" id="stats"></div>
  <div class="grid" id="grid"></div>
  <div class="foot" id="foot"></div>
</div>
"""

TAIL = """
</script>
</body>
</html>
"""

JS = """
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function highlight(text, hits){
  let html = esc(text);
  const ms = (hits||[]).map(h=>h.match).filter(Boolean).sort((a,b)=>b.length-a.length);
  for (const m of ms){
    const em = esc(m);
    if (!em) continue;
    const i = html.indexOf(em);
    if (i >= 0) html = html.slice(0,i) + '<mark>' + em + '</mark>' + html.slice(i+em.length);
  }
  return html;
}
function card(r){
  const hits = r.hits || [];
  const rows = hits.map(h=>`<tr><td>${esc(h.severity)}</td><td>${esc(h.category)}</td>
    <td>${esc(h.match)}<span class="sg">${esc(h.law)}</span></td></tr>`).join('');
  const table = hits.length ? `<table class="hits"><tr><th>级别</th><th>类别</th><th>命中 / 依据</th></tr>${rows}</table>` : '';
  const rw = r.rewrite ? `<div class="rw"><div class="k">规则改写 + 复检</div>
    <div class="after">${esc(r.rewrite.text)}</div>
    <div class="ex">${r.rewrite.exchanges.map(esc).join(' ｜ ') || '无需替换'} · 复检 <b>${esc(r.rewrite.risk)}</b>${r.rewrite.clean?' · clean':''}</div></div>` : '';
  const note = r.note ? `<div class="note">${esc(r.note)}</div>` : '';
  return `<div class="card"><div class="top"><span class="id">${esc(r.id)} · ${esc(r.industry)}/${esc(r.platform)}</span>
    <span class="lv ${esc(r.risk)}">${esc(r.risk)}</span></div>
    <p class="txt">${highlight(r.text, hits)}</p>${table}${rw}${note}</div>`;
}
const qEl = document.getElementById('q'), riskEl = document.getElementById('risk'), indEl = document.getElementById('ind');
const grid = document.getElementById('grid'), stats = document.getElementById('stats');
const inds = [...new Set(DATA.map(r=>r.industry))].sort();
indEl.innerHTML = '<option value="">全部行业</option>' + inds.map(i=>`<option value="${esc(i)}">${esc(i)}</option>`).join('');
function apply(){
  const q = qEl.value.trim().toLowerCase(), risk = riskEl.value, ind = indEl.value;
  const list = DATA.filter(r=>{
    if (risk && r.risk !== risk) return false;
    if (ind && r.industry !== ind) return false;
    if (!q) return true;
    const hay = [r.text, r.note, ...(r.hits||[]).flatMap(h=>[h.match,h.category,h.law])].join(' ').toLowerCase();
    return hay.includes(q);
  });
  const c = {high:0,medium:0,low:0,clean:0};
  DATA.forEach(r=>{ if (c[r.risk] !== undefined) c[r.risk]++; });
  const fixed = DATA.filter(r=>r.rewrite && r.rewrite.clean).length;
  const need = DATA.filter(r=>r.rewrite).length;
  stats.innerHTML = `<span>样本 <b>${DATA.length}</b> 条（全部来自仓库评测集）</span>
    <span>high <b>${c.high}</b></span><span>medium <b>${c.medium}</b></span>
    <span>low <b>${c.low}</b></span><span>clean <b>${c.clean}</b></span>
    <span>改写后复检干净 <b>${fixed}/${need}</b></span><span>当前显示 <b>${list.length}</b></span>`;
  grid.innerHTML = list.length ? list.map(card).join('') : '<div class="empty">没有匹配的样本，换个关键词或清空筛选。</div>';
}
qEl.oninput = apply; riskEl.onchange = apply; indEl.onchange = apply;
apply();
"""


def render(records: list[dict], meta: dict, built_at: str) -> str:
    data = json.dumps(records, ensure_ascii=False).replace("</", "<\\/")
    foot = (
        "<div>规则版本 <b>"
        + str(meta.get("version", "?"))
        + "</b> · 核心 "
        + str(meta.get("core_rule_count", 0))
        + " 规则 + 插件 "
        + str(len(meta.get("packages", [])))
        + " 个 → 全局 "
        + str(meta.get("rule_count", 0))
        + " 规则 / "
        + str(meta.get("replacement_count", 0))
        + " 替换 · 构建时间 "
        + built_at
        + "</div>"
        + '<div>自建工程项目（personal portfolio project），非客户案例；输出仅为风险提示与改写建议，'
        + "不构成法律意见，不承诺过审。</div>"
        + '<div><a href="' + REPO + '">' + REPO.replace("https://", "") + "</a>"
        + " · 复跑：<code>python evals/run_evals.py</code> · 重新生成本页："
        + "<code>python scripts/build_static_demo.py</code></div>"
    )
    head = HEAD.replace('<div class="foot" id="foot"></div>', '<div class="foot">' + foot + "</div>")
    return (
        head
        + "<script>\nconst DATA = "
        + data
        + ";\n"
        + JS
        + TAIL
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="生成静态快照演示页（docs/demo/index.html）")
    parser.add_argument("--out", default=str(ROOT / "docs" / "demo" / "index.html"))
    args = parser.parse_args()

    cases = load_cases()
    if not cases:
        print("[FAIL] 没有读到任何样本，确认 evals/cases/*.jsonl 存在", file=sys.stderr)
        return 1
    records = build_records(cases)
    meta = rules_store.meta()
    local = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    built_at = local.strftime("%Y-%m-%d %H:%M UTC+8")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(records, meta, built_at), encoding="utf-8")

    dist: dict[str, int] = {}
    for rec in records:
        dist[rec["risk"]] = dist.get(rec["risk"], 0) + 1
    rewritable = sum(1 for rec in records if rec["rewrite"])
    fixed = sum(1 for rec in records if rec["rewrite"] and rec["rewrite"]["clean"])
    size_kb = out.stat().st_size / 1024
    print(f"[OK] {out.relative_to(ROOT)} · {len(records)} 条样本 · {size_kb:.0f} KB")
    print(f"[OK] 风险分布：{dist} · 改写后复检干净 {fixed}/{rewritable}")
    print("[OK] 单文件、无外链；GitHub Pages 直接把 /docs 设成发布源即可访问 /demo/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
