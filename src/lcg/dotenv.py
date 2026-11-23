# -*- coding: utf-8 -*-
"""
lcg.dotenv —— 极简 ``.env`` 加载器（仅标准库，规则核心保持零第三方依赖）。

为什么需要它：``LLMConfig.from_env`` 只读取进程环境变量；而 README /
``.env.example`` 引导用户“复制 .env 填 key 后直接运行”。若不显式加载 .env，
新环境会一直停在 ``no_key`` 降级。本模块在 LLM 可选层被导入时补做一次本地
``.env`` 解析。

约定：
  · 只注入当前进程里**尚未设置**的变量；已存在的环境变量 / 平台 Secret 优先，不覆盖；
  · 不解析引号嵌套、不做 shell 展开，满足本项目简单 KEY=VALUE 配置即可；
  · 文件缺失或解析失败均静默跳过，不影响纯规则路径运行。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List


def _project_root() -> Path:
    """本文件位于 ``<root>/src/lcg/dotenv.py``，向上三级即项目根。"""
    return Path(__file__).resolve().parent.parent.parent


def _parse_line(line: str) -> tuple[str, str] | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("export "):
        line = line[len("export "):].strip()
    if "=" not in line:
        return None
    key, _, value = line.partition("=")
    key = key.strip()
    value = value.strip()
    # 剥离成对的首尾引号
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    if not key:
        return None
    return key, value


def load_dotenv(dotenv_path: str | os.PathLike | None = None) -> List[str]:
    """加载项目根 ``.env`` 到进程环境变量，返回本次新注入的键名列表。"""
    path = Path(dotenv_path) if dotenv_path else _project_root() / ".env"
    loaded: List[str] = []
    if not path.is_file():
        return loaded
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return loaded
    for raw in lines:
        parsed = _parse_line(raw)
        if not parsed:
            continue
        key, value = parsed
        # 已有进程环境变量优先（平台 Secret / 显式导出不被 .env 覆盖）
        if key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    return loaded
