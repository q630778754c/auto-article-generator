"""ORM 模型包入口：导入全部模型类以注册到 Base.metadata。"""

from app.models.user import UserAccount
from app.models.source import NewsSource, Material
from app.models.article import Article, ReviewReport, ArticleImage
from app.models.publish import PublishChannel, PublishRecord
from app.models.pipeline import PipelineRecord
from app.models.system import (
    SystemConfig, AlertEvent, AuditLog, ProcessLog,
    MetricsDaily, QuotaUsage,
)
from app.models.v3_stats import (
    SlaSample, ReviewQualityDaily, UnmannedRunStat, SpotCheckSample,
)
from app.models.api_key import ApiKey, ApiKeyCallLog

__all__ = [
    "UserAccount",
    "NewsSource", "Material",
    "Article", "ReviewReport", "ArticleImage",
    "PublishChannel", "PublishRecord",
    "PipelineRecord",
    "SystemConfig", "AlertEvent", "AuditLog", "ProcessLog",
    "MetricsDaily", "QuotaUsage",
    "SlaSample", "ReviewQualityDaily", "UnmannedRunStat", "SpotCheckSample",
    "ApiKey", "ApiKeyCallLog",
]