"""四维审核 Prompt 模板（ADR-015）。

四维：合规 / 原创 / 质量 / 图文一致
stop-slop 5维质量评分：直接性 / 节奏 / 信任 / 真实感 / 密度
来源：stop-slop-master @ references/structures.md + phrases.md
"""

from __future__ import annotations

STOP_SLOP_DIMENSIONS = [
    "直接性（directness）：是否绕弯子、铺垫过多？好文章直奔主题。",
    "节奏（rhythm）：句式是否单调？好文章长短句交替有韵律。",
    "信任（trust）：是否用空洞强调代替事实？好文章用数据说话。",
    "真实感（authenticity）：是否像AI生成的模板文？好文章有人味。",
    "密度（density）：信息密度是否过低？好文章每段都有新信息。",
]


def render(*, title: str = "", content: str = "", image_descriptions: list[str] | None = None) -> str:
    """渲染四维审核 Prompt。

    Args:
        title: 待审核文章标题
        content: 待审核文章正文
        image_descriptions: 配图描述列表（用于图文一致性审核）
    Returns:
        四维审核系统 Prompt
    """
    dims = "\n".join(f"- {d}" for d in STOP_SLOP_DIMENSIONS)
    images = "\n".join(f"  {i+1}. {d}" for i, d in enumerate(image_descriptions or [])) or "  无配图"

    return f"""你是一位资深内容审核编辑。请对以下文章进行四维审核。

## 审核维度

### 1. 合规审核（compliance）
- 是否含违规内容（时政敏感、虚假信息、侵权内容）
- 判定：pass / fail / severe_violation

### 2. 原创度评估（originality，0~100分）
- 与素材的改写程度，是否仅换词未换结构
- 70分以上为通过

### 3. 质量评估（quality，0~100分）
- 信息量、可读性、逻辑性
- 同时进行去AI味5维评分（每维0~100）：
{dims}
- 5维平均70分以上为通过

### 4. 图文一致性（image_text，0~1分）
- 配图描述与正文内容的匹配程度
- 0.6以上为通过

## 配图描述
{images}

## 待审核文章
标题：{title}
正文：{content}

## 输出格式
输出合法 JSON：
{{"compliance_result": "pass/fail/severe_violation", "originality_score": 0~100, "quality_score": 0~100, "image_text_score": 0.0~1.0, "similarity_score": 0.0~1.0, "opinion": "审核意见（不通过时必填）", "slop_dimensions": {{"directness": 0~100, "rhythm": 0~100, "trust": 0~100, "authenticity": 0~100, "density": 0~100}}}}

请直接输出 JSON，不要包裹在 markdown 代码块中。"""