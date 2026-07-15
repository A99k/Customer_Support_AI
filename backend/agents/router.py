"""
Module 4: Agent Router + Response Aggregator.

Maps detected intents -> specialized agent instances, invokes each relevant
agent (a message like "I paid yesterday but Premium is still locked" invokes
both Billing and Technical), and aggregates their replies into one coherent
response for the customer.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from backend.agents.billing import BillingAgent
from backend.agents.complaint import ComplaintAgent
from backend.agents.faq import FAQAgent
from backend.agents.intent_detection import get_intent_agent
from backend.agents.product import ProductAgent
from backend.agents.technical import TechnicalAgent
from backend.llm.hf_client import get_hf_client

# refund questions are handled by the billing agent
_INTENT_TO_AGENT = {
    "billing": "billing",
    "refund": "billing",
    "technical": "technical",
    "product": "product",
    "complaint": "complaint",
    "faq": "faq",
    "general": "faq",
}

AGGREGATOR_SYSTEM_PROMPT = (
    "You are a response aggregator for a multi-agent customer support system. "
    "You will be given draft replies from one or more specialist agents that "
    "each responded to the same customer message from their own area of "
    "expertise. Merge them into a single, coherent, non-repetitive reply in a "
    "friendly, professional support-agent voice. Keep all the concrete facts "
    "(policies, numbers, steps) from the drafts. Do not mention that you are "
    "merging multiple agents' responses."
)


class AgentRouter:
    def __init__(self):
        self._agents = {
            "billing": BillingAgent(),
            "technical": TechnicalAgent(),
            "product": ProductAgent(),
            "complaint": ComplaintAgent(),
            "faq": FAQAgent(),
        }
        self._intent_agent = get_intent_agent()
        self._llm = get_hf_client()

    def route(self, message: str, conversation_context: str = "") -> dict:
        intents = self._intent_agent.detect(message)

        agent_keys = []
        for intent in intents:
            key = _INTENT_TO_AGENT.get(intent, "faq")
            if key not in agent_keys:
                agent_keys.append(key)
        if not agent_keys:
            agent_keys = ["faq"]

        agent_results = [
            self._agents[key].handle(message, conversation_context)
            for key in agent_keys
        ]

        escalated = any(r.get("escalated") for r in agent_results)
        final_reply = self._aggregate(message, agent_results)

        sources = []
        for r in agent_results:
            for s in r["sources"]:
                if s not in sources:
                    sources.append(s)

        return {
            "reply": final_reply,
            "intents": intents,
            "agents_used": [r["agent"] for r in agent_results],
            "escalated": escalated,
            "sources": sources,
        }

    def _aggregate(self, message: str, agent_results: list[dict]) -> str:
        if len(agent_results) == 1:
            return agent_results[0]["reply"]

        drafts = "\n\n".join(
            f"--- Draft from {r['agent']} agent ---\n{r['reply']}" for r in agent_results
        )
        prompt = (
            f"Customer message: {message}\n\n"
            f"Specialist drafts:\n{drafts}\n\n"
            "Write the single merged reply now."
        )
        return self._llm.generate(AGGREGATOR_SYSTEM_PROMPT, prompt)


_router_instance: AgentRouter | None = None


def get_router() -> AgentRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = AgentRouter()
    return _router_instance
