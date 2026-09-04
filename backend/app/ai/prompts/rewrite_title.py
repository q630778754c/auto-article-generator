"""标题改写 Prompt 模板（ADR-015）。"""

from __future__ import annotations

SENSATIONAL_BLACKLIST = [
    "震惊", "速看", "惊呆", "吓傻", "懵了", "炸锅", "沸腾", "炸裂",
    "突发", "紧急", "速递", "快看", "别跑", "出事了", "大事件",
    "99%的人", "看了都", "所有人都", "没人能", "你绝对",
    "震惊全网", "刷屏了", "火了", "霸屏", "热议",
    "深度好文", "干货满满", "建议收藏", "必看", "必读",
]


def render(*, source_title: str = "", max_len: int = 30, platform: str = "") -> str:
    """渲染标题改写 Prompt。

    Args:
        source_title: 素材原标题
        max_len: 平台标题字数上限
        platform: 目标平台标识
    Returns:
        标题改写系统 Prompt
    """
    blacklist = "、".join(SENSATIONAL_BLACKLIST)

    return f"""你是一位资深新闻标题编辑。请将以下标题改写为吸引人但不夸张的标题。

## 要求
1. 标题不超过 {max_len} 字
2. 信息量充足，让读者一眼看出文章主题
3. 不使用感叹号堆砌，不使用问号诱骗点击
4. 保持事实准确，不添加素材中没有的信息

## 夸大词黑名单（禁止使用）
{blacklist}

## 素材原标题
{source_title}

请直接输出改写后的标题，不要加引号或其他标记。"""