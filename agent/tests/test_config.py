"""Tests for the configuration module."""
import pytest


class TestSettings:
    def test_settings_load(self):
        from app.core.config import settings
        assert settings.APP_NAME == "Agent Service"
        assert settings.PORT == 8001
        assert settings.HOST == "0.0.0.0"

    def test_settings_defaults(self):
        from app.core.config import settings
        assert settings.LLM_TIMEOUT == 300
        assert settings.TOOL_TIMEOUT == 300
