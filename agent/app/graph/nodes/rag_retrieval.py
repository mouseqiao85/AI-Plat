"""RAG retrieval node for the LangGraph pipeline."""
from app.graph.state import AgentState


async def rag_retrieval_node(state: AgentState) -> dict:
    """Retrieve relevant documents from knowledge base."""
    messages = state.get("messages", [])
    if not messages:
        return {"retrieved_docs": []}

    last_msg = messages[-1].get("content", "") if isinstance(messages[-1], dict) else str(messages[-1])

    try:
        from app.rag.retriever import retriever
        docs = retriever.query(last_msg, k=5)
        if docs:
            retrieved = [{"content": d.content, "metadata": d.metadata} for d in docs]
            context = state.get("context") or {}
            context["rag_docs"] = retrieved
            return {"retrieved_docs": retrieved, "context": context}
    except ImportError:
        pass

    return {"retrieved_docs": []}
