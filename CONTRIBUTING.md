# 贡献指南 / Contributing

感谢参与 livestream-compliance-guard（直播电商合规守卫 MCP）。

## 目录结构

```
src/lcg/            规则引擎包（models / rules_store / engine / server_stdio）
rules/rules.v1.json 规则库唯一事实源（语言无关 JSON，勿手改后不校验）
scripts/export_rules.py  规则 JSON 规范化与一致性校验
tests/              run_baseline.py（零依赖冒烟）+ pytest 单元测试
evals/              规则层评测集与 LLM 红队配置，产出 reports/BENCHMARK.md
reports/            对外信任凭证（BENCHMARK / SECURITY）
docs/               工具契约、补全台账等文档
server.py           向后兼容 shim（新代码请直接用 lcg.*）
```

## 本地验证（提交前必跑）

```bash
python scripts/export_rules.py --check   # 规则 JSON 结构/计数/格式一致
python tests/run_baseline.py             # 零依赖行为冒烟（11 项）
python -m pip install -r requirements-dev.txt
python -m pytest -q                      # 单元测试
python evals/run_evals.py               # 评测集并刷新 reports/BENCHMARK.md
python server.py --selftest             # 端到端自测
```

> 规则核心（`lcg.models/rules_store/engine`）零第三方依赖；`server_stdio` 才需要 `pip install mcp`。

## 新增/修改一条规则

1. 编辑 `rules/rules.v1.json`：在合适 `scope`（`all` / `industry:*` / `platform:*`）下增改规则；
2. 同步补充 `replacements`（安全替代词）；
3. 运行 `python scripts/export_rules.py` 规范化写回（会重算 `meta` 计数）；
4. 在 `evals/cases/` 增加**至少一条命中用例**，并确认 `benign.jsonl` 干净用例不被误伤；
5. 若改变判定行为，在 `rules.v1.json` 提升 `meta.version` 并在 `CHANGELOG.md` 记录；
6. 跑完全部本地验证再提交。

## 代码约定

- Python ≥ 3.10，行宽 100，提交前尽量通过 `ruff check .`（规则见 pyproject）；
- 判定逻辑只放在 `lcg.engine`，传输逻辑放在 `server_stdio` / 未来的 `server_http`；
- **不得**改变 `detect/scan_batch/suggest_rewrite/get_rules` 的既有输出字段（契约见 `docs/TOOL_SCHEMA.md`）；新增字段需向后兼容并更新文档与评测；
- 等长归一化（`normalize_text`）必须与原文**等长**（下标可映射，含全角/大小写/常用繁→简）；紧凑层（`normalize_compact`）只做剔除阻断符的补漏并经下标映射还原，必须保留中文标点与句子边界；谐音/拆字/emoji 替字/近义暗示等需上下文判断的变体交给 LLM 层；
- 法规与平台规则引用须可溯源，区分“已查证”与“待核实”。

## 提交信息

建议使用 Conventional Commits：`feat:` / `fix:` / `rules:` / `docs:` / `test:` / `chore:`。

## 法律边界

规则库引用的法规条文与平台政策仅用于合规自检。禁止利用本项目从事任何违法用途；涉及真实商家/平台的安全测试须获得书面授权。
