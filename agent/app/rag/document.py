"""Document model and loader for RAG system."""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Document:
    id: str
    content: str
    metadata: dict = field(default_factory=dict)
    embedding: Optional[List[float]] = None


def split_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    return chunks


def load_text(path: str, chunk_size: int = 500) -> list[Document]:
    """Load a text file and split into documents."""
    import os
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    filename = os.path.basename(path)
    chunks = split_text(content, chunk_size)

    docs = []
    for i, chunk in enumerate(chunks):
        docs.append(Document(
            id=f"{filename}_{i}",
            content=chunk,
            metadata={"source": filename, "chunk": i},
        ))
    return docs
