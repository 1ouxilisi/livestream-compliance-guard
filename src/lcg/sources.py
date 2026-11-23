# -*- coding: utf-8 -*-
"""
lcg.sources —— 可插拔输入源骨架（零第三方依赖，不含真实 ASR/OCR 调用）。

定位：上游语音转写（ASR）、图像文字识别（OCR）、字幕文件、表格等产出文本片段后，
由一个“输入源”统一交付给检测链路。本模块只定义接入协议与内存实现；**不内置任何
真实语音/图像识别模型，也不发起网络请求**。

接入方式（将来对接真实服务时）：
  · 实现 ``TranscriptSource`` 协议的 ``fetch()``，返回原始片段列表（形态见 ``lcg.ingest``）；
  · 在服务装配处把该源传给 ``load_source``，归一后交给 ``engine.scan_batch`` /
    ``pipeline``；
  · 真实后端的 provider / base_url / api_key 由部署方在环境变量或 Secret 中注入，
    本骨架不保存、不转发凭证。

当前内置实现：
  · ``ListSource``：直接持有静态片段列表（内存 / 测试 / 回放用）；
  · ``StubSource``：脚本化桩，按预设片段返回，供演示与离线测试，不接外部服务；
  · ``StubRecognizer``：ASR / OCR 识别桩，回放预设片段，不调用真实识别模型。
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable

from . import ingest


@runtime_checkable
class TranscriptSource(Protocol):
    """输入源协议：任何实现 ``fetch`` 的对象都可被 ``load_source`` 接受。"""

    def fetch(self) -> List[Dict[str, Any]]:
        """返回原始片段列表（形态异构均可，交由 ingest 归一）。"""
        ...


class ListSource:
    """静态片段源：包装一个列表或可调用对象，每次 fetch 重新归一。"""

    def __init__(self, items: Any) -> None:
        self._items = items

    def fetch(self) -> List[Dict[str, Any]]:
        items = self._items() if isinstance(self._items, Callable) else self._items
        return ingest.normalize_transcript(items)


class StubSource:
    """脚本化桩源：按预设片段返回，用于演示 / 离线测试，不接触外部服务。"""

    def __init__(self, segments: Optional[List[Dict[str, Any]]] = None) -> None:
        self._segments = segments or []

    def fetch(self) -> List[Dict[str, Any]]:
        return ingest.normalize_transcript(self._segments)

    def add(self, item: Dict[str, Any]) -> None:
        self._segments.append(item)


def load_source(source: Any) -> List[Dict[str, Any]]:
    """把输入源统一归一为检测契约片段列表。

    接受：``TranscriptSource`` 实例、片段列表 / 元组、可调用对象（返回片段列表）。
    """
    if isinstance(source, TranscriptSource):
        raw = source.fetch()
    elif isinstance(source, Callable):
        raw = source()
    else:
        raw = source
    return ingest.normalize_transcript(raw)


@runtime_checkable
class Recognizer(Protocol):
    """识别适配器协议：把音频 / 图片等媒体负载转为文本片段。

    与 ``TranscriptSource`` 的区别：Source 交付**已经转写好的文本片段**；
    Recognizer 消费**媒体负载**（音频路径 / 字节、图片帧 / 引用等），由真实
    ASR / OCR 后端识别成文本后，再交 ``ingest`` 归一。本骨架不内置任何真实
    识别模型，也不发起网络请求。
    """

    def recognize(self, payload: Any) -> List[Dict[str, Any]]:
        """返回识别出的原始片段列表（形态异构均可，交由 ingest 归一）。"""
        ...


class StubRecognizer:
    """脚本化识别桩：按预设片段返回，用于演示 / 离线测试，不接触外部识别服务。

    真实 ASR / OCR 后端由部署方实现本协议；其 provider / base_url / api_key
    从环境变量或 Secret 注入，桩与本骨架都不保存、不转发凭证。
    """

    def __init__(self, segments: Optional[List[Dict[str, Any]]] = None) -> None:
        self._segments: List[Dict[str, Any]] = list(segments or [])

    def recognize(self, payload: Any = None) -> List[Dict[str, Any]]:
        # 桩忽略媒体负载，直接回放预设片段；真实实现应据此调用识别服务。
        _ = payload
        return ingest.normalize_transcript(self._segments)

    def add(self, item: Dict[str, Any]) -> None:
        self._segments.append(item)
