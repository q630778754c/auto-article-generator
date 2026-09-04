"""文章记录路由（design 2.5.2 D组）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select, func

from app.api.deps import get_current_user
from app.core import database
from app.core.exceptions import ParamError
from app.models import Article, ReviewReport, ArticleImage, PublishRecord

router = APIRouter()


@router.get("")
async def list_articles(
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    user: dict = Depends(get_current_user),
):
    async with database.get_session() as s:
        stmt = select(Article).order_by(Article.id.desc())
        count_stmt = select(func.count()).select_from(Article)
        if status:
            stmt = stmt.where(Article.status == status)
            count_stmt = count_stmt.where(Article.status == status)
        total = await s.scalar(count_stmt)
        result = await s.execute(
            stmt.offset((page - 1) * page_size).limit(page_size)
        )
        items = [
            {"id": r.id, "material_id": r.material_id, "title": r.title,
             "style": r.style, "rewrite_count": r.rewrite_count,
             "model_used": r.model_used, "status": r.status,
             "created_at": r.created_at, "updated_at": r.updated_at}
            for r in result.scalars()
        ]
    return {"code": 0, "message": "ok", "data": {"items": items, "total": total or 0, "page": page, "page_size": page_size}}


@router.get("/{article_id}")
async def get_article(article_id: int, user: dict = Depends(get_current_user)):
    async with database.get_session() as s:
        result = await s.execute(select(Article).where(Article.id == article_id))
        art = result.scalar()
        if not art:
            raise ParamError("文章不存在")
        reviews_result = await s.execute(
            select(ReviewReport).where(ReviewReport.article_id == article_id).order_by(ReviewReport.round_no)
        )
        reviews = [
            {"id": r.id, "round_no": r.round_no, "compliance_result": r.compliance_result,
             "originality_score": r.originality_score, "quality_score": r.quality_score,
             "image_text_score": r.image_text_score, "similarity_score": r.similarity_score,
             "opinion": r.opinion, "reviewed_at": r.reviewed_at, "model_used": r.model_used}
            for r in reviews_result.scalars()
        ]
        images_result = await s.execute(
            select(ArticleImage).where(ArticleImage.article_id == article_id).order_by(ArticleImage.position)
        )
        images = [
            {"id": r.id, "file_url": r.file_url, "origin_flag": r.origin_flag,
             "position": r.position, "is_cover": r.is_cover,
             "width_px": r.width_px, "height_px": r.height_px, "status": r.status}
            for r in images_result.scalars()
        ]
        pub_result = await s.execute(
            select(PublishRecord).where(PublishRecord.article_id == article_id)
        )
        publishes = [
            {"id": r.id, "channel_id": r.channel_id, "status": r.status,
             "platform_audit": r.platform_audit, "platform_url": r.platform_url,
             "publish_time": r.publish_time, "retry_count": r.retry_count}
            for r in pub_result.scalars()
        ]
    return {"code": 0, "message": "ok", "data": {
        "id": art.id, "material_id": art.material_id, "title": art.title,
        "content": art.content, "style": art.style, "rewrite_count": art.rewrite_count,
        "model_used": art.model_used, "status": art.status,
        "created_at": art.created_at, "updated_at": art.updated_at,
        "reviews": reviews, "images": images, "publishes": publishes,
    }}


@router.delete("/{article_id}")
async def delete_article(article_id: int, user: dict = Depends(get_current_user)):
    async with database.get_session() as s:
        result = await s.execute(select(Article).where(Article.id == article_id))
        art = result.scalar()
        if not art:
            raise ParamError("文章不存在")
        if art.status in ("awaiting_confirm", "in_review"):
            raise ParamError("文章处于确认/审核中，不可删除")
        await s.delete(art)
    return {"code": 0, "message": "ok", "data": None}