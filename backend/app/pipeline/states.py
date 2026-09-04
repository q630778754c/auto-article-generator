"""流水线状态枚举与迁移规则（design 2.1.5(1) 状态图）。

状态流转：
PENDING_REWRITE → REWRITING → IMAGE_GENERATING → REVIEWING → PUBLISHING → DONE
分支：FAILED / VIOLATION_BLOCKED / ARCHIVED_PAUSED / AWAITING_CONFIRM
打回回边：REVIEWING → REWRITING
"""

from __future__ import annotations

from enum import Enum


class Step(str, Enum):
    COLLECT = "collect"
    REWRITE = "rewrite"
    IMAGE = "image"
    REVIEW = "review"
    PUBLISH = "publish"
    DONE = "done"


class ArticleStatus(str, Enum):
    PENDING_REWRITE = "pending_rewrite"
    REWRITING = "rewriting"
    IMAGE_GENERATING = "image_generating"
    REVIEWING = "reviewing"
    PUBLISHING = "publishing"
    DONE = "done"
    FAILED = "failed"
    VIOLATION_BLOCKED = "violation_blocked"
    ARCHIVED_PAUSED = "archived_paused"
    AWAITING_CONFIRM = "awaiting_confirm"


class MaterialStatus(str, Enum):
    PENDING_REWRITE = "pending_rewrite"
    PROCESSING = "processing"
    FAILED = "failed"
    INCOMPLETE = "incomplete"
    TOPIC_BLOCKED = "topic_blocked"
    ARCHIVED = "archived"


TERMINAL_STATES = frozenset({
    ArticleStatus.DONE, ArticleStatus.FAILED,
    ArticleStatus.VIOLATION_BLOCKED, ArticleStatus.ARCHIVED_PAUSED,
})

TRANSITIONS: dict[ArticleStatus, frozenset[ArticleStatus]] = {
    ArticleStatus.PENDING_REWRITE: frozenset({ArticleStatus.REWRITING, ArticleStatus.FAILED, ArticleStatus.ARCHIVED_PAUSED}),
    ArticleStatus.REWRITING: frozenset({ArticleStatus.IMAGE_GENERATING, ArticleStatus.FAILED, ArticleStatus.VIOLATION_BLOCKED}),
    ArticleStatus.IMAGE_GENERATING: frozenset({ArticleStatus.REVIEWING, ArticleStatus.FAILED}),
    ArticleStatus.REVIEWING: frozenset({
        ArticleStatus.PUBLISHING, ArticleStatus.REWRITING,
        ArticleStatus.FAILED, ArticleStatus.VIOLATION_BLOCKED,
        ArticleStatus.AWAITING_CONFIRM,
    }),
    ArticleStatus.PUBLISHING: frozenset({ArticleStatus.DONE, ArticleStatus.FAILED}),
    ArticleStatus.AWAITING_CONFIRM: frozenset({ArticleStatus.PUBLISHING, ArticleStatus.ARCHIVED_PAUSED}),
    ArticleStatus.DONE: frozenset(),
    ArticleStatus.FAILED: frozenset(),
    ArticleStatus.VIOLATION_BLOCKED: frozenset(),
    ArticleStatus.ARCHIVED_PAUSED: frozenset(),
}


def can_transition(from_status: ArticleStatus, to_status: ArticleStatus) -> bool:
    """校验状态迁移是否合法。终态后禁止再流转。"""
    if from_status in TERMINAL_STATES:
        return False
    allowed = TRANSITIONS.get(from_status, frozenset())
    return to_status in allowed


def next_step(current: ArticleStatus) -> Step | None:
    """获取当前状态对应的下一步环节。"""
    mapping = {
        ArticleStatus.PENDING_REWRITE: Step.REWRITE,
        ArticleStatus.REWRITING: Step.IMAGE,
        ArticleStatus.IMAGE_GENERATING: Step.REVIEW,
        ArticleStatus.REVIEWING: Step.PUBLISH,
        ArticleStatus.PUBLISHING: Step.DONE,
    }
    return mapping.get(current)