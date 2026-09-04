"""正文改写 Prompt 模板（ADR-015）。

stop-slop-master 41条反模式裁剪记录（中文资讯版）：
- 保留：二元对立开场、喉塞白、空洞强调、被动语态、虚假代理、碎片化戏剧、修辞设套
- 裁剪：英文专用句式（"Here's the thing"等无法直译）、英文商业黑话（navigate/unpack等）
- 裁剪：英文副词清单（-ly系列），中文用"地"字结构等价约束
- 裁剪：meta-commentary 英文专用句式
来源版本：stop-slop-master @ references/structures.md + phrases.md
"""

from __future__ import annotations

STYLE_INSTRUCTIONS = {
    "casual": '口语化、接地气，像跟朋友聊天一样娓娓道来。可以用"你"拉近距离，但不要过度随意。',
    "professional": "专业严谨但不晦涩，用词精准，逻辑清晰。适合行业人士阅读。",
    "narrative": "讲故事的方式展开，有场景有细节有人物，让读者身临其境。",
    "listicle": "清单体，用编号列表组织要点，每条简洁有力，开头用一句话引出主题。",
}

STOP_SLOP_BANLIST = [
    '禁止二元对立开场：不要用"不是X，而是Y""与其说X，不如说Y"等反转句式，直接陈述Y',
    '禁止喉塞白：不要用"说实话""不得不说""其实吧""你知道吗"等开场白铺垫，直接进入正题',
    '禁止空洞强调：不要用"这一点非常重要""这很关键""毋庸置疑"等无信息强调，用事实说话',
    '禁止被动语态泛滥：每句话应有明确主语在做事，避免"被决定""被认为"掩盖行动者',
    '禁止虚假代理：不要说"市场证明了""数据告诉我们""时代选择了"，指明具体的人或团队在行动',
    '禁止碎片化戏剧：不要用"就这一个词。""没错。""就这样。"等短句制造假深度，写完整句子',
    '禁止修辞设套：不要用"想想看""你知道吗""有意思的是"等反问/设问引导，直接给出结论',
    '禁止万能连接词：不要滥用"然而""不过""但是"制造转折感，转折需有实质内容支撑',
    '禁止"地"字副词堆砌：少用"慢慢地""轻轻地""深深地"等副词修饰，用具体动作代替',
    '禁止总结式收尾：不要用"这就是为什么""所以说""归根结底"等总结句，让读者自己得出结论',
]

HARD_CONSTRAINTS = [
    "只能基于素材提供的事实改写，禁止捏造素材中不存在的事实、数据、引用或案例",
    "禁止添加素材中没有的人名、机构名、产品名或具体数字",
    "保持素材的核心信息和观点不变，改写的是表达方式而非内容本身",
    '输出必须是合法 JSON，格式为 {"title": "...", "content": "..."}',
]


def render(*, style: str, word_min: int = 800, word_max: int = 2000, source_title: str = "", source_content: str = "") -> str:
    """渲染正文改写 Prompt。

    Args:
        style: 四风格之一 casual/professional/narrative/listicle
        word_min: 最少字数
        word_max: 最多字数
        source_title: 素材原标题
        source_content: 素材原文正文
    Returns:
        完整的系统 Prompt 字符串
    """
    style_desc = STYLE_INSTRUCTIONS.get(style, STYLE_INSTRUCTIONS["casual"])
    bans = "\n".join(f"- {b}" for b in STOP_SLOP_BANLIST)
    constraints = "\n".join(f"- {c}" for c in HARD_CONSTRAINTS)

    return f"""你是一位资深中文资讯编辑。请将以下素材改写为一篇原创文章。

## 风格要求
{style_desc}

## 字数要求
正文 {word_min}~{word_max} 字，标题 15~30 字。

## 写作禁令（去AI味，来源：stop-slop-master 41条反模式中文裁剪版）
{bans}

## 硬约束
{constraints}

## 素材内容
标题：{source_title}
正文：{source_content}

请直接输出 JSON，不要包裹在 markdown 代码块中。"""