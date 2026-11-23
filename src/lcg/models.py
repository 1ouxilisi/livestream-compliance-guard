# -*- coding: utf-8 -*-
"""
lcg.models —— 枚举常量、入参校验与「等长」输入归一化（零第三方依赖）。

两层归一化：
  1) normalize_text（等长层）：只做 **1 个字符 -> 1 个字符** 的映射——全角 ASCII/数字/符号
     转半角、英文小写、常用繁体字一对一转简体；不插入也不删除字符，归一化文本与原文等长，
     命中下标可原样映射回原文，Hit.index / Hit.match 不失真。
  2) normalize_compact（紧凑层）：在等长层之上，仅剔除空白、零宽字符、emoji 与少数插入式
     装饰符（· ・ • . - _ ~ * # ^ 等），返回紧凑串与「紧凑下标 -> 原文下标」映射，用于拦
     “最 好”“NO·1”“微❤️abc12345”这类插空格/符号/emoji 阻断；**保留中文标点与中文句子
     边界**，不做跨句合并，避免误报。

  谐音（薇芯）、近义暗示（“老毛病不闹腾了”）、中文标点插字（“最，好”）等无法靠字形归一化
  可靠识别的变体，仍交给 LLM 语义层（见 lcg.pipeline）。
"""
from __future__ import annotations

INDUSTRIES = ("jadeite", "general", "food", "cosmetics")
PLATFORMS = ("douyin", "kuaishou", "shipinhao", "taobao")
RISK_LEVELS = ("clean", "low", "medium", "high")
SEV_ORDER = {"clean": 0, "low": 1, "medium": 2, "high": 3}

_FULLWIDTH_OFFSET = 0xFEE0  # 全角 ASCII 区 U+FF01..U+FF5E 与半角 0x21..0x7E 的差值

# 常用繁体字 -> 简体字的**一对一**映射（广告/电商/法规高频字集，等长）。
# 方向为繁->简：多个繁体可对应同一简体（多对一），但每个繁体码点始终映射到恰好一个
# 简体码点，故长度不变、下标不失真。生僻字不在表内，原样保留（交 LLM 语义层）。
_T2S = {
    "國": "国", "級": "级", "際": "际", "極": "极", "頂": "顶", "萬": "万",
    "絕": "绝", "對": "对", "選": "选", "領": "领", "網": "网", "銷": "销",
    "遠": "远", "終": "终", "壞": "坏", "穩": "稳", "賺": "赚", "漲": "涨",
    "賠": "赔", "風": "风", "險": "险", "無": "无", "過": "过", "純": "纯",
    "錯": "错", "僅": "仅", "後": "后", "倉": "仓", "價": "价", "脹": "胀",
    "資": "资", "買": "买", "撿": "捡", "寶": "宝", "傳": "传", "療": "疗",
    "醫": "医", "補": "补", "腎": "肾", "壯": "壮", "陽": "阳", "減": "减",
    "豐": "丰", "鎮": "镇", "藥": "药", "開": "开", "財": "财", "轉": "转",
    "運": "运", "養": "养", "體": "体", "維": "维", "碼": "码", "鏈": "链",
    "發": "发", "評": "评", "現": "现", "頭": "头", "賬": "账", "貨": "货",
    "礦": "矿", "滿": "满", "綠": "绿", "龍": "龙", "種": "种", "帶": "带",
    "們": "们", "虧": "亏", "衝": "冲", "錢": "钱", "質": "质", "優": "优",
    "產": "产", "業": "业", "廣": "广", "內": "内", "權": "权", "認": "认",
    "個": "个", "這": "这", "說": "说", "語": "语", "線": "线", "實": "实",
    "驗": "验", "證": "证", "書": "书", "檢": "检", "測": "测", "復": "复",
    "號": "号", "單": "单", "據": "据", "稅": "税", "費": "费", "違": "违",
    "規": "规", "則": "则", "處": "处", "罰": "罚", "條": "条", "購": "购",
    "顧": "顾", "點": "点", "護": "护", "紅": "红", "飾": "饰", "鐲": "镯",
    "墜": "坠", "觀": "观", "彌": "弥", "鑒": "鉴", "農": "农", "營": "营",
}


def validate_context(industry: str, platform: str) -> tuple:
    """校验行业/平台取值；非法值抛 ValueError（MCP 层会转成工具调用错误）。"""
    if industry not in INDUSTRIES:
        raise ValueError(
            f"不支持的 industry={industry!r}，可选：{', '.join(INDUSTRIES)}")
    if platform not in PLATFORMS:
        raise ValueError(
            f"不支持的 platform={platform!r}，可选：{', '.join(PLATFORMS)}")
    return industry, platform


def _map_char(ch: str) -> str:
    code = ord(ch)
    if code == 0x3000:  # 全角空格 -> 半角空格
        return " "
    if 0xFF01 <= code <= 0xFF5E:  # 全角 ASCII -> 半角
        ch = chr(code - _FULLWIDTH_OFFSET)
    if "A" <= ch <= "Z":  # 半角大写 -> 小写（严格单字符，避免 str.lower() 的变长特例）
        ch = chr(ord(ch) + 32)
    ch = _T2S.get(ch, ch)  # 常用繁体 -> 简体（一对一，等长）
    return ch


def normalize_text(text: str) -> str:
    """等长归一化：全角转半角、英文小写。中文等非 ASCII 字符原样返回。"""
    if not text:
        return ""
    return "".join(_map_char(c) for c in text)


# ---- “第一”语义消歧（B5）-------------------------------------------------
# “第一”后接顺序/序量词时（第一步、第一款、第一期、第一产业、第一人称…），
# 表达的是次序而非排名绝对化，不应判 high；“销量第一/行业第一/第一名”等仍判 high。
# 注意：刻意不收录“名/位/级/等/人”等字（第一名、第一位多为排名）。
_ORDINAL_SUFFIX_1CHAR = frozenset(
    "步款次集章期轮节课道回遍趟代批件页卷册部组场棒手季周月天年篇局盘单类线关条"
)
_ORDINAL_SUFFIX_2CHAR = (
    "部分", "阶段", "季度", "人称", "产业", "世界", "语言",
    "反应", "印象", "现场", "时间", "学历",
)


def is_ordinal_first(norm_text: str, after: int) -> bool:
    """norm_text 中“第一”结束于下标 after，判断其后是否为顺序/序数语境。"""
    if after < len(norm_text) and norm_text[after] in _ORDINAL_SUFFIX_1CHAR:
        return True
    if after + 2 <= len(norm_text) and norm_text[after:after + 2] in _ORDINAL_SUFFIX_2CHAR:
        return True
    return False


# ---- 紧凑归一化（B4：插空格 / 符号 / emoji 阻断）---------------------------
# 仅剔除“阻断/装饰”字符；**刻意保留中文标点（，。、；：！？（）《》等）与句子边界**，
# 也保留冒号、百分号、货币等有语义符号，因此不会把“最后，好货”跨标点错并成“最好”。
_DROP_COMPACT_CHARS = frozenset(" .·・•.-_~*#^")


def _is_drop_compact(ch: str) -> bool:
    if ch in _DROP_COMPACT_CHARS or ch.isspace():
        return True
    o = ord(ch)
    if o in (0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF):  # 零宽字符 / BOM
        return True
    if 0xFE00 <= o <= 0xFE0F:      # 变体选择符（emoji 修饰，如 ❤️ 的 ️）
        return True
    if 0x20D0 <= o <= 0x20FF:      # 组合封闭符（含数字 keycap 组合）
        return True
    if 0x2190 <= o <= 0x21FF:      # 箭头符号
        return True
    if 0x2300 <= o <= 0x23FF:      # 杂项技术符号（多为 emoji，如 ⏰⌨）
        return True
    if 0x2600 <= o <= 0x27BF:      # 杂项符号 / Dingbats（含 ❤ U+2764、★✅）
        return True
    if 0x2B00 <= o <= 0x2BFF:      # 杂类符号与箭头（含 ⭐⬅）
        return True
    if 0x1F000 <= o <= 0x1FAFF:    # emoji 主区（表情/人物/动物/食物/物品/补充符号）
        return True
    if 0x1F1E6 <= o <= 0x1F1FF:    # 区域指示符（国旗字母）
        return True
    return False


def normalize_compact(text: str):
    """在等长归一化之上剔除阻断字符，返回 (compact_text, index_map)。

    紧凑层只用于“补漏”匹配：把空格/中点/emoji 等插在违规词中间的阻断符去掉后再匹配。
    index_map[i] 是 compact_text 第 i 个字符在【原文】中的下标——等长层保证
    norm[k] 与原文第 k 个字符一一对应，故这里直接复用该位置，Hit 区间可无损还原，
    还原出的 match 仍保留原始绕过形态（如 “最 好”“微❤️abc”）。
    """
    norm = normalize_text(text or "")
    chars, idx = [], []
    for k, ch in enumerate(norm):
        if _is_drop_compact(ch):
            continue
        chars.append(ch)
        idx.append(k)
    return "".join(chars), idx
