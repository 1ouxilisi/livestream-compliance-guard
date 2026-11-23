# samples/ —— 成品样例（演示产物形态）

本目录存放由脚本**离线生成**的演示样例，用于在作品集 / Gig 中直观展示"客户拿到手的结果长什么样"。
所有样例均为**虚构示例数据**，不代表任何真实客户、品牌或直播场次；数字与判定由规则层本地跑出，可随时复现。

## 文件清单

| 文件 | 内容 | 复现命令 |
|---|---|---|
| `batch_report.html` | 整场合规周报：总体风险、风险分布、命中类别、按主播分级、待整改清单、分段明细（单文件内联样式，可直接浏览器打开） | `python scripts/export_report.py` |
| `batch_report.csv` | 批量检测分段明细：序号 / 主播 / 话术 / 风险级别 / 命中类别与级别 | 同上 |
| `rewrite_before_after.csv` | 命中词替换前后对照：原文、原始风险、替换明细、改写后全文、复检风险与是否 clean | 同上 |
| `feedback_example.csv` | 误报 / 漏报 / 存疑反馈的导出样例（UTF-8 BOM，表格软件可直接打开） | 同上 |

## 字段说明

### batch_report.csv
- `risk_level`：`clean`（合规）/ `low`（低）/ `medium`（中）/ `high`（高）。
- `hits`：该段命中的规则，格式 `类别(级别)`，多条以 `;` 分隔；空表示未命中。

### rewrite_before_after.csv
- `replacements`：命中词到建议表述的映射，`from → to`，多条以 `;` 分隔。
- `rewritten`：按替换规则改写后的全文；`rewritten_risk` / `rewritten_clean` 为改写结果复检结论（闭环：复检未 clean 不会被当作合规话术采用）。
- 规则层替换偏保守、可能留有机械替换痕迹；更自然的整句改写由可选 LLM 语义层完成。

### feedback_example.csv
- `feedback`：`false_positive`（误报）/ `false_negative`（漏报）/ `review`（存疑待复核）。
- 反馈仅沉淀到本地文件，作为规则库迭代与评测集扩充的输入，不上传、不做自动改规则。

## 自定义输入

```bash
# 用内置示例语料生成到默认 samples/
python scripts/export_report.py

# 传入自己的片段（JSON 数组或 JSONL，每条 {"speaker": ..., "text": ...}）
python scripts/export_report.py --input my_segments.jsonl --industry food --platform douyin

# 指定输出目录
python scripts/export_report.py --out-dir ./out
```

## 边界

本工具仅提供合规风险提示与改写建议，不构成法律意见；不核验资质 / 备案 / 证书真伪，不做语音（ASR）或图像（OCR）识别。法条与平台规则以监管机关及平台最新规则为准，重要场景请咨询法务。
