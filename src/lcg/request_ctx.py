# -*- coding: utf-8 -*-
"""
lcg.request_ctx —— 请求级上下文（contextvar）。

HTTP 鉴权通过后，把当前请求归属的租户与计量器挂到上下文；pipeline 在检测 / 改写
结束后从上下文取回，把 LLM 层透传的 token 用量回填到配额计量。

边界：
  · 仅在同一 ASGI 请求上下文内有效；stdio 路径不设置上下文，回填自动跳过；
  · 上下文只持有租户 id 与计量器引用，不复制请求体；
  · 回填异常不阻断主流程，与计量层容错口径一致。
"""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # 避免与 tenant 模块循环导入
    from .tenant import UsageMeter


@dataclass(frozen=True)
class RequestContext:
    tenant_id: str
    meter: "UsageMeter"


_CTX: ContextVar[Optional[RequestContext]] = ContextVar(
    "lcg_request_ctx", default=None)


def set_request(ctx: Optional[RequestContext]) -> object:
    """写入请求上下文，返回 token 供 ``reset`` 还原。"""
    return _CTX.set(ctx)


def reset(token: object) -> None:
    """还原到上一层上下文（请求结束时调用）。"""
    _CTX.reset(token)  # type: ignore[arg-type]


def current() -> Optional[RequestContext]:
    """读取当前请求上下文；无 HTTP 租户归属时返回 ``None``。"""
    return _CTX.get()
