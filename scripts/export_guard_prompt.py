# -*- coding: utf-8 -*-
"""
export_guard_prompt.py —— 把检测系统提示 `lcg.llm.DETECT_SYSTEM` 导出为 promptfoo 用的 prompt 文件。

为什么需要：
  promptfoo 的固定用例若只发送待审话术，测的是**裸模型**，不是本项目的守卫本体——
  裸模型会顺从越狱、直接写出违规广告词，与产品行为无关。
  因此这里把检测系统提示 + 待审话术占位符拼成一份 prompt 文件，让 promptfoo 测到
  「系统提示约束下的模型行为」，与 `lcg.pipeline.analyze` 的真实链路一致。

产物：`evals/prompts/guard_prompt.txt`（由本脚本生成，勿手改；DETECT_SYSTEM 变更后重跑本脚本）

运行：python scripts/export_guard_prompt.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from lcg.llm import DETECT_SYSTEM, PROMPT_VERSION  # noqa: E402

OUT = ROOT / "evals" / "prompts" / "guard_prompt.txt"

TAIL = (
    "\n\n【待审话术】\n{{text}}\n\n"
    "请按上述 JSON 格式输出判定结果，不要输出任何解释或 markdown。"
)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    body = DETECT_SYSTEM + TAIL
    OUT.write_text(body, encoding="utf-8", newline="\n")
    print(f"[OK] 已写出 {OUT.relative_to(ROOT)}"
          f"（prompt_version={PROMPT_VERSION}，{len(body)} 字符）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
