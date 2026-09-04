"""schemas 单测：统一响应/分页/脱敏。"""

from __future__ import annotations

import pytest

from app.schemas.common import ApiResponse, PageRequest, PageResponse, MaskedCredentialMixin
from app.core.security import mask_sensitive_value


class TestApiResponse:
    def test_default(self):
        r = ApiResponse()
        assert r.code == 0
        assert r.message == "ok"
        assert r.data is None

    def test_with_data(self):
        r = ApiResponse(code=0, message="ok", data={"key": "value"})
        assert r.data == {"key": "value"}

    def test_generic_typing(self):
        r = ApiResponse[str](data="hello")
        assert r.data == "hello"


class TestPageRequest:
    def test_defaults(self):
        p = PageRequest()
        assert p.page == 1
        assert p.page_size == 20

    def test_offset(self):
        p = PageRequest(page=3, page_size=10)
        assert p.offset == 20

    def test_page_ge_1(self):
        with pytest.raises(ValueError):
            PageRequest(page=0)

    def test_page_size_bounds(self):
        with pytest.raises(ValueError):
            PageRequest(page_size=0)
        with pytest.raises(ValueError):
            PageRequest(page_size=101)


class TestPageResponse:
    def test_defaults(self):
        r = PageResponse()
        assert r.items == []
        assert r.total == 0
        assert r.total_pages == 0

    def test_total_pages(self):
        r = PageResponse(items=[1, 2, 3], total=25, page=1, page_size=10)
        assert r.total_pages == 3

    def test_total_pages_exact(self):
        r = PageResponse(total=20, page_size=10)
        assert r.total_pages == 2


class TestMaskedCredential:
    def test_mask_on_serialize(self):
        class ChannelResp(MaskedCredentialMixin):
            platform: str = "toutiao"

        resp = ChannelResp(credential_cipher="sk-very-long-secret-key-12345Aa")
        dumped = resp.model_dump()
        assert "sk-very-long-secret-key-12345Aa" not in dumped["credential_cipher"]
        assert "****" in dumped["credential_cipher"]

    def test_mask_empty(self):
        class ChannelResp(MaskedCredentialMixin):
            pass

        resp = ChannelResp(credential_cipher="")
        assert resp.model_dump()["credential_cipher"] == ""

    def test_mask_short(self):
        class ChannelResp(MaskedCredentialMixin):
            pass

        resp = ChannelResp(credential_cipher="abc")
        assert resp.model_dump()["credential_cipher"] == "****"