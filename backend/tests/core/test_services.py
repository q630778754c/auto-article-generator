"""领域服务单测：采集基础 + 改写 + 审核 + 发布。"""

from __future__ import annotations

import pytest

from app.collector.fingerprint import digest
from app.collector.topic_filter import screen, DEFAULT_BLOCKED_KEYWORDS
from app.collector.rate_limiter import truncate, remaining


class TestFingerprint:
    def test_stability(self):
        fp1 = digest("标题", "正文内容")
        fp2 = digest("标题", "正文内容")
        assert fp1 == fp2

    def test_sensitivity(self):
        fp1 = digest("标题", "正文内容")
        fp2 = digest("标题", "正文内容2")
        assert fp1 != fp2

    def test_only_first_200_chars(self):
        fp1 = digest("T", "A" * 200 + "B")
        fp2 = digest("T", "A" * 200 + "C")
        assert fp1 == fp2

    def test_hex_length(self):
        fp = digest("T", "C")
        assert len(fp) == 64


class TestTopicFilter:
    def test_pass_normal(self):
        result = screen("科技新闻", "AI技术发展")
        assert result.passed

    def test_block_sensitive(self):
        result = screen("时政新闻", "某会议召开")
        assert not result.passed
        assert result.rule_name == "时政"

    def test_block_in_content(self):
        result = screen("普通标题", "内容含军事关键词")
        assert not result.passed
        assert result.rule_name == "军事"

    def test_custom_keywords(self):
        result = screen("test", "content", blocked_keywords=["test"])
        assert not result.passed
        assert result.rule_name == "test"

    def test_default_keywords_nonempty(self):
        assert len(DEFAULT_BLOCKED_KEYWORDS) > 10


class TestRateLimiter:
    def test_truncate_within_limit(self):
        items = list(range(10))
        result = truncate(items, 20)
        assert len(result) == 10

    def test_truncate_exceeds_limit(self):
        items = list(range(30))
        result = truncate(items, 20)
        assert len(result) == 20

    def test_truncate_zero(self):
        items = list(range(10))
        result = truncate(items, 0)
        assert result == []

    def test_remaining(self):
        assert remaining(15, 20) == 5
        assert remaining(25, 20) == 0


class TestTitleGuard:
    def test_contains_sensational(self):
        from app.services.rewrite_service import TitleGuard
        assert TitleGuard.contains_sensational("震惊！大事件") == "震惊"

    def test_no_sensational(self):
        from app.services.rewrite_service import TitleGuard
        assert TitleGuard.contains_sensational("AI技术最新进展") is None

    def test_truncate(self):
        from app.services.rewrite_service import TitleGuard
        assert len(TitleGuard.truncate("A" * 50, 30)) == 30


class TestWordCalibrator:
    def test_in_range(self):
        from app.services.rewrite_service import WordCalibrator
        ok, reason = WordCalibrator.check_range("A" * 1000, 800, 2000)
        assert ok
        assert reason == "ok"

    def test_too_short(self):
        from app.services.rewrite_service import WordCalibrator
        ok, reason = WordCalibrator.check_range("A" * 500, 800, 2000)
        assert not ok
        assert reason == "too_short"

    def test_too_long(self):
        from app.services.rewrite_service import WordCalibrator
        ok, reason = WordCalibrator.check_range("A" * 3000, 800, 2000)
        assert not ok
        assert reason == "too_long"


class TestSimilarityChecker:
    def test_identical(self):
        from app.services.review_service import SimilarityChecker
        assert SimilarityChecker.similarity("相同文本", "相同文本") == 1.0

    def test_different(self):
        from app.services.review_service import SimilarityChecker
        sim = SimilarityChecker.similarity("完全不同的内容A", "毫不相干的文字B")
        assert sim < 0.5

    def test_partial(self):
        from app.services.review_service import SimilarityChecker
        sim = SimilarityChecker.similarity("AI技术发展新趋势", "AI技术发展新方向")
        assert 0.5 < sim < 1.0


class TestReviewDecider:
    def _make_report(self, **kwargs):
        from app.services.review_service import ReviewReport
        defaults = dict(compliance_result="pass", originality_score=80, quality_score=80,
                        image_text_score=0.7, similarity_score=0.1)
        defaults.update(kwargs)
        return ReviewReport(**defaults)

    def test_pass(self):
        from app.services.review_service import ReviewDecider
        report = self._make_report()
        decision = ReviewDecider.decide(report)
        assert decision.action == "pass"

    def test_hard_block(self):
        from app.services.review_service import ReviewDecider
        report = self._make_report(compliance_result="severe_violation")
        decision = ReviewDecider.decide(report)
        assert decision.action == "hard_block"

    def test_send_back_low_originality(self):
        from app.services.review_service import ReviewDecider
        report = self._make_report(originality_score=50)
        decision = ReviewDecider.decide(report)
        assert decision.action == "send_back"
        assert "原创度" in decision.reason

    def test_send_back_high_similarity(self):
        from app.services.review_service import ReviewDecider
        report = self._make_report(similarity_score=0.5)
        decision = ReviewDecider.decide(report)
        assert decision.action == "send_back"
        assert "相似度" in decision.reason

    def test_send_back_low_quality(self):
        from app.services.review_service import ReviewDecider
        report = self._make_report(quality_score=50)
        decision = ReviewDecider.decide(report)
        assert decision.action == "send_back"
        assert "质量" in decision.reason

    def test_send_back_low_image_text(self):
        from app.services.review_service import ReviewDecider
        report = self._make_report(image_text_score=0.3)
        decision = ReviewDecider.decide(report)
        assert decision.action == "send_back"
        assert "图文一致" in decision.reason

    def test_custom_thresholds(self):
        from app.services.review_service import ReviewDecider
        report = self._make_report(originality_score=75)
        decision = ReviewDecider.decide(report, originality_threshold=80)
        assert decision.action == "send_back"


class TestFetchers:
    def test_rss_fetcher_create(self):
        from app.collector.fetchers.rss_fetcher import RssFetcher
        f = RssFetcher()
        assert isinstance(f, RssFetcher)

    def test_webpage_fetcher_create(self):
        from app.collector.fetchers.webpage_fetcher import WebPageFetcher
        f = WebPageFetcher()
        assert isinstance(f, WebPageFetcher)


class TestPublishService:
    def test_create_service(self, tmp_path):
        from app.services.publish_service import PublishService
        from app.core.security import Cipher, load_or_create_key
        key = load_or_create_key(tmp_path / "k")
        svc = PublishService(Cipher(key))
        assert svc is not None