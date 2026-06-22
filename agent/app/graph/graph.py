from langgraph.graph import StateGraph, END

from app.graph.state import AgentState
from app.graph.nodes.router import router_node
from app.graph.nodes.planner import planner_node
from app.graph.nodes.executor import executor_node
from app.graph.nodes.responder import responder_node
from app.graph.nodes.input_validator import input_validator_node
from app.graph.nodes.scope_check import scope_check_node
from app.graph.nodes.output_validator import output_validator_node
from app.graph.nodes.rag_retrieval import rag_retrieval_node
from app.graph.nodes.worker_orchestrator import worker_orchestrator_node
from app.graph.edges import (
    route_by_intent,
    should_continue,
    route_by_safety,
    route_by_scope,
    route_after_plan,
)


def build_agent_graph():
    graph = StateGraph(AgentState)

    # Add all nodes
    graph.add_node("input_validator", input_validator_node)
    graph.add_node("router", router_node)
    graph.add_node("rag_retrieval", rag_retrieval_node)
    graph.add_node("planner", planner_node)
    graph.add_node("scope_check", scope_check_node)
    graph.add_node("executor", executor_node)
    graph.add_node("responder", responder_node)
    graph.add_node("output_validator", output_validator_node)
    graph.add_node("worker_orchestrator", worker_orchestrator_node)

    # Entry point
    graph.set_entry_point("input_validator")

    # Input validation → router (pass) or END (fail)
    graph.add_conditional_edges(
        "input_validator",
        route_by_safety,
        {"allowed": "router", "fail": END}
    )

    # Router → planner/responder
    graph.add_conditional_edges(
        "router",
        route_by_intent,
        {"planner": "rag_retrieval", "responder": "responder"}
    )

    # RAG → planner
    graph.add_edge("rag_retrieval", "planner")

    # Planner → route_after_plan (worker_orchestrator, scope_check, or responder for empty plan)
    graph.add_conditional_edges(
        "planner",
        route_after_plan,
        {
            "worker_orchestrator": "worker_orchestrator",
            "scope_check": "scope_check",
            "responder": "responder",
        }
    )

    # Worker orchestrator → responder
    graph.add_edge("worker_orchestrator", "responder")

    # Scope check → executor (pass) or responder (blocked)
    graph.add_conditional_edges(
        "scope_check",
        route_by_scope,
        {"allowed": "executor", "blocked": "responder"}
    )

    # Executor loop
    graph.add_conditional_edges(
        "executor",
        should_continue,
        {"continue": "scope_check", "respond": "responder"}
    )

    # Responder → output_validator
    graph.add_edge("responder", "output_validator")

    # Output validator → END
    graph.add_conditional_edges(
        "output_validator",
        route_by_safety,
        {"allowed": END, "fail": END}
    )

    return graph.compile()
