"""测试 sequential 模式下单角色失败不中断整链。

行为验证：
1. 创建一个 3 角色的 sequential flow
2. 角色 A 成功 → 角色 B 失败 → 角色 C 仍然执行并成功
3. 最终 run 状态为 "succeeded"（因为至少一个角色成功）
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from typing import List
from unittest.mock import patch, MagicMock

import pytest

# ── 将 bridge 加入搜索路径 ──────────────────────────────────────────────────
_test_dir = os.path.dirname(os.path.abspath(__file__))
_bridge_dir = os.path.join(_test_dir, "..")
sys.path.insert(0, _bridge_dir)

from bridge.orchestrator import run_flow, Event
from bridge.flows import create as create_flow
from bridge import db


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _temp_db():
    """每个测试使用独立的临时 SQLite 数据库。"""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    os.environ["ORCHESTRATOR_DB"] = tmp.name
    # 强制重连
    db._conn = None
    db.init()
    yield
    db._conn.close()
    os.unlink(tmp.name)


def _make_stream_gen(role_behaviors: dict):
    """创建 mock 的 execute_skill_direct_stream 生成器。

    role_behaviors: {role_id: {"content": str} | {"error": str}}
    """
    def _gen(role_id: str, task: str, timeout: int = 600,
             session_id: str = "", model: str = "", project_dir: str = ""):
        behavior = role_behaviors.get(role_id, {"content": f"output from {role_id}"})
        if "error" in behavior:
            yield "", session_id, False
            raise RuntimeError(behavior["error"])
        else:
            content = behavior.get("content", f"output from {role_id}")
            for chunk in [content]:
                yield chunk, session_id, False
            yield content, session_id, True

    return _gen


# ── 辅助函数 ─────────────────────────────────────────────────────────────────

async def _collect_events(flow_id: int, user_input: str) -> List[Event]:
    """执行 flow 并收集所有事件。"""
    events = []
    async for event in run_flow(flow_id, user_input):
        events.append(event)
    return events


# ── 测试用例 ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sequential_middle_role_failure_does_not_abort_chain():
    """中间角色失败 → 链不中断，后续角色继续执行。"""
    # 创建一个 3 角色的 sequential flow
    flow = create_flow(
        name="3-role sequential test",
        flow_type="sequential",
        role_ids=["role-A", "role-B", "role-C"],
        description="测试中间角色失败",
    )

    # mock execute_skill_direct_stream: 角色 B 失败，A/C 成功
    role_behaviors = {
        "role-A": {"content": "Result from role A"},
        "role-B": {"error": "Simulated failure for role B"},
        "role-C": {"content": "Result from role C"},
    }

    with patch("bridge.orchestrator.hermes_cli.execute_skill_direct_stream") as mock_exec:
        def side_effect(role_id, task, **kwargs):
            return _make_stream_gen(role_behaviors)(role_id, task, **kwargs)
        mock_exec.side_effect = side_effect

        events = await _collect_events(flow.id, "test input")

    # ── 断言 ─────────────────────────────────────────────────────────────────
    event_types = [e.type for e in events]

    # 1. 三个角色的 role_started 事件都应该存在
    assert "role_started" in event_types
    started_roles = [e.role_id for e in events if e.type == "role_started"]
    assert "role-A" in started_roles
    assert "role-B" in started_roles
    assert "role-C" in started_roles
    assert len(started_roles) == 3, f"应有 3 个 role_started，实际: {len(started_roles)}"

    # 2. 角色 A 应该完成 (role_completed)
    completed_roles = [e.role_id for e in events if e.type == "role_completed"]
    assert "role-A" in completed_roles, "角色 A 应成功完成"

    # 3. 角色 B 应该失败 (role_failed)
    failed_roles = [e.role_id for e in events if e.type == "role_failed"]
    assert "role-B" in failed_roles, "角色 B 应失败"
    b_fail_event = [e for e in events if e.type == "role_failed" and e.role_id == "role-B"][0]
    assert b_fail_event.error is not None
    assert "Simulated failure" in b_fail_event.error

    # 4. ⭐ 角色 C 仍然执行并完成（即使 B 失败）
    assert "role-C" in completed_roles, "角色 C 应在 B 失败后仍然继续执行并完成"

    # 5. 最终 run 状态为 "succeeded"（因为至少一个角色成功）
    assert "run_completed" in event_types, "整体 run 应成功完成"
    assert "run_failed" not in event_types, "整体 run 不应标记为 failed"

    # 6. 验证 order: role-A → role-B → role-C (sequential 顺序)
    started_A = [e for e in events if e.type == "role_started" and e.role_id == "role-A"][0]
    started_B = [e for e in events if e.type == "role_started" and e.role_id == "role-B"][0]
    started_C = [e for e in events if e.type == "role_started" and e.role_id == "role-C"][0]
    assert started_A.index == 0
    assert started_B.index == 1
    assert started_C.index == 2
    assert started_A.total == 3
    assert started_B.total == 3
    assert started_C.total == 3


@pytest.mark.asyncio
async def test_sequential_first_role_failure():
    """第一个角色失败 → 链不中断，后续角色继续。"""
    flow = create_flow(
        name="first-fails sequential",
        flow_type="sequential",
        role_ids=["role-A", "role-B"],
    )

    role_behaviors = {
        "role-A": {"error": "A failed"},
        "role-B": {"content": "B output"},
    }

    with patch("bridge.orchestrator.hermes_cli.execute_skill_direct_stream") as mock_exec:
        def side_effect(role_id, task, **kwargs):
            return _make_stream_gen(role_behaviors)(role_id, task, **kwargs)
        mock_exec.side_effect = side_effect

        events = await _collect_events(flow.id, "input")

    event_types = [e.type for e in events]

    # 角色 A 失败
    assert "role_failed" in event_types
    assert any(e.role_id == "role-A" and e.type == "role_failed" for e in events)

    # ⭐ 角色 B 仍然执行
    assert "role_completed" in event_types
    assert any(e.role_id == "role-B" and e.type == "role_completed" for e in events)

    # run 整体成功（至少一个角色成功）
    assert "run_completed" in event_types


@pytest.mark.asyncio
async def test_sequential_all_roles_fail():
    """所有角色都失败 → run 状态为 failed。"""
    flow = create_flow(
        name="all-fail sequential",
        flow_type="sequential",
        role_ids=["role-A", "role-B"],
    )

    role_behaviors = {
        "role-A": {"error": "A failed"},
        "role-B": {"error": "B failed"},
    }

    with patch("bridge.orchestrator.hermes_cli.execute_skill_direct_stream") as mock_exec:
        def side_effect(role_id, task, **kwargs):
            return _make_stream_gen(role_behaviors)(role_id, task, **kwargs)
        mock_exec.side_effect = side_effect

        events = await _collect_events(flow.id, "input")

    event_types = [e.type for e in events]

    # 两个角色都失败
    assert sum(1 for e in events if e.type == "role_failed") == 2

    # ⭐ 没有角色成功 → run_failed
    assert "run_completed" not in event_types
    assert "run_failed" in event_types

    # 验证错误信息
    fail_event = [e for e in events if e.type == "run_failed"][0]
    assert "no role produced output" in fail_event.error


@pytest.mark.asyncio
async def test_sequential_prior_passed_to_next_on_success():
    """sequential 模式下，成功的角色输出传递给下一个角色的 prior。"""
    flow = create_flow(
        name="prior-passing sequential",
        flow_type="sequential",
        role_ids=["role-A", "role-B"],
    )

    captured_tasks = []

    with patch("bridge.orchestrator.hermes_cli.execute_skill_direct_stream") as mock_exec:
        def side_effect(role_id, task, **kwargs):
            captured_tasks.append((role_id, task))
            return _make_stream_gen({
                "role-A": {"content": "Prior content from A"},
                "role-B": {"content": "Output from B"},
            })(role_id, task, **kwargs)
        mock_exec.side_effect = side_effect

        events = await _collect_events(flow.id, "user query here")

    # 角色 B 的 task 应包含角色 A 的输出
    b_task = [t for r, t in captured_tasks if r == "role-B"]
    assert len(b_task) == 1
    task_text = b_task[0]
    assert "Prior content from A" in task_text
    assert "user query here" in task_text


@pytest.mark.asyncio
async def test_sequential_no_prior_on_failure():
    """sequential 模式下，失败的角色的输出不传递给下一个角色。"""
    flow = create_flow(
        name="no-prior-on-fail sequential",
        flow_type="sequential",
        role_ids=["role-A", "role-B"],
    )

    captured_tasks = []

    with patch("bridge.orchestrator.hermes_cli.execute_skill_direct_stream") as mock_exec:
        def side_effect(role_id, task, **kwargs):
            captured_tasks.append((role_id, task))
            return _make_stream_gen({
                "role-A": {"error": "A exploded"},
                "role-B": {"content": "B survives"},
            })(role_id, task, **kwargs)
        mock_exec.side_effect = side_effect

        events = await _collect_events(flow.id, "user query")

    # 角色 B 的 task 不应包含角色 A 的内容（因为 A 失败，prior 保持空）
    b_task = [t for r, t in captured_tasks if r == "role-B"]
    assert len(b_task) == 1
    task_text = b_task[0]
    assert "A exploded" not in task_text
    assert "user query" in task_text


@pytest.mark.asyncio
async def test_sequential_events_order():
    """验证事件顺序：started → output → completed/failed → next started → ..."""
    flow = create_flow(
        name="event-order sequential",
        flow_type="sequential",
        role_ids=["role-A", "role-B"],
    )

    with patch("bridge.orchestrator.hermes_cli.execute_skill_direct_stream") as mock_exec:
        def side_effect(role_id, task, **kwargs):
            return _make_stream_gen({
                "role-A": {"content": "A ok"},
                "role-B": {"content": "B ok"},
            })(role_id, task, **kwargs)
        mock_exec.side_effect = side_effect

        events = await _collect_events(flow.id, "input")

    # 提取事件顺序
    timeline = [(e.type, e.role_id) for e in events
                if e.type in ("role_started", "role_completed", "role_failed")]

    assert len(timeline) >= 4
    assert timeline[0] == ("role_started", "role-A"), f"1: {timeline[0]}"
    assert timeline[1] == ("role_completed", "role-A"), f"2: {timeline[1]}"
    assert timeline[2] == ("role_started", "role-B"), f"3: {timeline[2]}"
    assert timeline[3] == ("role_completed", "role-B"), f"4: {timeline[3]}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
