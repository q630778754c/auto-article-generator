"""适配层单测：Prompt资产 + LLM Provider + 平台适配器 + 通知。"""

from __future__ import annotations

import pytest

from app.ai.prompts.rewrite_body import render as render_body, STOP_SLOP_BANLIST, STYLE_INSTRUCTIONS
from app.ai.prompts.rewrite_title import render as render_title, SENSATIONAL_BLACKLIST
from app.ai.prompts.keypoint import render as render_keypoint
from app.ai.prompts.four_dim_review import render as render_review, STOP_SLOP_DIMENSIONS


class TestRewriteBodyPrompt:
    def test_render_contains_style(self):
        p = render_body(style="casual", source_title="测试", source_content="内容")
        assert "口语化" in p

    def test_render_contains_all_styles(self):
        for style in STYLE_INSTRUCTIONS:
            p = render_body(style=style)
            assert STYLE_INSTRUCTIONS[style][:10] in p

    def test_render_contains_banlist(self):
        p = render_body(style="casual")
        for ban in STOP_SLOP_BANLIST:
            assert ban[:10] in p

    def test_render_contains_word_range(self):
        p = render_body(style="casual", word_min=800, word_max=2000)
        assert "800" in p
        assert "2000" in p

    def test_render_contains_source(self):
        p = render_body(style="casual", source_title="原标题", source_content="原内容")
        assert "原标题" in p
        assert "原内容" in p

    def test_no_unresolved_placeholders(self):
        p = render_body(style="narrative", source_title="T", source_content="C")
        assert "{style}" not in p
        assert "{source_title}" not in p


class TestRewriteTitlePrompt:
    def test_render_contains_max_len(self):
        p = render_title(source_title="测试", max_len=30)
        assert "30" in p

    def test_render_contains_blacklist(self):
        p = render_title(source_title="测试")
        for word in ["震惊", "速看", "惊呆"]:
            assert word in p

    def test_blacklist_nonempty(self):
        assert len(SENSATIONAL_BLACKLIST) > 10


class TestKeypointPrompt:
    def test_render_contains_count(self):
        p = render_keypoint(title="T", content="C", image_count=4)
        assert "4" in p

    def test_render_contains_json_format(self):
        p = render_keypoint(title="T", content="C")
        assert "JSON" in p
        assert "prompt" in p


class TestFourDimReviewPrompt:
    def test_render_contains_dimensions(self):
        p = render_review(title="T", content="C")
        assert "合规" in p
        assert "原创" in p
        assert "质量" in p
        assert "图文一致" in p

    def test_render_contains_slop_dimensions(self):
        p = render_review(title="T", content="C")
        for dim in STOP_SLOP_DIMENSIONS:
            assert dim[:5] in p

    def test_render_with_images(self):
        p = render_review(title="T", content="C", image_descriptions=["图1描述", "图2描述"])
        assert "图1描述" in p
        assert "图2描述" in p


class TestLLMProvider:
    def test_create_openai_provider(self):
        from app.ai.llm_provider import create_provider, LLMProvider
        p = create_provider(provider="deepseek", api_key="sk-test", base_url="https://api.deepseek.com/v1", model="deepseek-chat")
        assert isinstance(p, LLMProvider)

    def test_create_anthropic_provider(self):
        from app.ai.llm_provider import create_provider, AnthropicLLMProvider
        p = create_provider(provider="anthropic", api_key="sk-test", base_url="https://api.anthropic.com/v1", model="claude-3-sonnet")
        assert isinstance(p, AnthropicLLMProvider)

    def test_llm_response_parse_json(self):
        from app.ai.llm_provider import LLMResponse
        resp = LLMResponse(content='{"title": "测试", "content": "正文"}', model="m")
        data = resp.parse_json()
        assert data["title"] == "测试"

    def test_llm_response_parse_json_with_codeblock(self):
        from app.ai.llm_provider import LLMResponse
        resp = LLMResponse(content='```json\n{"title": "测试"}\n```', model="m")
        data = resp.parse_json()
        assert data["title"] == "测试"


class TestImageProvider:
    def test_create_provider(self):
        from app.ai.image_provider import create_image_provider, ImageGenProvider
        p = create_image_provider(provider="tongyi_volc", api_key="sk-test")
        assert isinstance(p, ImageGenProvider)


class TestPlatformAdapters:
    def test_all_5_adapters_registered(self):
        from app.publisher.adapters import ADAPTERS
        assert set(ADAPTERS.keys()) == {"toutiao", "baijiahao", "zhihu", "penguin", "xhs"}

    def test_adapter_configs(self):
        from app.publisher.adapters import ADAPTERS
        for name, cls in ADAPTERS.items():
            adapter = cls()
            cfg = adapter.get_default_config()
            assert cfg.title_max > 0
            assert cfg.content_max > 0

    def test_xhs_config(self):
        from app.publisher.adapters.xhs import XhsAdapter
        cfg = XhsAdapter().get_default_config()
        assert cfg.title_max == 20
        assert cfg.content_max == 1000
        assert cfg.image_min == 3

    def test_credential_parsing(self):
        from app.publisher.base import PlatformAdapter, CookieCredential, OauthCredential
        from app.core.security import Cipher, load_or_create_key
        import json
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as td:
            key = load_or_create_key(Path(td) / "k")
            cipher = Cipher(key)

            cookie_data = json.dumps({"cookies": {"session": "abc"}, "headers": {}})
            encrypted = cipher.encrypt(cookie_data)

            class TestAdapter(PlatformAdapter):
                platform = "test"
                async def publish(self, c, cred): ...
                async def check_health(self, cred): ...
                async def query_by_title(self, t, cred): ...
                def get_default_config(self): ...

            adapter = TestAdapter()
            cred = adapter.parse_credential(encrypted, cipher, "cookie")
            assert isinstance(cred, CookieCredential)
            assert cred.cookies["session"] == "abc"


class TestNotifier:
    @pytest.mark.asyncio
    async def test_p2_not_sent(self):
        from app.services.notifier import Notifier, AlertMessage
        n = Notifier(wechat_webhook="http://example.com/webhook")
        alert = AlertMessage(level="P2", source="system", title="测试", description="P2告警")
        results = await n.send(alert)
        assert results == {}

    @pytest.mark.asyncio
    async def test_p0_triggers_wechat(self):
        from app.services.notifier import Notifier, AlertMessage
        n = Notifier(wechat_webhook="http://example.com/webhook")
        alert = AlertMessage(level="P0", source="system", title="测试", description="P0告警")
        results = await n.send(alert)
        assert "wechat" in results

    @pytest.mark.asyncio
    async def test_no_channels_configured(self):
        from app.services.notifier import Notifier, AlertMessage
        n = Notifier()
        alert = AlertMessage(level="P0", source="system", title="测试", description="P0")
        results = await n.send(alert)
        assert results == {}