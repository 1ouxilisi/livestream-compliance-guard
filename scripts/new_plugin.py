# -*- coding: utf-8 -*-
"""
new_plugin.py —— 把「客户自己的违禁词表」在 3 分钟内接成行业插件包。

背景：核心包 rules/rules.v1.json 只有通用 + 翡翠规则，行业增量全部走
rules/plugins/*.json。本脚本把一份逗号分隔的词表变成结构合法、可被
lcg.rules_store 直接加载的插件包，写完立刻用 validate_plugin + load_payload
自检，并打印聚合后的规则总数。

用法：
  python scripts/new_plugin.py --list
  python scripts/new_plugin.py --industry skincare --name 护肤品 \
      --words "七天美白,永久脱毛,医美级@medium" --dry-run
  python scripts/new_plugin.py --industry skincare --name 护肤品 \
      --words "七天美白,永久脱毛,医美级@medium"

约定：
  · 一个词一条规则：命中归因清楚，severity 可逐词不同（词后加 @low/@medium/@high）。
  · 文件名不能以下划线开头（_template.json 等视为模板，不参与加载）。
  · 规则 scope 必须等于 industry:<industry>，否则 load_payload 直接报错。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from lcg import engine, rules_store  # noqa: E402

INDUSTRY_RE = re.compile(r"^[a-z][a-z0-9_]{1,23}$")
RESERVED = {"all", "platform", "jadeite"}  # 内置在核心包或保留给 scope 前缀
SEV = ("low", "medium", "high")

DEFAULT_TIP = (
    "命中「{word}」属未举证的绝对化/功效宣称：改为可举证的客观表述"
    "（成分、检测报告、适用范围），删去疗效与时限承诺；强监管行业上线前须法务复核。"
)


def fail(msg: str) -> int:
    print(f"[FAIL] {msg}", file=sys.stderr)
    return 1


def split_words(raw: str) -> list[tuple[str, str]]:
    """把 "词,词@medium" 拆成 [(词, severity)]，去重且保持顺序。"""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for chunk in re.split(r"[,，]", raw):
        token = chunk.strip()
        if not token:
            continue
        sev = "high"
        word = token
        if "@" in token:
            head, _, tail = token.rpartition("@")
            word, sev = head.strip(), tail.strip().lower()
            if sev not in SEV:
                raise ValueError(f"「{word}」的 severity 非法：{sev!r}（只能是 {'/'.join(SEV)}）")
        if not word:
            continue
        if word in seen:
            continue
        seen.add(word)
        out.append((word, sev))
    if not out:
        raise ValueError("--words 为空：至少要有一个词")
    return out


def build_payload(args: argparse.Namespace, words: list[tuple[str, str]]) -> dict:
    law = args.law
    rules = [
        {
            "scope": f"industry:{args.industry}",
            "category": args.category or f"{args.name}-未举证功效宣称",
            "severity": sev,
            "law": law,
            "words": [word],
            "patterns": [],
            "patterns_compact": [],
            "tip": args.tip or DEFAULT_TIP.format(word=word),
        }
        for word, sev in words
    ]
    return {
        "meta": {
            "package": args.industry,
            "format": "lcg-plugin/1",
            "language": "zh-CN",
            "version": "v1.0",
            "industry": args.industry,
            "rule_count": len(rules),
            "replacement_count": len(words),
            "note": args.note or (
                f"{args.name}行业插件包（new_plugin.py 生成）。"
                f"词表来源与法条依据须由使用者核实：本包只做风险提示，不替代法务判断。"
            ),
            "sources": [{"law": law, "article": "", "url": args.source_url}],
        },
        "rules": rules,
        "replacements": {word: args.replacement for word, _ in words},
    }


def print_packages() -> int:
    packages = rules_store.meta().get("packages", [])
    core = rules_store.meta()
    print(f"核心包：{core.get('core_rule_count')} 规则 / {core.get('core_replacement_count')} 替换")
    if not packages:
        print("当前没有加载任何插件包（rules/plugins/*.json 且文件名不以 _ 开头）")
        return 0
    print("已加载插件包：")
    for p in packages:
        print(f"  - {p['package']:<14} industry={p['industry']:<10} "
              f"{p['rule_count']} 规则 / {p['replacement_count']} 替换  ({p['version']})")
    print("\n未加载（下划线前缀，仅模板）文件：")
    for path in sorted(rules_store.PLUGINS_DIR.glob("_*.json")):
        print(f"  - {path.name}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="生成行业插件包（rules/plugins/<industry>.json）并自检",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--list", action="store_true", help="列出已加载 / 未加载的插件包后退出")
    parser.add_argument(
        "--industry", help="行业标识：小写英文 2-24 位，如 skincare / medical_device")
    parser.add_argument("--name", help="行业中文名，如 护肤品；用于默认 category 与 note")
    parser.add_argument("--words", help="逗号分隔词表，词后可加 @low/@medium/@high，默认 high")
    parser.add_argument("--category", help="风险类别，默认「<name>-未举证功效宣称」")
    parser.add_argument("--law", default="《广告法》第4条、第28条（上线前须逐条核实）",
                        help="法条依据文本，写进每条规则与 meta.sources")
    parser.add_argument("--source-url", default="https://flk.npc.gov.cn",
                        help="法条来源链接，默认国家法律法规数据库")
    parser.add_argument("--tip", help="处置建议模板，可用 {word} 占位")
    parser.add_argument("--replacement", default="（改为客观、可举证的表述）",
                        help="替换建议，写进 replacements")
    parser.add_argument("--note", help="meta.note，说明词表来源与核实状态")
    parser.add_argument("--dry-run", action="store_true", help="只打印 JSON，不写盘")
    parser.add_argument("--force", action="store_true", help="覆盖已存在的同名插件包")
    args = parser.parse_args()

    if args.list:
        return print_packages()

    for req in ("industry", "name", "words"):
        if not getattr(args, req):
            return fail(f"缺少必填参数 --{req}（可先跑 --list 看现状）")

    industry = args.industry.strip().lower()
    if not INDUSTRY_RE.match(industry):
        return fail(f"--industry 非法：{industry!r}，要求小写英文 2–24 位，允许数字与下划线")
    if industry in RESERVED:
        return fail(f"--industry 不能用保留名：{industry}（{'/'.join(sorted(RESERVED))}）")

    try:
        words = split_words(args.words)
    except ValueError as exc:
        return fail(str(exc))

    payload = build_payload(args, words)
    target = rules_store.PLUGINS_DIR / f"{industry}.json"

    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print(f"\n[dry-run] 未写盘；去掉 --dry-run 即写入 {target.relative_to(ROOT)}")
        return 0

    if target.exists() and not args.force:
        return fail(f"{target.name} 已存在；确认要覆盖请加 --force（或换一个 --industry）")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    try:
        rules_store.validate_plugin(payload, target.name)
        rules_store.load_payload.cache_clear()
        agg = rules_store.load_payload()
    except ValueError as exc:
        return fail(f"写入后校验失败：{exc}")

    meta = agg["meta"]
    print(f"[OK] 已写入 {target.relative_to(ROOT)}（{len(words)} 条规则 / "
          f"{len(payload['replacements'])} 条替换）")
    print(f"[OK] 聚合：核心 {meta['core_rule_count']} + 插件 {len(meta['packages'])} 个 "
          f"→ 全局 {meta['rule_count']} 规则 / {meta['replacement_count']} 替换")

    probe = f"这款产品{words[0][0]}，效果很好。"
    res = engine.detect(probe, industry, "douyin")
    print(f"[OK] 自检命中：industry={industry} 探针句 → {res['risk_level']}（{res['count']} 条）")
    print("\n下一步：")
    print("  python scripts/export_rules.py --check   # CI 同款规则守门")
    print("  python -m pytest -q                      # 全套测试")
    print(f"  调用时记得把 industry 传成 {industry!r}，否则该包不会被激活")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
