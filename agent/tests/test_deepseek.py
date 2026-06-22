"""Tests for DeepSeek multi-round chat support."""
import pytest
from app.llm.client import is_deepseek_provider, build_llm_client


class TestDeepSeekDetection:
    def test_detect_by_provider_id(self):
        assert is_deepseek_provider("deepseek", "") is True

    def test_detect_by_model_name(self):
        assert is_deepseek_provider("", "deepseek-v4-pro") is True
        assert is_deepseek_provider("", "deepseek-v4-flash") is True
        assert is_deepseek_provider("", "deepseek-chat") is True

    def test_not_deepseek(self):
        assert is_deepseek_provider("openai", "gpt-4") is False
        assert is_deepseek_provider("", "gpt-4o-mini") is False

    def test_combined_detection(self):
        assert is_deepseek_provider("deepseek", "deepseek-v4-pro") is True
        assert is_deepseek_provider("deepseek", "gpt-4") is True  # provider wins


class TestBuildClient:
    def test_deepseek_client_uses_correct_base(self):
        client = build_llm_client(provider_id="deepseek", model="deepseek-v4-pro")
        assert "api.deepseek.com" in str(client.base_url)

    def test_generic_client_uses_default_base(self):
        client = build_llm_client(base_url="https://api.openai.com/v1")
        assert "api.openai.com" in str(client.base_url)

    def test_custom_base_overrides_deepseek(self):
        custom = "https://custom.proxy.com/v1"
        client = build_llm_client(provider_id="deepseek", base_url=custom)
        assert "custom.proxy.com" in str(client.base_url)
