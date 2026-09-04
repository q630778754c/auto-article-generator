"""题材初筛：敏感/违规题材词库命中检测（spec 5.1.1 规则8）。"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_BLOCKED_KEYWORDS = [
    "时政", "国家领导", "领导人讲话", "党代会", "人大", "两会",
    "军事", "武器", "军队", "国防", "外交",
    "暴恐", "暴乱", "恐怖袭击", "极端组织",
    "邪教", "法轮功", "全能神",
    "色情", "赌博", "毒品", "诈骗",
    "维权", "上访", "群体事件", "游行示威",
    "六四", "天安门", "文革", "新疆",
    "台独", "藏独", "港独", "疆独",
    "翻墙", "VPN", "代理服务器",
]


@dataclass
class FilterResult:
    passed: bool
    rule_name: str = ""


def screen(title: str, content: str, blocked_keywords: list[str] | None = None) -> FilterResult:
    """题材初筛：命中词库返回 (False, 命中词)，否则 (True, "")。"""
    keywords = blocked_keywords or DEFAULT_BLOCKED_KEYWORDS
    text = f"{title} {content}"
    for kw in keywords:
        if kw in text:
            return FilterResult(passed=False, rule_name=kw)
    return FilterResult(passed=True)