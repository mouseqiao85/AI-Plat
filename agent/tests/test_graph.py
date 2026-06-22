"""Tests for the LangGraph agent graph."""
import pytest
from app.graph.state import AgentState
from app.graph.graph import build_agent_graph
from app.graph.edges import route_by_intent, should_continue, route_by_safety, route_by_scope
from app.graph.nodes.planner import _filter_invalid_calculator_steps, _keyword_plan


class TestStateGraph:
    def test_graph_builds(self):
        graph = build_agent_graph()
        assert graph is not None

    def test_graph_nodes_present(self):
        graph = build_agent_graph()
        nodes = graph.get_graph().nodes
        expected = {"input_validator", "router", "rag_retrieval", "planner",
                     "scope_check", "executor", "responder", "output_validator"}
        assert expected.issubset(set(nodes.keys()))


class TestEdges:
    def test_route_by_intent_task(self):
        state: AgentState = {"intent": "task", "messages": [], "session_id": "",
                              "user_id": 0, "conversation_id": 0, "plan": None,
                              "current_step": 0, "tool_results": None, "retrieved_docs": None,
                              "context": None, "feedback": None, "safety_passed": True,
                              "approved": True, "retry_count": 0, "error": None,
                              "response": None, "provider_id": "", "model": "",
                              "available_tools": None}
        assert route_by_intent(state) == "planner"

    def test_route_by_intent_chat(self):
        state: AgentState = {"intent": "chat", "messages": [], "session_id": "",
                              "user_id": 0, "conversation_id": 0, "plan": None,
                              "current_step": 0, "tool_results": None, "retrieved_docs": None,
                              "context": None, "feedback": None, "safety_passed": True,
                              "approved": True, "retry_count": 0, "error": None,
                              "response": None, "provider_id": "", "model": "",
                              "available_tools": None}
        assert route_by_intent(state) == "responder"

    def test_should_continue_empty_plan(self):
        state: AgentState = {"intent": "task", "messages": [], "session_id": "",
                              "user_id": 0, "conversation_id": 0, "plan": [],
                              "current_step": 0, "tool_results": None, "retrieved_docs": None,
                              "context": None, "feedback": None, "safety_passed": True,
                              "approved": True, "retry_count": 0, "error": None,
                              "response": None, "provider_id": "", "model": "",
                              "available_tools": None}
        assert should_continue(state) == "respond"

    def test_should_continue_with_plan(self):
        state: AgentState = {"intent": "task", "messages": [], "session_id": "",
                              "user_id": 0, "conversation_id": 0,
                              "plan": [{"tool": "web_search", "args": {"query": "test"}}],
                              "current_step": 0, "tool_results": None, "retrieved_docs": None,
                              "context": None, "feedback": None, "safety_passed": True,
                              "approved": True, "retry_count": 0, "error": None,
                              "response": None, "provider_id": "", "model": "",
                              "available_tools": None}
        assert should_continue(state) == "continue"

    def test_route_by_safety_allowed(self):
        state: AgentState = {"intent": "chat", "messages": [], "session_id": "",
                              "user_id": 0, "conversation_id": 0, "plan": None,
                              "current_step": 0, "tool_results": None, "retrieved_docs": None,
                              "context": None, "feedback": None, "safety_passed": True,
                              "approved": True, "retry_count": 0, "error": None,
                              "response": None, "provider_id": "", "model": "",
                              "available_tools": None}
        assert route_by_safety(state) == "allowed"

    def test_route_by_safety_fail(self):
        state: AgentState = {"intent": "chat", "messages": [], "session_id": "",
                              "user_id": 0, "conversation_id": 0, "plan": None,
                              "current_step": 0, "tool_results": None, "retrieved_docs": None,
                              "context": None, "feedback": None, "safety_passed": False,
                              "approved": True, "retry_count": 0, "error": None,
                              "response": None, "provider_id": "", "model": "",
                              "available_tools": None}
        assert route_by_safety(state) == "fail"


class TestAgentState:
    def test_state_defaults(self):
        state: AgentState = {"messages": [], "session_id": "test", "user_id": 1,
                              "conversation_id": 1, "intent": "chat", "plan": None,
                              "current_step": 0, "tool_results": None, "retrieved_docs": None,
                              "context": None, "feedback": None, "safety_passed": True,
                              "approved": True, "retry_count": 0, "error": None,
                              "response": None, "provider_id": "", "model": "",
                              "available_tools": None}
        assert state["session_id"] == "test"
        assert state["user_id"] == 1
        assert state["intent"] == "chat"


class TestPlannerKeywordFallback:
    def test_report_date_range_does_not_trigger_calculator(self):
        plan = _keyword_plan("罗氏制药中国渠道销售情况分析2025-2026，生成html报告", ["calculator", "web_search"])

        assert not any(step["tool"] == "calculator" for step in plan)

    def test_plain_math_still_triggers_calculator(self):
        plan = _keyword_plan("计算 2 + 3 * 4", ["calculator"])

        assert plan == [{
            "tool": "calculator",
            "args": {"expression": "2 + 3 * 4"},
            "description": "计算: 2 + 3 * 4",
        }]

    def test_invalid_llm_calculator_step_is_dropped(self):
        steps = _filter_invalid_calculator_steps([{
            "tool": "calculator",
            "args": {"expression": "罗氏制药中国渠道销售情况分析2025-2026，生成html报告"},
            "description": "计算报告日期区间",
        }])

        assert steps == []
