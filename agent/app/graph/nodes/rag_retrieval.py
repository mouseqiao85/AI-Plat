"""RAG retrieval node for the LangGraph pipeline."""
from app.graph.state import AgentState


async def rag_retrieval_node(state: AgentState) -> dict:
    """Retrieve vector documents and graph context from the knowledge base."""
    messages = state.get("messages", [])
    if not messages:
        return {"retrieved_docs": []}

    last_msg = messages[-1].get("content", "") if isinstance(messages[-1], dict) else str(messages[-1])
    context = state.get("context") or {}
    retrieved = []

    try:
        from app.rag.retriever import retriever
        docs = retriever.query(last_msg, k=5)
        if docs:
            retrieved = [{"content": d.content, "metadata": d.metadata} for d in docs]
            context["rag_docs"] = retrieved
    except ImportError:
        pass

    try:
        from app.rag.graphrag import graph_retriever
        graph_context = await graph_retriever.query(last_msg)
        if graph_context:
            context["knowledge_graph"] = graph_context
            context["graphrag"] = {
                "query": last_msg,
                "hit_count": len(graph_context),
                "mode": "title_key_path_match",
            }
    except ImportError:
        pass

    if context:
        return {"retrieved_docs": retrieved, "context": context}
    return {"retrieved_docs": []}
