# -*- coding: utf-8 -*-
"""pytest 共享引导：把项目根与 src/ 加入 sys.path，免 pip install -e 即可测试。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "src", ROOT):
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)
