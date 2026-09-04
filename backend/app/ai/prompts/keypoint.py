"""配图要点提取 Prompt 模板（ADR-015）。"""

from __future__ import annotations


def render(*, title: str = "", content: str = "", image_count: int = 4) -> str:
    """渲染配图要点提取 Prompt。

    Args:
        title: 文章标题
        content: 文章正文
        image_count: 需要提取的图片描述数量（3~5）
    Returns:
        配图要点提取系统 Prompt
    """
    return f"""你是一位资深图片编辑。请从以下文章中提取 {image_count} 个配图要点。

## 要求
1. 每个要点对应文章中的一个关键段落或主题
2. 描述要具体、可视化，能直接用于 AI 文生图
3. 图片描述用中文，每条 20~50 字
4. 标注每张图应插入的段落位置（从0开始的索引）

## 输出格式
输出合法 JSON 数组，每个元素格式：
{{"prompt": "图片描述", "position": 段落索引, "is_cover": true/false}}
第一张图 is_cover 为 true。

## 文章内容
标题：{title}
正文：{content}

请直接输出 JSON 数组，不要包裹在 markdown 代码块中。"""