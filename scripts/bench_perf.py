# -*- coding: utf-8 -*-
"""
bench_perf.py —— 规则层性能与 LLM 层成本基准（零第三方依赖，可离线跑规则层）。

测什么：
  · 规则层单句检测延迟（avg / P50 / P95 / max）与吞吐（句/秒）——确定性、可复现；
  · 批量 scan_batch 总耗时与单句均摊；
  · LLM 层：若模型可用，抽样跑 analyze，记录 mode / status / 单次墙钟延迟 / 调用次数；
    不可用则标注 skipped，不计入规则层成绩。

口径与边界（务必随报告一起阅读）：
  · 规则层延迟为本机单次进程内测量，受机器负载影响，仅供相对比较，不代表生产 SLA；
  · LLM 层 usage 已由后端解析并透传，报告汇总输入/输出/总 token；单价未配置时只报 token 量；
  · 在线 LLM 延迟受网络与模型排队影响，波动大，不作为离线门禁。

运行：python scripts/bench_perf.py
"""
from __future__ import annotations

import datetime
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from lcg import (  # noqa: E402
    engine,
    pipeline,
    rules_store,  # noqa: E402
)
from lcg.llm import LLMConfig, LLMJudge  # noqa: E402

REPORTS = ROOT / "reports"

# 代表性样本：覆盖 high / medium / low / clean，跨行业与平台。
SAMPLES = [
    ("jadeite", "douyin", "这块玻璃种帝王绿，100%保真，戴了能养生辟邪，收藏必涨。"),
    ("general", "douyin", "全网最低价，国家级玉雕大师作品，销量第一，百分百纯天然。"),
    ("general", "taobao", "这个料子买了稳赚不赔，保值升值空间巨大，错过再无。"),
    ("food", "douyin", "坚持喝三个月，高血压都降了，糖尿病也稳了，比吃药还管用。"),
    ("cosmetics", "douyin", "这款药妆面霜消炎抗敏，专治湿疹皮炎，七天根治痘痘。"),
    ("general", "kuaishou", "想要的加薇信 qq8899123 私下发货。"),
    ("jadeite", "douyin", "这款手镯颜色很漂亮，种水不错，属于玻璃种，性价比很高。"),
    ("general", "douyin", "家人们宝宝们看过来，这款宝贝亏本冲量白送啦！"),
    ("general", "taobao", "本品采用优质不锈钢工艺，做工精细，支持七天无理由退货。"),
    ("jadeite", "douyin", "这是天然翡翠A货吊坠，配有鉴定证书，支持复检，喜欢可下单。"),
    ("food", "douyin", "蓝帽认证保健食品，增强免疫力，每日两粒，本品不能代替药物。"),
    ("cosmetics", "douyin", "这款面霜主打玻尿酸保湿补水，质地清爽不黏腻，干皮上脸很滋润。"),
]

REPEAT = 200          # 规则层每句重复轮数
BATCH_SIZE = 120      # 批量压测句数（样本循环补足）
LLM_SAMPLE = 3        # LLM 抽样句数


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(round(q * (len(ordered) - 1))))
    return ordered[idx]


def bench_rules() -> dict:
    """规则层单句延迟与吞吐。"""
    per_sentence: list[float] = []
    all_lat: list[float] = []
    # warmup
    for ind, plat, text in SAMPLES:
        engine.detect(text, ind, plat)

    for ind, plat, text in SAMPLES:
        lat: list[float] = []
        for _ in range(REPEAT):
            t0 = time.perf_counter()
            engine.detect(text, ind, plat)
            lat.append((time.perf_counter() - t0) * 1000)
        per_sentence.append(statistics.mean(lat))
        all_lat.extend(lat)

    total_calls = len(all_lat)
    total_ms = sum(all_lat)
    return {
        "calls": total_calls,
        "avg_ms": statistics.mean(all_lat),
        "p50_ms": _percentile(all_lat, 0.50),
        "p95_ms": _percentile(all_lat, 0.95),
        "max_ms": max(all_lat),
        "throughput_per_s": total_calls / (total_ms / 1000) if total_ms > 0 else 0.0,
    }


def bench_batch() -> dict:
    messages = []
    for i in range(BATCH_SIZE):
        ind, plat, text = SAMPLES[i % len(SAMPLES)]
        messages.append({"speaker": f"主播{i % 3}", "text": text})
    t0 = time.perf_counter()
    res = engine.scan_batch(messages, "general", "douyin")
    elapsed = (time.perf_counter() - t0) * 1000
    return {
        "messages": len(messages),
        "total_ms": elapsed,
        "per_message_ms": elapsed / len(messages),
        "flagged": res["flagged_segments"],
        "high": res["high_risk_hits"],
    }


def bench_llm() -> dict:
    """LLM 层抽样；不可用时返回 skipped，不影响规则层结论。

    usage 由后端 ``comp.usage`` 解析并经 JudgeResult/pipeline meta 透传；
    单价（每百万 token，币种随 provider 账单）未配置时只汇总 token 量、不报金额。
    """
    cfg = LLMConfig.from_env()
    judge = LLMJudge(cfg)
    avail = judge.availability()
    if avail != "ok":
        return {"status": "skipped", "reason": avail, "samples": 0, "runs": []}

    runs = []
    tot = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for ind, plat, text in SAMPLES[:LLM_SAMPLE]:
        t0 = time.perf_counter()
        r = pipeline.analyze(text, ind, plat, judge=judge)
        lat = (time.perf_counter() - t0) * 1000
        meta = r["llm"]
        pt = meta.get("prompt_tokens", 0)
        ct = meta.get("completion_tokens", 0)
        tt = meta.get("total_tokens", 0)
        tot["prompt_tokens"] += pt
        tot["completion_tokens"] += ct
        tot["total_tokens"] += tt
        runs.append({
            "mode": r["mode"],
            "status": meta["status"],
            "model": meta["model"],
            "calls": meta["calls"],
            "prompt_tokens": pt,
            "completion_tokens": ct,
            "total_tokens": tt,
            "latency_ms": round(lat, 1),
        })

    price_in = cfg.price_input_per_mtok
    price_out = cfg.price_output_per_mtok
    cost = None
    if price_in > 0 or price_out > 0:
        cost = (tot["prompt_tokens"] / 1_000_000) * price_in \
            + (tot["completion_tokens"] / 1_000_000) * price_out
    return {
        "status": "ok",
        "model_primary": cfg.model_primary,
        "model_fallback": cfg.model_fallback,
        "timeout_s": cfg.timeout,
        "samples": len(runs),
        "runs": runs,
        "totals": tot,
        "price_in_per_mtok": price_in,
        "price_out_per_mtok": price_out,
        "cost": cost,
    }


def main() -> int:
    rules = bench_rules()
    batch = bench_batch()
    llm = bench_llm()
    meta = rules_store.meta()

    today = datetime.date.today().isoformat()
    L = [
        "# PERF · 性能与成本基准",
        "",
        f"- 生成日期：{today}",
        f"- 规则版本：{meta.get('version', '?')}；样本 {len(SAMPLES)} 条；规则层重复 {REPEAT} 轮",
        "- 规则层为进程内本机测量，仅作相对比较，不代表生产 SLA。",
        "",
        "## 规则层单句检测",
        "",
        "| 指标 | 数值 |",
        "|---|---|",
        f"| 检测调用次数 | {rules['calls']} |",
        f"| 平均延迟 | {rules['avg_ms']:.2f} ms |",
        f"| P50 | {rules['p50_ms']:.2f} ms |",
        f"| P95 | {rules['p95_ms']:.2f} ms |",
        f"| 最大延迟 | {rules['max_ms']:.2f} ms |",
        f"| 吞吐 | {rules['throughput_per_s']:.0f} 句/秒 |",
        "",
        "## 批量检测（scan_batch）",
        "",
        "| 指标 | 数值 |",
        "|---|---|",
        f"| 消息条数 | {batch['messages']} |",
        f"| 总耗时 | {batch['total_ms']:.1f} ms |",
        f"| 单句均摊 | {batch['per_message_ms']:.2f} ms |",
        f"| 命中分段 | {batch['flagged']}（high 命中 {batch['high']}） |",
        "",
        "## LLM 语义层（抽样）",
        "",
    ]

    if llm["status"] == "ok":
        L += [
            f"- 主力模型：`{llm['model_primary']}`；"
            f"兜底：`{llm['model_fallback'] or '无'}`；超时 {llm['timeout_s']}s",
            "",
            "| 样本 | mode | 状态 | 模型 | 调用 | 输入 token | 输出 token | 总 token | 延迟 ms |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for i, r in enumerate(llm["runs"], 1):
            L.append(
                f"| {i} | {r['mode']} | {r['status']} | {r['model']} "
                f"| {r['calls']} | {r['prompt_tokens']} | {r['completion_tokens']} "
                f"| {r['total_tokens']} | {r['latency_ms']} |"
            )
        tot = llm["totals"]
        L += [
            "",
            f"- 抽样合计：输入 {tot['prompt_tokens']} tokens，"
            f"输出 {tot['completion_tokens']} tokens，"
            f"总计 {tot['total_tokens']} tokens（{llm['samples']} 条样本）。",
        ]
        if llm["cost"] is not None:
            L.append(
                f"- 估算成本：输入单价 {llm['price_in_per_mtok']}/百万 token，"
                f"输出单价 {llm['price_out_per_mtok']}/百万 token，"
                f"本批约 {llm['cost']:.4f}（币种随 provider 账单）。"
            )
        else:
            L.append(
                "- 单价未配置：设置 `LCG_PRICE_INPUT_PER_MTOK` / `LCG_PRICE_OUTPUT_PER_MTOK`"
                "（每百万 token 单价）后，报告自动给出估算金额；当前仅汇总 token 量。"
            )
    else:
        L += [
            f"- 状态：skipped（`{llm['reason']}`）；"
            "未配置可用模型，本批不含 LLM 延迟与成本数据。"
        ]

    L += [
        "",
        "## 成本口径",
        "",
        "- 规则层：零第三方模型调用，仅本机 CPU 成本，单句延迟见上表。",
        "- LLM 层：每条话术最多 1 次检测调用；命中风险时改写另计 1 次。",
        "- 单句成本 ≈（输入 tokens ÷ 100 万）× 输入单价 ＋（输出 tokens ÷ 100 万）× 输出单价；"
        "usage 已由后端 `comp.usage` 解析并经 meta 透传，"
        "单价经环境变量配置，未配置时只报 token 量、不报金额。",
        "",
        "> 仅为合规风险提示，不构成法律意见；性能数据随机器与负载波动。",
        "",
    ]

    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "PERF.md").write_text("\n".join(L), encoding="utf-8")

    print(f"[PERF] 规则层 avg={rules['avg_ms']:.2f}ms "
          f"P95={rules['p95_ms']:.2f}ms 吞吐={rules['throughput_per_s']:.0f}/s")
    print(f"[PERF] 批量 {batch['messages']} 句 {batch['total_ms']:.1f}ms；LLM: {llm['status']}")
    print("[OK] 已写出 reports/PERF.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
