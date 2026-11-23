# -*- coding: utf-8 -*-
"""
lcg.rules_store —— 规则库加载层（零第三方依赖）。

事实源布局（M5 起插件化）：
  rules/rules.v1.json         核心包：meta + scope=all 通用规则 + 平台规则 + jadeite 行业规则
  rules/plugins/<name>.json   行业插件包：meta(package/industry/version/sources)
                              + rules + replacements
核心包与各插件包均为语言无关 JSON，可被 Python 与未来 TS/Cloudflare 运行时共用。
本模块只负责加载、校验、按行业/平台筛选与聚合，不包含任何判定逻辑。
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Tuple


# 规则目录按以下顺序解析，兼容三种运行布局：
#   1. 包内数据（wheel / 安装后，lcg/rules 随包打入）；
#   2. 源码布局（src/lcg/rules_store.py -> 项目根/rules，PYTHONPATH=src 或仓库直跑）；
#   3. 进程工作目录（Docker 整仓拷贝到 /app 后从 cwd 运行）。
def _candidate_rules_dirs() -> List[Path]:
    here = Path(__file__).resolve()
    candidates: List[Path] = [here.parents[2] / "rules", Path.cwd() / "rules"]
    try:
        from importlib.resources import files

        candidates.insert(0, Path(str(files("lcg") / "rules")))
    except Exception:
        pass
    return candidates


def _resolve_rules_dir() -> Path:
    for directory in _candidate_rules_dirs():
        if (directory / "rules.v1.json").exists():
            return directory
    # 均未命中时回退源码布局，保留原有“文件缺失”报错路径。
    return Path(__file__).resolve().parents[2] / "rules"


RULES_DIR = _resolve_rules_dir()
RULES_PATH = RULES_DIR / "rules.v1.json"
PLUGINS_DIR = RULES_DIR / "plugins"

_REQUIRED_RULE_KEYS = ("scope", "category", "severity", "law", "words", "patterns", "tip")
_SEV = ("low", "medium", "high")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_rules(rules: Any, where: str) -> None:
    if not isinstance(rules, list):
        raise ValueError(f"{where} 缺少合法的 rules 数组")
    for i, r in enumerate(rules):
        missing = [k for k in _REQUIRED_RULE_KEYS if k not in r]
        if missing:
            raise ValueError(f"{where} 第 {i} 条规则缺少字段：{missing}")
        if r["severity"] not in _SEV:
            raise ValueError(f"{where} 第 {i} 条规则 severity 非法：{r['severity']!r}")


def validate_core(data: Dict[str, Any]) -> None:
    """校验核心包 rules.v1.json 自身结构与计数（不涉及插件）。"""
    if not isinstance(data, dict) or "rules" not in data or "replacements" not in data:
        raise ValueError("rules.v1.json 结构非法：缺少 rules 或 replacements 顶层键")
    _check_rules(data["rules"], "rules.v1.json")
    meta = data.get("meta", {})
    if meta.get("rule_count") not in (None, len(data["rules"])):
        raise ValueError(
            "核心 meta.rule_count 与核心 rules 条数不一致，"
            "请运行 scripts/export_rules.py")
    if meta.get("replacement_count") not in (None, len(data["replacements"])):
        raise ValueError("核心 meta.replacement_count 与核心 replacements 条数不一致")


def validate_plugin(data: Dict[str, Any], where: str) -> None:
    """校验行业插件包：meta 需含 package/industry，规则 scope 必须与 industry 一致。"""
    if not isinstance(data, dict) or "rules" not in data or "replacements" not in data:
        raise ValueError(f"{where} 结构非法：缺少 rules 或 replacements 顶层键")
    _check_rules(data["rules"], where)
    meta = data.get("meta")
    if not isinstance(meta, dict) or not meta.get("package") or not meta.get("industry"):
        raise ValueError(f"{where} meta 需包含 package 与 industry")
    industry = meta["industry"]
    for i, r in enumerate(data["rules"]):
        if r["scope"] != f"industry:{industry}":
            raise ValueError(f"{where} 第 {i} 条规则 scope 必须为 industry:{industry}")
    if meta.get("rule_count") not in (None, len(data["rules"])):
        raise ValueError(f"{where} meta.rule_count 与本包 rules 条数不一致")
    if meta.get("replacement_count") not in (None, len(data["replacements"])):
        raise ValueError(f"{where} meta.replacement_count 与本包 replacements 条数不一致")


def plugin_paths() -> List[Path]:
    if not PLUGINS_DIR.exists():
        return []
    # 下划线前缀文件（如 _template.json）视为模板/占位，不参与聚合加载与校验
    return sorted(p for p in PLUGINS_DIR.glob("*.json")
                  if p.is_file() and not p.name.startswith("_"))


@lru_cache(maxsize=1)
def load_payload() -> Dict[str, Any]:
    """加载核心包并聚合全部行业插件，返回聚合视图（进程内缓存）。

    聚合 meta：version 取核心包；rule_count/replacement_count 为全局总数；
    core_* 为核心包计数；packages 列出各插件摘要。核心包文件本身保持自洽。
    """
    core = _read_json(RULES_PATH)
    validate_core(core)
    rules: List[Dict[str, Any]] = list(core["rules"])
    repl: Dict[str, str] = dict(core["replacements"])
    packages: List[Dict[str, Any]] = []
    for path in plugin_paths():
        pkg = _read_json(path)
        validate_plugin(pkg, path.name)
        m = pkg["meta"]
        rules.extend(pkg["rules"])
        repl.update(pkg["replacements"])
        packages.append({"package": m["package"], "industry": m["industry"],
                         "version": m.get("version", "?"),
                         "rule_count": len(pkg["rules"]),
                         "replacement_count": len(pkg["replacements"])})
    meta = dict(core.get("meta", {}))
    meta["core_rule_count"] = len(core["rules"])
    meta["core_replacement_count"] = len(core["replacements"])
    meta["rule_count"] = len(rules)
    meta["replacement_count"] = len(repl)
    meta["packages"] = packages
    return {"meta": meta, "rules": rules, "replacements": repl}


def core_payload() -> Dict[str, Any]:
    """只读并校验核心包文件（不聚合插件），供规范化 / 守门使用。"""
    data = _read_json(RULES_PATH)
    validate_core(data)
    return data


def plugin_payloads() -> List[Tuple[Path, Dict[str, Any]]]:
    """读并校验每个行业插件包，返回 (path, data)。"""
    out: List[Tuple[Path, Dict[str, Any]]] = []
    for path in plugin_paths():
        data = _read_json(path)
        validate_plugin(data, path.name)
        out.append((path, data))
    return out


def all_rules() -> List[Dict[str, Any]]:
    return load_payload()["rules"]


def replacements() -> Dict[str, str]:
    return load_payload()["replacements"]


def meta() -> Dict[str, Any]:
    return load_payload().get("meta", {})


def active_rules(industry: str, platform: str) -> List[Dict[str, Any]]:
    """按 scope 返回当前行业×平台生效的规则：all 全量 + 本行业 + 本平台。"""
    out: List[Dict[str, Any]] = []
    for r in all_rules():
        scope = r["scope"]
        if scope == "all":
            out.append(r)
        elif scope.startswith("industry:") and scope.split(":", 1)[1] == industry:
            out.append(r)
        elif scope.startswith("platform:") and scope.split(":", 1)[1] == platform:
            out.append(r)
    return out
