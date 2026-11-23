# -*- coding: utf-8 -*-
"""
export_report.py —— 生成可复现的成品样例（整场报告 HTML/CSV、改写前后对照、反馈导出）。

零第三方依赖，离线可跑；内置示例语料，也可用 ``--input`` 传入 JSON / JSONL 片段。

输出到 ``--out-dir``（默认 ``samples/``）：
  · ``batch_report.html``         整场合规周报（风险分布 / 类别 / 主播分级 / 待整改清单）
  · ``batch_report.csv``          分段明细
  · ``rewrite_before_after.csv``  命中词替换前后对照
  · ``feedback_example.csv``      误报 / 漏报反馈导出样例

示例数据仅用于演示产物形态，不代表任何真实客户或直播场次。
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from lcg import aggregator, engine, feedback  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows 终端防中文乱码
except Exception:
    pass

RISK_CN = {"clean": "合规", "low": "低风险", "medium": "中风险", "high": "高风险"}
RISK_COLOR = {"clean": "#1a7f37", "low": "#bf8700", "medium": "#bc4c00", "high": "#cf222e"}

# 内置示例语料（规则层判定已经探针核实），仅作演示
SAMPLE_MESSAGES = [
    {"speaker": "主播A", "text": "这款保温杯304不锈钢内胆，一年质保，48小时内发货。"},
    {"speaker": "主播B", "text": "全网最低价，国家级大师作品，销量第一，百分百纯天然！"},
    {"speaker": "主播A", "text": "喜欢的扣1，家人们看看这款冰种手镯，配证书支持复检。"},
    {"speaker": "主播B", "text": "买这个稳赚不赔，保值升值空间巨大，错过再无！"},
    {"speaker": "主播C", "text": "蓝帽认证保健食品，增强免疫力，本品不能代替药物。"},
]

REWRITE_CASES = [
    ("jadeite", "douyin", "这只手镯100%保真，买到就是升值！"),
    ("general", "douyin", "想要优惠的加 ｖｘ：ａｂｃ１２３４５ 咨询。"),
    ("food", "douyin", "坚持喝三个月，高血压都降了，糖尿病也稳了，比吃药还管用！"),
    ("cosmetics", "douyin", "这款药妆面霜消炎抗敏，专治湿疹皮炎，七天根治痘痘！"),
]

FEEDBACK_SAMPLES = [
    {"feedback": "false_positive", "reported_risk": "medium", "category": "化妆品-医疗作用宣称",
     "text": "这款精华帮助祛痘控油，温和不刺激。", "note": "合规妆效被误报，建议复核词库"},
    {"feedback": "false_negative", "reported_risk": "clean", "category": "站外导流",
     "text": "想要资料的看我主页联系方式。", "note": "暗示导流，规则层未命中，待补语义探针"},
    {"feedback": "review", "reported_risk": "low", "category": "绝对化用语",
     "text": "这款是我们店里卖得很好的一款。", "note": "存疑：销量描述是否构成夸大，待人工复核"},
]


def _load_messages(path: Optional[str]) -> List[Dict[str, Any]]:
    if not path:
        return list(SAMPLE_MESSAGES)
    p = Path(path)
    raw = p.read_text(encoding="utf-8").strip()
    if p.suffix.lower() == ".jsonl":
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    else:
        rows = json.loads(raw)
    if isinstance(rows, dict):
        rows = [rows]
    return [{"speaker": str(r.get("speaker", "")), "text": str(r.get("text", ""))} for r in rows]


def _esc(v: Any) -> str:
    return html.escape(str(v if v is not None else ""), quote=True)


def _risk_badge(level: str) -> str:
    color = RISK_COLOR.get(level, "#57606a")
    cn = RISK_CN.get(level, level)
    return f'<span class="badge" style="background:{color}">{_esc(level)} · {_esc(cn)}</span>'


def write_batch_csv(path: Path, batch: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["seq", "speaker", "text", "risk_level", "hits"])
        for seg in batch["results"]:
            hits = "; ".join(f"{h['category']}({h['severity']})" for h in seg["hits"])
            writer.writerow([seg["seq"], seg["speaker"], seg["text"], seg["risk_level"], hits])


def write_rewrite_csv(path: Path, industry: str, platform: str) -> int:
    rows = 0
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["industry", "platform", "original", "risk_level",
                         "replacements", "rewritten", "rewritten_risk", "rewritten_clean"])
        for ind, pf, text in REWRITE_CASES:
            rw = engine.suggest_rewrite(text, ind, pf)
            repl = "; ".join(f"{x['from']} → {x['to']}" for x in rw["replacements"])
            writer.writerow([ind, pf, rw["original"], rw["risk_level"], repl,
                             rw["rewritten"], rw["rewritten_risk"], rw["rewritten_clean"]])
            rows += 1
    return rows


def write_feedback_csv(path: Path, industry: str, platform: str) -> int:
    tmp_dir = Path(tempfile.mkdtemp(prefix="lcg_report_"))
    jsonl = tmp_dir / "feedback.jsonl"
    for sample in FEEDBACK_SAMPLES:
        feedback.submit(text=sample["text"], industry=industry, platform=platform,
                        reported_risk=sample["reported_risk"], feedback=sample["feedback"],
                        category=sample["category"], note=sample["note"], path=str(jsonl))
    events = feedback.load(str(jsonl))
    return feedback.export_csv(events, str(path))


def render_html(summary: Dict[str, Any], batch: Dict[str, Any],
                industry: str, platform: str) -> str:
    dist = summary["risk_distribution"]
    total = max(summary["segments"], 1)

    dist_cells = "".join(
        f'<tr><td>{_risk_badge(level)}</td><td>{dist.get(level, 0)}</td>'
        f'<td>{dist.get(level, 0) / total * 100:.0f}%</td></tr>'
        for level in ("clean", "low", "medium", "high"))

    cat_rows = "".join(
        f'<tr><td>{_esc(c["category"])}</td><td>{c["count"]}</td></tr>'
        for c in summary["categories"]) or '<tr><td colspan="2">无命中类别</td></tr>'

    sp_rows = "".join(
        f'<tr><td>{_esc(sp["speaker"])}</td><td>{_risk_badge(sp["max_risk"])}</td>'
        f'<td>{sp["segments"]}</td><td>{sp["high_hits"]}</td></tr>'
        for sp in summary["speakers"])

    review_rows = "".join(
        f'<tr><td>{r["seq"]}</td><td>{_esc(r["speaker"])}</td><td>{_esc(r["text"])}</td>'
        f'<td>{_risk_badge(r["risk_level"])}</td><td>{_esc(", ".join(r["categories"]))}</td></tr>'
        for r in summary["review_list"]) or '<tr><td colspan="5">无待整改分段</td></tr>'

    detail_rows = ""
    for seg in batch["results"]:
        hits = "; ".join(f"{h['category']}·{h['match']}" for h in seg["hits"])
        detail_rows += (f'<tr><td>{seg["seq"]}</td><td>{_esc(seg["speaker"])}</td>'
                        f'<td>{_esc(seg["text"])}</td><td>{_risk_badge(seg["risk_level"])}</td>'
                        f'<td>{_esc(hits)}</td></tr>')

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>直播合规周报（示例）</title>
<style>
  body {{
    font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
    margin: 2rem; color: #1f2328; background: #f6f8fa;
  }}
  h1 {{ font-size: 1.4rem; }}
  .meta {{ color: #57606a; font-size: .9rem; margin-bottom: 1rem; }}
  .badge {{
    color: #fff; border-radius: 10px; padding: 2px 10px;
    font-size: .82rem; white-space: nowrap;
  }}
  .cards {{ display: flex; gap: 1rem; margin: 1rem 0; flex-wrap: wrap; }}
  .card {{
    background: #fff; border: 1px solid #d0d7de;
    border-radius: 10px; padding: .8rem 1.1rem;
  }}
  .card .num {{ font-size: 1.3rem; font-weight: 600; }}
  table {{
    border-collapse: collapse; width: 100%; background: #fff;
    margin: .6rem 0 1.4rem; font-size: .9rem;
  }}
  th, td {{ border: 1px solid #d0d7de; padding: 6px 10px; text-align: left; vertical-align: top; }}
  th {{ background: #eaeef2; }}
  section {{ margin-bottom: 1.6rem; }}
  .footnote {{ color: #57606a; font-size: .8rem; }}
</style>
</head>
<body>
<h1>直播合规周报（演示样例）</h1>
<p class="meta">行业：{_esc(industry)} ｜ 平台：{_esc(platform)} ｜
本页由 <code>scripts/export_report.py</code> 离线生成，示例数据不代表真实场次。</p>
<div class="cards">
  <div class="card"><div>总体风险</div>
  <div class="num">{_risk_badge(summary['overall_risk'])}</div></div>
  <div class="card"><div>分段数</div><div class="num">{summary['segments']}</div></div>
  <div class="card"><div>标记风险分段</div>
  <div class="num">{summary['flagged_segments']}</div></div>
  <div class="card"><div>high 命中</div><div class="num">{batch['high_risk_hits']}</div></div>
</div>
<section>
  <h2>风险分布</h2>
  <table><tr><th>级别</th><th>段数</th><th>占比</th></tr>{dist_cells}</table>
</section>
<section>
  <h2>命中类别</h2>
  <table><tr><th>类别</th><th>次数</th></tr>{cat_rows}</table>
</section>
<section>
  <h2>按主播分级</h2>
  <table><tr><th>主播</th><th>最高风险</th><th>分段数</th><th>high 命中</th></tr>{sp_rows}</table>
</section>
<section>
  <h2>待整改清单</h2>
  <table><tr><th>序号</th><th>主播</th><th>话术</th><th>风险</th><th>类别</th></tr>{review_rows}</table>
</section>
<section>
  <h2>分段明细</h2>
  <table><tr><th>序号</th><th>主播</th><th>话术</th><th>风险</th><th>命中</th></tr>{detail_rows}</table>
</section>
<p class="footnote">本工具仅为合规风险提示与改写建议，不构成法律意见；
法条与平台规则以监管机关及平台最新规则为准。</p>
</body>
</html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description="生成可复现的合规成品样例（HTML/CSV）")
    parser.add_argument("--input", help="可选 JSON/JSONL 片段文件；缺省用内置示例语料")
    parser.add_argument("--out-dir", default="samples", help="输出目录（默认 samples）")
    parser.add_argument("--industry", default="general", help="行业（默认 general）")
    parser.add_argument("--platform", default="douyin", help="平台（默认 douyin）")
    args = parser.parse_args()

    messages = _load_messages(args.input)
    batch = engine.scan_batch(messages, args.industry, args.platform)
    summary = aggregator.summarize(batch)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    write_batch_csv(out / "batch_report.csv", batch)
    n_rw = write_rewrite_csv(out / "rewrite_before_after.csv", args.industry, args.platform)
    n_fb = write_feedback_csv(out / "feedback_example.csv", args.industry, args.platform)
    (out / "batch_report.html").write_text(
        render_html(summary, batch, args.industry, args.platform), encoding="utf-8")

    print(f"输出目录：{out.resolve()}")
    print(f"  batch_report.html / batch_report.csv：{batch['segments']} 段，"
          f"总体 {summary['overall_risk']}，标记 {summary['flagged_segments']} 段")
    print(f"  rewrite_before_after.csv：{n_rw} 条改写对照")
    print(f"  feedback_example.csv：{n_fb} 条反馈导出")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
