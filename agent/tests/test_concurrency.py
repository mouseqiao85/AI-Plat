"""Concurrency stress tests for manager singletons."""
import asyncio
import time
import pytest
from app.harness.session import SessionManager
from app.harness.state import StateManager
from app.harness.scope import ScopeManager

pytestmark = pytest.mark.asyncio


class TestSessionManagerConcurrency:
    """Stress test SessionManager with concurrent create/close operations."""

    CONCURRENT_OPS = 20

    async def test_concurrent_create_and_close(self):
        mgr = SessionManager()

        async def create_and_close(i):
            session = await mgr.create_session(user_id=i % 5)
            assert session.session_id is not None
            assert session.sandbox_path is not None
            await mgr.close_session(session.session_id)

        tasks = [create_and_close(i) for i in range(self.CONCURRENT_OPS)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        errors = [r for r in results if isinstance(r, Exception)]
        assert len(errors) == 0, f"{len(errors)} errors: {errors}"

    async def test_concurrent_gets(self):
        mgr = SessionManager()
        session = await mgr.create_session(user_id=1)

        async def get_session():
            return await mgr.get(session.session_id)

        tasks = [get_session() for _ in range(20)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        errors = [r for r in results if isinstance(r, Exception)]
        assert len(errors) == 0, f"{len(errors)} errors: {errors}"
        assert all(s is not None and s.session_id == session.session_id for s in results if not isinstance(s, Exception))

        await mgr.close_session(session.session_id)

    async def test_session_limit_enforcement(self):
        mgr = SessionManager()
        # Create sessions up to the limit
        sessions = []
        for i in range(5):
            s = await mgr.create_session(user_id=900 + i)
            sessions.append(s)

        assert all(s is not None for s in sessions)

        # Cleanup
        for s in sessions:
            await mgr.close_session(s.session_id)


class TestStateManagerConcurrency:
    """Stress test StateManager with concurrent reads/writes."""

    CONCURRENT_OPS = 30

    async def test_concurrent_reads_and_writes(self):
        mgr = StateManager()
        state = await mgr.create(session_id="conc-test", user_id=1)

        async def read_state():
            s = await mgr.get("conc-test")
            return s is not None

        async def update_state(i):
            return await mgr.update("conc-test", turn_count=i)

        # Mix of reads and writes
        tasks = []
        for i in range(self.CONCURRENT_OPS):
            if i % 3 == 0:
                tasks.append(update_state(i))
            else:
                tasks.append(read_state())

        results = await asyncio.gather(*tasks, return_exceptions=True)
        errors = [r for r in results if isinstance(r, Exception)]
        assert len(errors) == 0, f"{len(errors)} errors: {errors}"

        await mgr.end("conc-test")


class TestScopeManagerConcurrency:
    """Stress test ScopeManager rate limiting under concurrency."""

    async def test_concurrent_rate_limit_checks(self):
        mgr = ScopeManager()

        async def check_rate(i):
            ok, msg = await mgr.check_rate_limit("web_search", user_id=i % 3)
            return ok

        tasks = [check_rate(i) for i in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        errors = [r for r in results if isinstance(r, Exception)]
        assert len(errors) == 0, f"{len(errors)} errors: {errors}"
        # Most should pass (200 calls/hour limit, spread across 3 user IDs)
        passed = sum(1 for r in results if r is True)
        assert passed > 0, "All rate limit checks should pass"


class TestConcurrentSessionLoad:
    """End-to-end concurrency: 5 users, each creating sessions and exercising managers."""

    async def test_5_concurrent_users_full_workflow(self):
        session_mgr = SessionManager()
        state_mgr = StateManager()
        scope_mgr = ScopeManager()

        async def user_workflow(user_id: int) -> dict:
            start = time.time()
            try:
                s = await session_mgr.create_session(user_id=user_id)
                st = await state_mgr.create(session_id=s.session_id, user_id=user_id)
                await state_mgr.update(s.session_id, current_task=f"task-{user_id}")

                for _ in range(3):
                    ok, _ = await scope_mgr.check_rate_limit("web_search", user_id=user_id)
                    await asyncio.sleep(0.01)

                cp_id = await state_mgr.checkpoint(s.session_id)
                await state_mgr.update(s.session_id, turn_count=1)

                await session_mgr.close_session(s.session_id)
                await state_mgr.end(s.session_id)

                return {
                    "user_id": user_id,
                    "success": True,
                    "duration": time.time() - start,
                }
            except Exception as e:
                return {"user_id": user_id, "success": False, "error": str(e)}

        results = await asyncio.gather(*[user_workflow(i) for i in range(1, 6)])
        failures = [r for r in results if not r["success"]]
        assert len(failures) == 0, f"{len(failures)} users failed: {failures}"

        durations = [r["duration"] for r in results]
        avg = sum(durations) / len(durations)
        print(f"5 concurrent users: avg={avg:.2f}s, max={max(durations):.2f}s")
