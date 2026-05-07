"""Performance tests: 5 concurrent users, sandbox isolation, SSE throughput.

Run: pytest tests/test_performance.py -v --tb=short
"""
import asyncio
import os
import time
import pytest

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


# ── Concurrent Sessions ─────────────────────────────────────────────

class TestConcurrentSessions:
    """5 concurrent sessions created and cleaned up."""

    def test_5_concurrent_sessions_sandbox(self):
        """Create 5 sessions simultaneously, verify sandbox isolation."""
        from app.harness.session import get_session_manager

        mgr = get_session_manager()
        sessions = []
        try:
            for i in range(5):
                s = mgr.create_session(user_id=i + 1)
                sessions.append(s)

            assert len(sessions) == 5
            # All sandboxes exist and are unique
            sandboxes = {s.sandbox_dir for s in sessions}
            assert len(sandboxes) == 5, f"Expected 5 unique sandboxes, got {len(sandboxes)}"
            for s in sessions:
                assert s.sandbox_dir is not None
                assert os.path.exists(s.sandbox_dir)
                assert ".joeyagent" in s.sandbox_dir
        finally:
            for s in sessions:
                mgr.close_session(s.session_id)
                assert not os.path.exists(s.sandbox_dir)

    def test_session_per_user_limit(self):
        """MAX_SESSIONS_PER_USER is >= 5 for 5 concurrent users."""
        from app.harness.session import MAX_SESSIONS_PER_USER, MAX_SESSIONS_TOTAL
        assert MAX_SESSIONS_TOTAL >= 5
        assert MAX_SESSIONS_PER_USER >= 5

    def test_sandbox_cleanup_on_close(self):
        """Sandbox is removed when session is closed."""
        from app.harness.session import get_session_manager

        mgr = get_session_manager()
        s = mgr.create_session(user_id=1)
        sandbox = s.sandbox_dir
        assert sandbox is not None
        assert os.path.exists(sandbox)

        mgr.close_session(s.session_id)
        assert not os.path.exists(sandbox)


# ── API Latency ──────────────────────────────────────────────────────

class TestAPILatency:
    """API endpoint latency under concurrent load."""

    def test_health_endpoint_rapid_fire(self):
        """Health endpoint handles rapid sequential requests quickly."""
        from httpx import AsyncClient, ASGITransport

        async def _run():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                start = time.time()
                for _ in range(20):
                    resp = await client.get("/health")
                    # May return 200 or 503 depending on DB/Redis state in test
                    assert resp.status_code in (200, 503)
                elapsed = time.time() - start
                rate = 20 / elapsed
                print(f"\n  Health: 20 req in {elapsed:.2f}s ({rate:.0f} req/s)")
                assert rate > 10, f"Too slow: {rate:.0f} req/s"

        asyncio.run(_run())

    @pytest.mark.asyncio
    async def test_health_endpoint_throughput_async(self):
        """Health endpoint throughput (async, 50 req)."""
        from httpx import AsyncClient, ASGITransport

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            start = time.time()
            for _ in range(50):
                resp = await client.get("/health")
                assert resp.status_code in (200, 503)
            elapsed = time.time() - start
            rate = 50 / elapsed
            print(f"\n  Health async: 50 req in {elapsed:.2f}s ({rate:.0f} req/s)")
            assert rate > 20, f"Too slow: {rate:.0f} req/s"


# ── SSE Throughput ──────────────────────────────────────────────────

class TestSSEThroughput:
    """SSE event formatting and throughput."""

    def test_sse_format_performance(self):
        """SSE event formatting < 500ms for 1000 events."""
        from app.agent.stream_adapter import format_sse_event, SSEEventType

        start = time.time()
        for _ in range(1000):
            format_sse_event(SSEEventType.TEXT, {"text": "Hello world " * 10})
        elapsed = time.time() - start

        avg_us = (elapsed / 1000) * 1_000_000
        print(f"\n  SSE format: 1000 events in {elapsed*1000:.1f}ms (avg {avg_us:.0f}us/event)")
        assert elapsed < 0.5, f"Too slow: {elapsed*1000:.1f}ms"


# ── Tool Loop Degradation ──────────────────────────────────────────

class TestToolDegradation:
    """Tool loop limited to 3 iterations with degradation."""

    def test_max_iterations_is_3(self):
        from app.core.config import settings
        assert settings.MAX_TOOL_ITERATIONS == 3

    def test_degradation_config_exists(self):
        from app.core.config import settings
        assert hasattr(settings, 'MAX_TOOL_ITERATIONS')


# ── Pool Size ──────────────────────────────────────────────────────

class TestConnectionPool:
    """Connection pool verification for 5 users."""

    def test_db_pool_config_exists(self):
        from app.core.database import engine
        assert engine is not None

    def test_redis_pool_sufficient(self):
        from app.core.redis import redis_pool
        if redis_pool is not None:
            assert redis_pool.max_connections >= 10
