"""单源限额器：单周期截断至 max_items_per_poll（spec 5.1.1 规则7）。"""

from __future__ import annotations


def truncate(items: list, max_items: int) -> list:
    """截断列表至 max_items 条，余量留待下周期。"""
    if max_items <= 0:
        return []
    return items[:max_items]


def remaining(total: int, max_items: int) -> int:
    """计算剩余配额。"""
    return max(0, max_items - total)