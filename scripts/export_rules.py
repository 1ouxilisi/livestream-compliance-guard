# -*- coding: utf-8 -*-
"""
export_rules.py —— 规则库（核心包 + 行业插件包）的规范化与一致性校验器。

事实源关系：
  rules/rules.v1.json 与 rules/plugins/*.json 是**唯一事实源**，由 lcg.rules_store
  在运行时直接加载；本脚本不从任何 Python 源码导出规则，只负责：
    · 无参数：逐文件读取 JSON -> 重算各自 meta 计数 -> 以统一格式规范化写回；
    · --check（CI 使用）：校验核心包与每个插件包均可加载、结构合法、meta 计数一致、
      规范化结果与磁盘逐字一致，并验证聚合视图可加载；任一不满足则退出码 1。

用法：
  python scripts/export_rules.py          # 规范化并写回核心包与全部插件包
  python scripts/export_rules.py --check  # CI 守门：只校验不写
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from lcg.rules_store import (  # noqa: E402
    RULES_PATH,
    core_payload,
    load_payload,
    plugin_payloads,
)


def normalize_payload(data: dict) -> dict:
    """返回重算了本文件 meta 计数、字段顺序稳定的副本（核心包/插件包通用）。"""
    payload = dict(data)
    meta = dict(data.get("meta", {}))
    meta["rule_count"] = len(data["rules"])
    meta["replacement_count"] = len(data["replacements"])
    payload["meta"] = meta
    return payload


def render(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    agg = load_payload()  # 聚合加载即触发核心包与全部插件包的结构/计数校验
    targets = [(RULES_PATH, core_payload())] + plugin_payloads()
    check = "--check" in sys.argv
    rc = 0

    for path, data in targets:
        text = render(normalize_payload(data))
        n_rules = len(data["rules"])
        n_repl = len(data["replacements"])
        if check:
            if not path.exists():
                print(f"[FAIL] {path.name} 不存在")
                rc = 1
                continue
            if path.read_text(encoding="utf-8") != text:
                print(f"[FAIL] {path.name} 未规范化或 meta 计数漂移，"
                      f"请运行 python scripts/export_rules.py")
                rc = 1
            else:
                print(f"[OK] {path.name} 规范一致（{n_rules} 条规则，{n_repl} 条替换建议）")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            print(f"[OK] 已规范化写出 {path.name}（{n_rules} 条规则，{n_repl} 条替换建议）")

    m = agg["meta"]
    pkgs = ", ".join(f"{p['package']} {p['rule_count']}/{p['replacement_count']}"
                     for p in m.get("packages", [])) or "无插件"
    summary = (f"聚合：核心 {m['core_rule_count']} 规则/{m['core_replacement_count']} 替换；"
               f"插件[{pkgs}]；全局 {m['rule_count']} 规则/{m['replacement_count']} 替换")
    if check:
        print("[FAIL] 存在未规范化文件" if rc else f"[OK] {summary}")
    else:
        print(f"[OK] {summary}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
