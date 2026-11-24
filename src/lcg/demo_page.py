# -*- coding: utf-8 -*-
"""
lcg.demo_page —— 可交互 Web demo 的单页前端。

设计取舍（对齐项目两条铁律）：

1. **零依赖、离线可跑**：整个页面是一个内联 HTML 字符串，不引用任何 CDN、
   字体或外部 JS，任何浏览器打开即可用；私域/内网部署也能直接演示。
2. **不碰模型预算**：页面只调用 ``/demo/analyze``，该端点固定 ``use_llm=False``，
   走纯规则层。公开 demo 无限次被刷也不会消耗 token，没有 key 也永远可用。
   页面上明确标注 "rules-only"，不暗示公开 demo 已含语义层。
3. **不夸大能力**：结果区固定展示免责声明；改写建议标注为 suggestion，
   不做"包过审""法律认证"这类表述。

对外文案口径：这是 portfolio demo，不是客户案例。
"""
# ruff: noqa: E501
# 上面这行是文件级豁免：整页 HTML/CSS/JS 作为一段内联字符串维护，
# 长行是浏览器里的真实排版，拆行反而会让 JS 字符串拼接更难核对。
from __future__ import annotations

DEMO_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Content Moderation Guard — live demo</title>
<style>
  :root{
    --bg:#0e1116; --panel:#161b22; --line:#262d38; --fg:#e6edf3; --dim:#9aa4b2;
    --hi:#ff6b5e; --mid:#f0b429; --low:#4da3ff; --ok:#3fb950;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--fg);
    font:15px/1.6 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
  .wrap{display:block;max-width:920px;margin:0 auto;padding:40px 20px 64px}
  h1{font-size:26px;margin:0 0 6px;letter-spacing:-.02em}
  .sub{color:var(--dim);font-size:14px;margin:0 0 26px}
  .badge{display:inline-block;font-size:11px;padding:2px 8px;border-radius:999px;
    border:1px solid var(--line);color:var(--dim);margin-left:8px;vertical-align:2px}
  textarea{width:100%;min-height:132px;resize:vertical;padding:14px;border-radius:10px;
    border:1px solid var(--line);background:var(--panel);color:var(--fg);font:inherit}
  textarea:focus{outline:none;border-color:#3d4756}
  .row{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:12px 0 4px}
  select,button{font:inherit;border-radius:8px;border:1px solid var(--line);
    background:var(--panel);color:var(--fg);padding:9px 12px}
  button.primary{background:#2f81f7;border-color:#2f81f7;color:#fff;font-weight:600;
    padding:11px 22px;cursor:pointer}
  button.primary:disabled{opacity:.55;cursor:not-allowed}
  .link{background:none;border:none;color:var(--dim);text-decoration:underline;
    cursor:pointer;padding:0;font-size:13px}
  .meta{color:var(--dim);font-size:12px;margin-top:6px}
  #out{margin-top:26px}
  .level{display:inline-flex;align-items:center;gap:8px;font-weight:700;
    font-size:13px;text-transform:uppercase;letter-spacing:.06em;
    padding:5px 12px;border-radius:999px;border:1px solid currentColor}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;
    padding:18px 20px;margin-top:14px}
  table{width:100%;border-collapse:collapse;font-size:14px}
  th,td{text-align:left;padding:9px 8px;border-bottom:1px solid var(--line);vertical-align:top}
  th{color:var(--dim);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.04em}
  tr:last-child td{border-bottom:none}
  mark{background:#4a2d2d;color:#ffb3ab;padding:0 3px;border-radius:3px}
  .rw{white-space:pre-wrap;background:#0b0f14;border:1px solid var(--line);
    border-radius:8px;padding:14px;margin-top:10px}
  .foot{color:var(--dim);font-size:12px;line-height:1.7;margin-top:22px;
    border-top:1px solid var(--line);padding-top:14px}
  .err{color:var(--hi);font-size:14px;margin-top:12px}
  .hint{color:var(--dim);font-size:13px}
  .k{color:var(--fg);font-weight:600}
</style>
</head>
<body>
<div class="wrap">
  <h1>Content Moderation Guard<span class="badge">rules-only · live</span></h1>
  <p class="sub">Paste a listing, ad, or comment. The engine maps it against a
  versioned banned-term rule pack and returns severity, the matched term, and a
  rewrite suggestion. English and Chinese input both supported.</p>

  <textarea id="txt" maxlength="2000" placeholder="e.g. 这款减肥茶三天瘦十斤，无效全额退款，绝对安全无副作用。"></textarea>

  <div class="row">
    <select id="industry">
      <option value="general">general</option>
      <option value="food">food</option>
      <option value="cosmetics">cosmetics</option>
      <option value="jadeite">jadeite (jade / jewelry)</option>
    </select>
    <select id="platform">
      <option value="douyin">douyin</option>
      <option value="kuaishou">kuaishou</option>
      <option value="shipinhao">shipinhao</option>
      <option value="taobao">taobao</option>
    </select>
    <button class="primary" id="go">Run check</button>
    <span class="hint" id="cnt">0 / 2000</span>
  </div>
  <div class="row">
    <button class="link" data-s="这款减肥茶三天瘦十斤，无效全额退款，绝对安全无副作用。">sample 1</button>
    <button class="link" data-s="Guaranteed to cure anxiety in 7 days, 100% risk free, no side effects.">sample 2</button>
    <button class="link" data-s="本品为普通食品，热量已标注，请按包装说明食用。">sample 3 (clean)</button>
  </div>

  <div id="out"></div>

  <div class="foot">
    <span class="k">What this is:</span> a portfolio demo of a self-built rules engine
    (versioned JSON rule pack, offline test suite, no external service dependency).
    Public demo intentionally runs the deterministic rule layer only;
    the deliverable adds an optional LLM semantic layer on top, which can never
    lower a rule hit.<br>
    <span class="k">Scope:</span> risk advisory and rewrite suggestions only — not
    legal advice, not a guarantee of platform approval. Judgment stays with the
    regulator, the platform, and you.<br>
    <span class="k">No client data:</span> the demo persists nothing — audit logging is
    off by default here; each request is scored in memory and discarded.
  </div>
</div>

<script>
(function(){
  var txt=document.getElementById('txt'), out=document.getElementById('out'),
      go=document.getElementById('go'), cnt=document.getElementById('cnt');
  var color={high:'var(--hi)',medium:'var(--mid)',low:'var(--low)',clean:'var(--ok)'};

  function esc(s){return String(s).replace(/[&<>"']/g,function(c){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}

  function sync(){cnt.textContent=txt.value.length+' / 2000';}
  txt.addEventListener('input',sync); sync();

  document.querySelectorAll('[data-s]').forEach(function(b){
    b.addEventListener('click',function(){txt.value=b.getAttribute('data-s');sync();});
  });

  function render(d){
    var lvl=d.detect.risk_level, c=color[lvl]||'var(--dim)';
    var hits=d.detect.hits||[];
    var rows = hits.length ? hits.map(function(h){
      return '<tr><td><strong>'+esc(h.severity)+'</strong></td><td>'+esc(h.category)+
        '</td><td><mark>'+esc(h.match)+'</mark></td><td>'+esc(h.source||'rule')+
        '</td></tr>';}).join('')
      : '<tr><td colspan="4" class="hint">No rule hit. That means clean for this rule pack — not a legal clearance.</td></tr>';

    var html='<span class="level" style="color:'+c+'">'+esc(lvl)+' risk</span>'+
      '<div class="card"><table><tr><th>Severity</th><th>Category</th>'+
      '<th>Matched term</th><th>Source</th></tr>'+rows+'</table></div>';

    if(d.rewrite){
      html+='<div class="card"><div class="hint" style="margin-bottom:8px">Suggested rewrite — '+
        esc(d.rewrite.rewrite_mode)+', recheck: <strong style="color:'+
        (color[d.rewrite.rewritten_risk]||'var(--dim)')+'">'+esc(d.rewrite.rewritten_risk)+
        '</strong></div><div class="rw">'+esc(d.rewrite.rewritten)+'</div>'+
        '<div class="meta">Replacement text is taken verbatim from the rule pack\'s '+
        'replacement table, so every edit stays traceable to a rule — it is not an '+
        'LLM-smoothed sentence. The delivered version adds an optional LLM rewrite pass on top.</div></div>';
    } else {
      html+='<div class="card hint">Rewrite skipped: input is already clean for this rule pack.</div>';
    }

    html+='<div class="meta">rules '+esc(d.rules_version)+' · '+esc(d.rule_count)+
      ' rules · engine '+esc(d.version)+' · '+esc(d.elapsed_ms)+' ms</div>';
    out.innerHTML=html;
  }

  go.addEventListener('click',function(){
    if(!txt.value.trim()){out.innerHTML='<div class="err">Input is empty.</div>';return;}
    go.disabled=true; out.innerHTML='<div class="hint">scoring…</div>';
    fetch('demo/analyze',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({text:txt.value,
        industry:document.getElementById('industry').value,
        platform:document.getElementById('platform').value})})
    .then(function(r){return r.json().then(function(j){return {ok:r.ok,j:j};});})
    .then(function(res){
      if(!res.ok){out.innerHTML='<div class="err">'+esc(res.j.detail||res.j.error||'request failed')+'</div>';return;}
      render(res.j);
    })
    .catch(function(e){out.innerHTML='<div class="err">'+esc(e.message)+'</div>';})
    .then(function(){go.disabled=false;});
  });
})();
</script>
</body>
</html>
"""
