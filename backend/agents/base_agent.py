"""Base class for every specialized (domain) agent.

Each specialized agent:
  1. Retrieves relevant chunks from the vector store (RAG).
  2. Builds a domain-specific system prompt.
  3. Calls the LLM with the retrieved context + conversation history + query.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from backend.llm.hf_client import get_hf_client
from backend.rag.retriever import get_retriever


class BaseAgent:
    name: str = "base"
    system_prompt: str = "You are a helpful customer support assistant."

    def __init__(self):
        self.llm = get_hf_client()
        self.retriever = get_retriever()

    def retrieve_context(self, query: str) -> list[dict]:
        return self.retriever.retrieve(query)

    def build_prompt(self, query: str, context_chunks: list[dict], conversation_context: str) -> str:
        context_text = "\n\n".join(
            f"[Source: {c['source']}]\n{c['text']}" for c in context_chunks
        ) or "No directly relevant company documents were found."

        return (
            f"Relevant company knowledge base excerpts:\n{context_text}\n\n"
            f"Recent conversation:\n{conversation_context or '(no prior messages)'}\n\n"
            f"Customer's current message: {query}\n\n"
            "Using ONLY the knowledge base excerpts above and the conversation "
            "for context, write a helpful, concise, and accurate reply. If the "
            "excerpts don't cover the question, say so honestly and suggest "
            "escalating to a human agent rather than guessing."
        )

    def handle(self, query: str, conversation_context: str = "") -> dict:
        chunks = self.retrieve_context(query)
        prompt = self.build_prompt(query, chunks, conversation_context)
        reply = self.llm.generate(self.system_prompt, prompt)
        return {
            "agent": self.name,
            "reply": reply,
            "sources": [{"source": c["source"], "text": c["text"]} for c in chunks],
        }
