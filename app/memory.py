"""Vector store (Chroma) for persisting memory across research runs."""
import os
from pathlib import Path
from typing import Optional

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

from app.config import CHROMA_PERSIST_DIR, OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL


def get_embedding_model() -> Optional[OpenAIEmbeddings]:
    if not OPENAI_API_KEY:
        return None
    return OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL)


def get_store(collection_name: str = "research_memory", persist: bool = True) -> Optional[Chroma]:
    """Return a Chroma vector store for research memory. Creates dir if needed."""
    emb = get_embedding_model()
    if not emb:
        return None
    persist_dir = str(CHROMA_PERSIST_DIR) if persist else None
    if persist_dir:
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=collection_name,
        embedding_function=emb,
        persist_directory=persist_dir,
    )


def add_research_memory(
    symbol: str,
    company_name: str,
    summary: str,
    report_json: dict,
    collection_name: str = "research_memory",
) -> None:
    """Store a completed research run in the vector DB for later retrieval."""
    store = get_store(collection_name=collection_name)
    if not store:
        return
    doc = Document(
        page_content=summary,
        metadata={"symbol": symbol, "company_name": company_name, "report": report_json},
    )
    store.add_documents([doc])


def search_similar_research(query: str, k: int = 3, collection_name: str = "research_memory") -> list[Document]:
    """Search past research by semantic similarity."""
    store = get_store(collection_name=collection_name)
    if not store:
        return []
    return store.similarity_search(query, k=k)
