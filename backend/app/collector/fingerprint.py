"""素材指纹器：SHA256(标题 + 正文前200字)（spec 6.2）。"""

from __future__ import annotations

import hashlib


def digest(title: str, body: str) -> str:
    """计算素材指纹：SHA256(title + body[:200])。

    同输入恒同输出；改一字即变（SHA256雪崩效应）。
    """
    raw = f"{title}{body[:200]}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()