# -*- coding: utf-8 -*-
"""
demo_walkthrough.py —— 离线可跑的产品演示脚本（录屏 / 作品集用）。

零第三方依赖：规则核心在本机离线跑通；LLM 语义层在无 key / 超时 / 脏返回时
自动降级 ``rules_only``，正好演示“永远可用、可降级、规则硬底线不可被降低”。

演示分镜（与 docs/DEMO_SCRIPT.md 对应）：
  1. 合规话术放行（clean）
  2. 规则高危拦截（命中词 + 法条依据 + 处置建议）
  3. 变体绕过识别（全角 / 插空格 / emoji 阻断 / 谐音导流）
  4. 行业插件（食品疾病宣称、化妆品药妆速效）
  5. 整场批量检测（scan_batch 时间线与高风险计数）
  6. 规则改写 ＋ 复检闭环
  7. LLM 融合 / 自动降级（规则硬底线不被 LLM 降低）
  8. 规则层性能快照
  9. 批量聚合 / 输入适配 / 反馈闭环 / 审计事件（离线临时目录）

运行：
  python scripts/demo_walkthrough.py            # 人类可读终端输出（有 key 时走在线融合）
  python scripts/demo_walkthrough.py --offline  # 强制纯规则，不调用模型、不耗额度（秒出）
  python scripts/demo_walkthrough.py --json     # 纯 JSON（便于截图 / 对接）
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from lcg import aggregator, audit, engine, feedback, ingest, pipeline  # noqa: E402
from lcg.llm import LLMConfig, LLMJudge  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows 终端防中文乱码
except Exception:
    pass

SEV_ICON = {"clean": "🟢", "low": "🟡", "medium": "🟠", "high": "🔴"}

# ---- 演示语料（规则层判定已经探针核实）-------------------------------------
CLEAN_CASES = [
    ("jadeite", "douyin", "这是天然翡翠A货吊坠，配有鉴定证书，支持复检，喜欢可在直播间下单。"),
    ("food", "douyin", "这款每日坚果配料干净，口感酥脆，新鲜日期发货，独立小包装方便携带。"),
    ("cosmetics", "douyin", "这款面霜主打玻尿酸保湿补水，质地清爽不黏腻，干皮上脸很滋润。"),
]

HIGH_CASE = ("jadeite", "douyin",
             "家人们这块玻璃种帝王绿，100%保真，戴了能养生辟邪，收藏必涨，加微信私下交易，今天最后一天！")

VARIANT_CASES = [
    ("general", "douyin", "想要优惠的加 ｖｘ：ａｂｃ１２３４５ 咨询。", "全角字母数字冒号变体导流"),
    ("general", "douyin", "这是最 好 的一款，没有之一。", "插空格拆分“最好”"),
    ("general", "douyin", "想领资料的宝子，看我主页 微❤️ abc12345 哈", "emoji 阻断联系方式"),
]

PLUGIN_CASES = [
    ("food", "douyin",
     "坚持喝三个月，高血压都降了，糖尿病也稳了，比吃药还管用！", "食品疾病治疗宣称"),
    ("cosmetics", "douyin",
     "这款药妆面霜消炎抗敏，专治湿疹皮炎，七天根治痘痘！", "化妆品医疗作用 + 速效"),
]

BATCH_MESSAGES = [
    {"speaker": "主播A", "text": "这款保温杯304不锈钢内胆，一年质保，48小时内发货。"},
    {"speaker": "主播B", "text": "全网最低价，国家级大师作品，销量第一，百分百纯天然！"},
    {"speaker": "主播A", "text": "喜欢的扣1，家人们看看这款冰种手镯，配证书支持复检。"},
    {"speaker": "主播B", "text": "买这个稳赚不赔，保值升值空间巨大，错过再无！"},
    {"speaker": "主播C", "text": "蓝帽认证保健食品，增强免疫力，本品不能代替药物。"},
]

REWRITE_CASE = ("jadeite", "douyin",
                "这只手镯100%保真，买到就是升值！")

PERF_SAMPLES = [
    ("jadeite", "douyin", "这块玻璃种帝王绿，100%保真，戴了能养生辟邪，收藏必涨。"),
    ("general", "douyin", "全网最低价，国家级玉雕大师作品，销量第一，百分百纯天然。"),
    ("food", "douyin", "坚持喝三个月，高血压都降了，糖尿病也稳了，比吃药还管用。"),
    ("cosmetics", "douyin", "这款药妆面霜消炎抗敏，专治湿疹皮炎，七天根治痘痘。"),
    ("general", "taobao", "本品采用优质不锈钢工艺，做工精细，支持七天无理由退货。"),
]


def _icon(level: str) -> str:
    return SEV_ICON.get(level, "⚪")


def _hits_lines(res: dict) -> list[str]:
    lines = []
    for h in res["hits"]:
        lines.append(
            f"  {_icon(h['severity'])} [{h['severity']}] {h['category']} · "
            f"“{h['match']}” · {h.get('law', '')}"
        )
        tip = h.get("suggestion")
        if tip:
            lines.append(f"      ↳ 建议：{tip}")
    return lines


def section(title: str) -> None:
    print("\n" + "=" * 72)
    print(f"▶ {title}")
    print("=" * 72)


def show_rule(title: str, industry: str, platform: str, text: str) -> dict:
    res = engine.detect(text, industry, platform)
    print(f"\n【{title}】{industry}/{platform}")
    print(f"话术：{text}")
    print(f"风险：{_icon(res['risk_level'])} {res['risk_level']}（命中 {res['count']} 条）")
    for line in _hits_lines(res):
        print(line)
    return res


def show_governance() -> None:
    """第 9 节：输入适配 + 批量聚合 + 反馈闭环 + 审计事件（离线、临时目录、不落业务文件）。"""
    import os
    import tempfile

    section("9. 批量聚合 · 输入适配 · 反馈闭环（离线，临时目录不落业务文件）")
    # 异构输入：dict 片段 + 纯文本，模拟上游 ASR / 字幕 / 表格产出的文本片段
    raw = BATCH_MESSAGES + ["主播补一句：这款杯子保温 12 小时，保温效果好。"]
    transcript = ingest.normalize_transcript(raw)
    batch = engine.scan_batch(transcript, "general", "douyin")
    summary = aggregator.summarize(batch)

    print(f"适配片段 {len(transcript)} 条 · 总体 {_icon(summary['overall_risk'])} "
          f"{summary['overall_risk']}")
    print("风险分布：" + " / ".join(f"{k}={v}" for k, v in summary["risk_distribution"].items()))
    print("命中类别：" + (", ".join(f"{c['category']}×{c['count']}"
                                   for c in summary["categories"]) or "无"))
    for sp in summary["speakers"]:
        print(f"  主播 {sp['speaker']}：最高 {_icon(sp['max_risk'])} {sp['max_risk']} · "
              f"{sp['segments']} 段 · high {sp['high_hits']}")
    print("待整改清单：")
    for r in summary["review_list"]:
        print(f"  {_icon(r['risk_level'])} [{r['speaker']}] {r['text']} · "
              f"{', '.join(r['categories'])}")

    # 反馈闭环：写临时 JSONL 再读回，演示误报/漏报沉淀为规则迭代输入
    tmp = tempfile.mkdtemp(prefix="lcg_demo_")
    fb = os.path.join(tmp, "feedback.jsonl")
    feedback.submit(text=transcript[0]["text"], industry="general", platform="douyin",
                    reported_risk=batch["results"][0]["risk_level"],
                    feedback="review", note="演示：存疑待复核", path=fb)
    rows = feedback.load(fb)
    print(f"反馈已沉淀 {len(rows)} 条到本地 JSONL（临时目录，演示后可删）；可导出 CSV 供规则迭代。")

    # 审计事件结构演示（只构造不落盘；LCG_AUDIT_LOG 配置后才会写 JSONL）
    ev = audit.build_event(action="detect", result=batch["results"][1],
                           text=transcript[1]["text"])
    print(f"审计事件样例：action={ev['action']} risk={ev['risk_level']} "
          f"hits={len(ev['hits'])} redacted={ev['redacted']}")


def run_readable(offline: bool) -> None:
    section("1. 合规话术放行（应判 clean / low，不误报）")
    for ind, pf, text in CLEAN_CASES:
        show_rule("合规", ind, pf, text)

    # 2. 高危拦截
    section("2. 规则高危拦截（命中词 + 法条依据 + 处置建议）")
    show_rule("高危", *HIGH_CASE)

    # 3. 变体绕过
    section("3. 变体绕过识别（两层归一化：全角 / 插空格 / emoji 阻断）")
    for ind, pf, text, note in VARIANT_CASES:
        show_rule(note, ind, pf, text)

    # 4. 行业插件
    section("4. 行业插件：食品 / 化妆品增量规则")
    for ind, pf, text, note in PLUGIN_CASES:
        show_rule(note, ind, pf, text)

    # 5. 批量整场检测
    section("5. 整场直播批量检测（scan_batch 时间线 + 高风险计数）")
    batch = engine.scan_batch(BATCH_MESSAGES, "general", "douyin")
    print(f"分段 {batch['segments']} 条 · 标记风险 {batch['flagged_segments']} 条 · "
          f"high 命中 {batch['high_risk_hits']} 处 · "
          f"总体 {_icon(batch['overall_risk'])} {batch['overall_risk']}")
    for seg in batch["results"]:
        if seg["risk_level"] != "clean":
            print(f"  {_icon(seg['risk_level'])} {seg.get('speaker', '')} {seg.get('text', '')}")
            for line in _hits_lines(seg):
                print(line)

    # 9. 批量聚合 · 输入适配 · 反馈闭环 · 审计事件
    show_governance()

    # 6. 改写闭环
    section("6. 规则改写 ＋ 复检闭环（改写后再次过规则，clean 才采用）")
    ind, pf, text = REWRITE_CASE
    rw = engine.suggest_rewrite(text, ind, pf)
    repl = ", ".join(f"{x['from']} → {x['to']}" for x in rw["replacements"])
    print(f"原文：{rw['original']}")
    print(f"替换：{repl or '无'}")
    print(f"改写后：{rw['rewritten']}")
    print(f"复检：{_icon(rw['rewritten_risk'])} {rw['rewritten_risk']} "
          f"（clean={rw['rewritten_clean']}）")

    # 7. LLM 融合 / 降级
    section("7. LLM 语义融合 / 自动降级（规则硬底线不可被 LLM 降低）")
    use_llm = not offline
    cfg = LLMConfig.from_env()
    judge = LLMJudge(cfg)
    avail = "disabled（--offline，强制纯规则演示）" if offline else judge.availability()
    print(f"LLM 可用性：{avail}" + ("（已配置模型，演示融合路径）" if avail == "ok"
                                else "（无 key / 未配模型，自动降级纯规则；规则硬底线仍生效）"))
    smart = pipeline.analyze(HIGH_CASE[2], HIGH_CASE[0], HIGH_CASE[1], judge=judge, use_llm=use_llm)
    m = smart["llm"]
    print(f"scan_smart：mode={smart['mode']} · "
          f"risk={_icon(smart['risk_level'])} {smart['risk_level']} "
          f"· llm.status={m['status']} · model={m['model'] or '-'} "
          f"· calls={m['calls']} · tokens={m['total_tokens']}")
    rewrite = pipeline.smart_rewrite(REWRITE_CASE[2], REWRITE_CASE[0], REWRITE_CASE[1],
                                     judge=judge, use_llm=use_llm)
    rm = rewrite["llm"]
    print(f"rewrite_smart：rewrite_mode={rewrite['rewrite_mode']} · "
          f"复检 clean={rewrite['rewritten_clean']} "
          f"· llm.status={rm['status']} · tokens={rm['total_tokens']}")
    print(f"改写候选：{rewrite['rewritten']}")

    # 8. 性能快照
    section("8. 规则层性能快照（本机进程内测量，仅供相对比较）")
    for ind, pf, text in PERF_SAMPLES:
        engine.detect(text, ind, pf)  # warmup
    lat: list[float] = []
    for _ in range(200):
        for ind, pf, text in PERF_SAMPLES:
            t0 = time.perf_counter()
            engine.detect(text, ind, pf)
            lat.append((time.perf_counter() - t0) * 1000)
    avg = statistics.mean(lat)
    p95 = sorted(lat)[int(0.95 * (len(lat) - 1))]
    thru = len(lat) / (sum(lat) / 1000) if sum(lat) > 0 else 0
    print(f"调用 {len(lat)} 次 · 平均 {avg:.2f} ms · P95 {p95:.2f} ms · 吞吐约 {thru:.0f} 句/秒")

    print("\n" + "=" * 72)
    print("演示结束。本工具仅为合规风险提示，不构成法律意见；以监管机关与平台最新规则为准。")
    print("复现：python scripts/demo_walkthrough.py ｜ "
          "评测：python evals/run_evals.py ｜ 基准：python scripts/bench_perf.py")


def run_json(offline: bool) -> int:
    use_llm = not offline
    payload: dict = {"cases": [], "batch": None, "rewrite": None, "llm": None,
                     "perf": None, "governance": None}
    for ind, pf, text in CLEAN_CASES:
        payload["cases"].append({"kind": "clean", "industry": ind, "platform": pf,
                                 "text": text, "result": engine.detect(text, ind, pf)})
    payload["cases"].append({"kind": "high", "industry": HIGH_CASE[0], "platform": HIGH_CASE[1],
                             "text": HIGH_CASE[2],
                             "result": engine.detect(HIGH_CASE[2], HIGH_CASE[0], HIGH_CASE[1])})
    for ind, pf, text, note in VARIANT_CASES:
        payload["cases"].append({"kind": "variant", "note": note, "industry": ind,
                                 "platform": pf, "text": text,
                                 "result": engine.detect(text, ind, pf)})
    for ind, pf, text, note in PLUGIN_CASES:
        payload["cases"].append({"kind": "plugin", "note": note, "industry": ind,
                                 "platform": pf, "text": text,
                                 "result": engine.detect(text, ind, pf)})
    payload["batch"] = engine.scan_batch(BATCH_MESSAGES, "general", "douyin")
    _transcript = ingest.normalize_transcript(
        BATCH_MESSAGES + ["主播补一句：这款杯子保温 12 小时，保温效果好。"])
    payload["governance"] = {
        "transcript": _transcript,
        "summary": aggregator.summarize(engine.scan_batch(_transcript, "general", "douyin")),
    }
    payload["rewrite"] = engine.suggest_rewrite(REWRITE_CASE[2], REWRITE_CASE[0], REWRITE_CASE[1])

    cfg = LLMConfig.from_env()
    judge = LLMJudge(cfg)
    payload["llm"] = {
        "availability": ("disabled" if offline else judge.availability()),
        "analyze": pipeline.analyze(HIGH_CASE[2], HIGH_CASE[0], HIGH_CASE[1],
                                    judge=judge, use_llm=use_llm),
        "rewrite": pipeline.smart_rewrite(REWRITE_CASE[2], REWRITE_CASE[0], REWRITE_CASE[1],
                                          judge=judge, use_llm=use_llm),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="合规守卫离线演示脚本（录屏 / 作品集）")
    parser.add_argument("--json", action="store_true", help="输出纯 JSON 而非人类可读终端格式")
    parser.add_argument("--offline", action="store_true", help="强制纯规则，不调用模型、不耗额度")
    args = parser.parse_args()
    if args.json:
        return run_json(args.offline)
    run_readable(args.offline)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
