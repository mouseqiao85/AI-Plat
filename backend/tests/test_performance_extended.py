"""扩展性能测试 — 覆盖 SSE、内存管理、认证、并发等场景。

Run:  pytest tests/test_performance_extended.py -v --tb=short
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"


# ── SSE Throughput ─────────────────────────────────────────────────────────

class TestSSEThroughputExtended:
    """扩展 SSE 格式化性能测试"""

    def test_sse_format_mixed_events_5000(self):
        """5,000 混合 SSE 事件格式化 < 2s"""
        from app.agent.stream_adapter import format_sse_event, SSEEventType

        events = [
            (SSEEventType.TEXT, {"text": "这是测试文本 " * 5}),
            (SSEEventType.THINKING, {"text": "推理内容 " * 5}),
            (SSEEventType.TOOL_CALL, {"name": "web_search", "status": "completed"}),
        ]
        start = time.time()
        for i in range(5000):
            etype, data = events[i % len(events)]
            format_sse_event(etype, data)
        elapsed = time.time() - start

        avg_us = (elapsed / 5000) * 1_000_000
        print(f"\n  SSE mixed: 5000 events in {elapsed*1000:.1f}ms (avg {avg_us:.0f}us/event)")
        assert elapsed < 2.0, f"Too slow: {elapsed:.2f}s"

    def test_sse_large_payload(self):
        """SSE 格式化包含大量数据的 payload < 1ms"""
        from app.agent.stream_adapter import format_sse_event, SSEEventType

        big_data = {"text": "A" * 10000}
        start = time.time()
        for _ in range(100):
            format_sse_event(SSEEventType.TEXT, big_data)
        elapsed = time.time() - start

        avg_us = (elapsed / 100) * 1_000_000
        print(f"\n  SSE large payload: 100 events in {elapsed*1000:.1f}ms (avg {avg_us:.0f}us/event)")
        assert avg_us < 1000, f"Per-event too slow: {avg_us:.0f}us"


# ── Memory Manager Performance ─────────────────────────────────────────────

class TestMemoryManagerPerformance:
    """MemoryManager 格式化和压缩性能"""

    def test_format_for_claude_100_messages(self):
        """格式化 100 条消息 < 50ms"""
        from app.agent.memory_manager import MemoryManager
        from app.models import Message

        messages = []
        for i in range(100):
            role = "user" if i % 2 == 0 else "assistant"
            msg = Message(
                id=i + 1,
                conversation_id=1,
                role=role,
                content=f"消息内容 {i}，这是一段测试文本。" * 3,
                token_count=0,
            )
            messages.append(msg)

        start = time.time()
        for _ in range(10):
            MemoryManager._format_for_claude(messages)
        elapsed = time.time() - start

        avg_ms = (elapsed / 10) * 1000
        print(f"\n  Format 100 msgs: avg {avg_ms:.1f}ms over 10 runs")
        assert avg_ms < 50, f"Too slow: {avg_ms:.1f}ms"

    def test_sanitize_history_200_messages(self):
        """清洗 200 条消息历史 < 20ms"""
        from app.agent.memory_manager import MemoryManager

        formatted = []
        for i in range(50):
            formatted.append({"role": "user", "content": f"用户消息 {i}"})
            formatted.append({"role": "assistant", "content": f"助手回复 {i}"})

        start = time.time()
        for _ in range(100):
            MemoryManager._sanitize_history(formatted)
        elapsed = time.time() - start

        avg_us = (elapsed / 100) * 1_000_000
        print(f"\n  Sanitize 100 msgs: avg {avg_us:.0f}us over 100 runs")
        assert avg_us < 20000, f"Too slow: {avg_us:.0f}us"

    def test_estimate_token_count_50_messages(self):
        """估算 50 条消息的 token 数 < 5ms"""
        from app.agent.memory_manager import MemoryManager

        messages = [{"role": "user", "content": "这是一段测试文本，用于评估 token 计数性能。" * 5}] * 50

        start = time.time()
        for _ in range(100):
            MemoryManager.estimate_token_count(messages)
        elapsed = time.time() - start

        avg_us = (elapsed / 100) * 1_000_000
        print(f"\n  Estimate tokens 50 msgs: avg {avg_us:.0f}us over 100 runs")
        assert avg_us < 5000, f"Too slow: {avg_us:.0f}us"


# ── Long-Term Memory Performance ───────────────────────────────────────────

class TestLongTermMemoryPerformance:
    """长期记忆性能测试"""

    def test_format_for_prompt_100_profiles(self):
        """格式化 100 个用户档案 < 10ms"""
        from app.agent.long_term_memory import UserMemoryManager, _empty_profile

        mgr = UserMemoryManager(None, None, "test-model")
        profile = _empty_profile(1)
        profile["preferences"]["language_style"] = "专业简洁"
        profile["key_facts"]["profession"] = "软件工程师"
        profile["key_facts"]["interests"] = ["AI", "Python", "Web"]
        profile["profile_summary"] = "资深技术用户，关注 AI 和 Web 开发"

        start = time.time()
        for _ in range(1000):
            mgr.format_for_prompt(profile)
        elapsed = time.time() - start

        avg_us = (elapsed / 1000) * 1_000_000
        print(f"\n  Format profile: 1000 runs avg {avg_us:.1f}us")
        assert avg_us < 100, f"Too slow: {avg_us:.1f}us"

    def test_merge_profile_100_iterations(self):
        """合并 100 次档案更新 < 50ms"""
        from app.agent.long_term_memory import UserMemoryManager, _empty_profile

        mgr = UserMemoryManager(None, None, "test-model")
        profile = _empty_profile(1)

        start = time.time()
        for i in range(100):
            extracted = {
                "key_facts": {"interests": [f"topic_{i}"]},
            }
            profile = mgr._merge_profile(profile, extracted, ["web_search"])
        elapsed = time.time() - start

        print(f"\n  Merge 100 updates: {elapsed*1000:.1f}ms")
        assert elapsed < 0.05, f"Too slow: {elapsed*1000:.1f}ms"


# ── Security Performance ───────────────────────────────────────────────────

class TestSecurityPerformance:
    """安全模块性能测试"""

    def test_password_hash_10_rounds(self):
        """10 次 bcrypt hash < 5s（bcrypt 慢是设计特性）"""
        from app.core.security import hash_password

        start = time.time()
        for _ in range(10):
            hash_password("test_password_123")
        elapsed = time.time() - start

        avg_ms = (elapsed / 10) * 1000
        print(f"\n  Bcrypt hash: avg {avg_ms:.0f}ms/hash")
        assert elapsed < 5.0, f"Too slow: {elapsed:.2f}s"

    def test_token_create_verify_1000(self):
        """1000 次 JWT 创建+验证 < 2s"""
        from app.core.security import create_access_token, decode_access_token

        start = time.time()
        for i in range(1000):
            token = create_access_token({"sub": str(i)})
            payload = decode_access_token(token)
        elapsed = time.time() - start

        avg_us = (elapsed / 1000) * 1_000_000
        print(f"\n  JWT create+verify: 1000 rounds avg {avg_us:.0f}us")
        assert elapsed < 2.0, f"Too slow: {elapsed:.2f}s"


# ── API Concurrency ────────────────────────────────────────────────────────

class TestAPIConcurrency:
    """API 并发性能测试"""

    @pytest.mark.anyio
    async def test_concurrent_health_checks_20(self):
        """20 个并发 health check < 3s"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            start = time.time()
            tasks = [client.get("/health") for _ in range(20)]
            responses = await asyncio.gather(*tasks)
            elapsed = time.time() - start

            for resp in responses:
                assert resp.status_code in (200, 503)

            print(f"\n  20 concurrent health checks: {elapsed*1000:.0f}ms")
            assert elapsed < 3.0, f"Too slow: {elapsed:.2f}s"

    @pytest.mark.anyio
    async def test_concurrent_dev_login_10(self):
        """10 个并发 dev-login < 3s"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            start = time.time()
            tasks = [client.post("/api/v1/auth/dev-login") for _ in range(10)]
            responses = await asyncio.gather(*tasks)
            elapsed = time.time() - start

            for resp in responses:
                assert resp.status_code == 200

            print(f"\n  10 concurrent dev-logins: {elapsed*1000:.0f}ms")
            assert elapsed < 3.0, f"Too slow: {elapsed:.2f}s"

    @pytest.mark.anyio
    async def test_concurrent_provider_list_10(self):
        """10 个并发 provider 列表请求 < 3s"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            start = time.time()
            tasks = [client.get("/api/v1/chat/providers") for _ in range(10)]
            responses = await asyncio.gather(*tasks)
            elapsed = time.time() - start

            for resp in responses:
                assert resp.status_code == 200

            print(f"\n  10 concurrent provider lists: {elapsed*1000:.0f}ms")
            assert elapsed < 3.0, f"Too slow: {elapsed:.2f}s"


# ── File Storage Performance ───────────────────────────────────────────────

class TestFileStoragePerformance:
    """文件存储性能测试"""

    def test_uuid_validation_10000(self):
        """10,000 次 UUID 验证 < 100ms"""
        from app.services.file_storage import _is_valid_uuid

        test_uuid = "550e8400-e29b-41d4-a716-446655440000"
        start = time.time()
        for _ in range(10000):
            _is_valid_uuid(test_uuid)
        elapsed = time.time() - start

        avg_us = (elapsed / 10000) * 1_000_000
        print(f"\n  UUID validation: 10000 runs avg {avg_us:.1f}us")
        assert elapsed < 0.1, f"Too slow: {elapsed*1000:.1f}ms"

    def test_should_generate_file_10000(self):
        """10,000 次文件生成判断 < 200ms"""
        from app.agent.engine import AgentEngine

        short = "短文本"
        long = "A" * 3000

        start = time.time()
        for _ in range(5000):
            AgentEngine._should_generate_file(short)
            AgentEngine._should_generate_file(long)
        elapsed = time.time() - start

        avg_us = (elapsed / 10000) * 1_000_000
        print(f"\n  File check: 10000 runs avg {avg_us:.1f}us")
        assert elapsed < 0.2, f"Too slow: {elapsed*1000:.1f}ms"


# ── Config Loading Performance ─────────────────────────────────────────────

class TestConfigPerformance:
    """配置加载性能测试"""

    def test_get_llm_providers_1000_calls(self):
        """1000 次 get_llm_providers 调用 < 500ms"""
        from app.core.config import get_llm_providers

        start = time.time()
        for _ in range(1000):
            get_llm_providers()
        elapsed = time.time() - start

        avg_us = (elapsed / 1000) * 1_000_000
        print(f"\n  get_llm_providers: 1000 runs avg {avg_us:.0f}us")
        assert elapsed < 0.5, f"Too slow: {elapsed*1000:.1f}ms"
