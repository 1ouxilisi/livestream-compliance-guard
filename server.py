# -*- coding: utf-8 -*-
"""
livestream-compliance-guard / 直播电商合规守卫 MCP
----------------------------------------------------
**向后兼容入口（shim）**。规则引擎已重构进 ``src/lcg`` 包，且以
``rules/rules.v1.json`` 为唯一事实源。本文件保留在仓库根，仅为：

  1. re-export 公共 API，保证旧脚本/客户端 ``import server`` 行为不变；
  2. 直接运行时启动 stdio MCP（``python server.py``，需 pip install mcp）；
  3. 零依赖自测 ``python server.py --selftest``；
  4. 打印版本 ``python server.py --version``。

新代码请直接使用 ``lcg.engine`` / ``lcg.server_stdio``。
本工具只做风险提示，不构成法律意见；最终以监管机关与平台最新规则为准。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 无需 pip install -e 即可 import src/lcg
_SRC = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(_SRC))

from lcg import (  # noqa: E402
    __version__,  # noqa: E402
    engine,  # noqa: F401  # re-export，兼容旧客户端 `server.engine`
    pipeline,  # noqa: F401  # re-export，兼容旧客户端 `server.pipeline`
)
from lcg.engine import detect, get_rules, scan_batch, suggest_rewrite  # noqa: E402,F401
from lcg.models import SEV_ORDER  # noqa: E402,F401
from lcg.pipeline import analyze, smart_rewrite  # noqa: E402,F401


def _selftest() -> None:
    samples = [
        ("家人们这块玻璃种帝王绿，100%保真，戴了能养生辟邪，收藏必涨，加微信私下交易，今天最后一天！",
         "jadeite", "douyin"),
        ("这是天然翡翠A货吊坠，配有鉴定证书，支持复检，喜欢可在直播间下单。", "jadeite", "douyin"),
        ("本品采用优质不锈钢工艺，做工精细，支持七天无理由退货。", "general", "taobao"),
    ]
    for text, ind, plat in samples:
        print("=" * 70)
        print("TEXT:", text)
        print(json.dumps(detect(text, ind, plat), ensure_ascii=False, indent=2))
    print("=" * 70)
    print("REWRITE:", json.dumps(suggest_rewrite(samples[0][0]), ensure_ascii=False, indent=2))
    print("=" * 70)
    smart = analyze(samples[0][0], "jadeite", "douyin", use_llm=True)
    print("SMART:", "mode=", smart["mode"], "| llm.status=", smart["llm"]["status"],
          "| risk=", smart["risk_level"], "| hits=", smart["count"])
    assert smart["risk_level"] == "high", "硬底线失效：高危句融合后必须仍为 high"
    assert "mode" in smart and "llm" in smart
    print("[OK] 语义融合入口可用（未配置 key 时 mode=rules_only，规则硬底线生效）")


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--selftest", action="store_true", help="不启动MCP，仅自测规则")
    parser.add_argument("--version", action="store_true", help="打印版本号并退出")


try:
    from lcg.server_stdio import mcp as _mcp  # noqa: E402

    def main() -> None:
        parser = argparse.ArgumentParser(
            description="livestream-compliance-guard MCP server (stdio)")
        _add_common_args(parser)
        args = parser.parse_args()
        if args.version:
            print(__version__)
        elif args.selftest:
            _selftest()
        else:
            _mcp.run(transport="stdio")

except ImportError:  # 未安装 mcp 时仍可零依赖自测 / 看版本
    def main() -> None:
        parser = argparse.ArgumentParser(description="livestream-compliance-guard (rule core only)")
        _add_common_args(parser)
        args = parser.parse_args()
        if args.version:
            print(__version__)
        elif args.selftest:
            _selftest()
        else:
            print("未安装 mcp 包，先运行: pip install -r requirements.txt  ；"
                  "规则自测: python server.py --selftest")


if __name__ == "__main__":
    main()
