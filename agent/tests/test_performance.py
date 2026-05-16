"""Performance tests for the agent platform."""
import asyncio
import json
import time
import pytest
from httpx import AsyncClient, ASGITransport
from main import app

pytestmark = pytest.mark.asyncio


class TestSSEStreamingLatency:
    """Measure SSE streaming throughput and latency."""

    CONCURRENT_USERS = 5

    async def test_sse_stream_latency(self):
        """Measure time-to-first-event and full-stream duration."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "message": "你好，今天天气怎么样？",
                "session_id": "perf-latency-1",
                "user_id": 1,
            }
            start = time.monotonic()
            first_event_time = None
            event_count = 0
            async with client.stream("POST", "/api/v1/agent/chat/stream", json=payload) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data:"):
                        event_count += 1
                        if first_event_time is None:
                            first_event_time = time.monotonic()
            duration = time.monotonic() - start

            ttfe = (first_event_time - start) if first_event_time else duration
            print(f"SSE stream: first_event={ttfe:.3f}s total={duration:.3f}s events={event_count}")
            assert resp.status_code == 200


class TestConcurrentSessionCapacity:
    """Verify 5 concurrent sessions operate without failures."""

    async def test_5_concurrent_streams(self):
        """Run 5 concurrent chat streams and verify no failures."""
        transport = ASGITransport(app=app)

        async def single_session(user_id: int) -> dict:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                payload = {
                    "message": "搜索新闻",
                    "session_id": f"perf-concurrent-{user_id}",
                    "user_id": user_id,
                }
                start = time.monotonic()
                try:
                    events = 0
                    async with client.stream("POST", "/api/v1/agent/chat/stream", json=payload) as resp:
                        async for line in resp.aiter_lines():
                            if line.startswith("data:"):
                                events += 1
                    return {
                        "user_id": user_id,
                        "success": True,
                        "duration": time.monotonic() - start,
                        "events": events,
                    }
                except Exception as e:
                    return {"user_id": user_id, "success": False, "error": str(e)}

        results = await asyncio.gather(*[single_session(i) for i in range(1, 6)])
        failures = [r for r in results if not r["success"]]
        assert len(failures) == 0, f"{len(failures)} sessions failed: {failures}"

        durations = [r["duration"] for r in results]
        avg_dur = sum(durations) / len(durations)
        print(f"Concurrent sessions: {len(results)} completed, "
              f"avg duration: {avg_dur:.2f}s, max: {max(durations):.2f}s")


class TestToolExecutionThroughput:
    """Measure tool execution throughput."""

    async def test_sequential_tool_calls(self):
        """Execute 10 sequential tool calls and measure throughput."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            count = 10
            successes = 0
            failures = 0
            start = time.monotonic()

            for i in range(count):
                payload = {
                    "message": f"计算 {i}+{i}",
                    "session_id": f"perf-tool-{i}",
                    "user_id": 1,
                }
                try:
                    async with client.stream("POST", "/api/v1/agent/chat/stream", json=payload) as resp:
                        async for _ in resp.aiter_lines():
                            pass
                    successes += 1
                except Exception:
                    failures += 1

            duration = time.monotonic() - start
            throughput = count / duration if duration > 0 else 0
            print(f"Tool throughput: {throughput:.1f} calls/sec, "
                  f"successes={successes}, failures={failures}, duration={duration:.2f}s")
            assert failures == 0


class TestSessionSandboxPerformance:
    """Measure sandbox creation/cleanup performance."""

    async def test_sandbox_create_and_cleanup(self):
        """Measure sandbox lifecycle overhead."""
        from app.harness.sandbox import get_sandbox_manager

        mgr = get_sandbox_manager()
        count = 20
        start = time.monotonic()

        for i in range(count):
            sid = f"perf-sandbox-{i}"
            sandbox = await mgr.create_sandbox(sid)
            assert sandbox.path.exists()
            await mgr.remove_sandbox(sid)

        duration = time.monotonic() - start
        ops_per_sec = count / duration if duration > 0 else 0
        print(f"Sandbox ops: {ops_per_sec:.1f}/sec, total={duration:.2f}s")
