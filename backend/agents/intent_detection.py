"""
Module 3: Intent Detection Agent.

Classifies a customer message into one or more of:
billing, refund, technical, product, complaint, faq, general

Primary strategy: ask the LLM to return a small JSON array of intents.
Fallback strategy: keyword matching, used if the LLM call fails or returns
something unparsable, so the pipeline never breaks.
"""
import json
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from backend.llm.hf_client import get_hf_client

VALID_INTENTS = ["billing", "refund", "technical", "product", "complaint", "faq", "general"]

SYSTEM_PROMPT = (
    "You are an intent classification engine for a customer support system. "
    "Classify the customer's message into one or more of these categories: "
    f"{', '.join(VALID_INTENTS)}. "
    "A message can belong to more than one category (e.g. a payment that "
    "didn't unlock a feature is both 'billing' and 'technical'). "
    "Respond with ONLY a JSON array of lowercase category strings, nothing else. "
    'Example: ["billing", "technical"]'
)

_KEYWORD_MAP = {
    "billing": ["charge", "charged", "payment", "invoice", "subscription", "billed",
                "price", "emi", "declined", "premium"],
    "refund": ["refund", "return", "money back", "reimburse"],
    "technical": ["error", "bug", "not working", "won't", "wont", "cant login",
                  "can't login", "password", "install", "crash", "locked"],
    "product": ["feature", "spec", "compare", "availability", "in stock", "warranty"],
    "complaint": ["complain", "angry", "furious", "unacceptable", "worst", "terrible",
                  "disappointed", "frustrated"],
    "faq": ["hours", "contact", "policy", "how do i", "what is"],
}


def _keyword_fallback(message: str) -> list[str]:
    lowered = message.lower()
    matches = [
        intent for intent, keywords in _KEYWORD_MAP.items()
        if any(kw in lowered for kw in keywords)
    ]
    return matches or ["general"]


class IntentDetectionAgent:
    def __init__(self):
        self.llm = get_hf_client()

    def detect(self, message: str) -> list[str]:
        raw = self.llm.generate(SYSTEM_PROMPT, message, max_tokens=64, temperature=0.0)

        match = re.search(r"\[.*?\]", raw, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                intents = [i.strip().lower() for i in parsed if i.strip().lower() in VALID_INTENTS]
                if intents:
                    return intents
            except (json.JSONDecodeError, TypeError):
                pass

        # LLM output wasn't usable JSON (or the API call failed) -> fall back
        return _keyword_fallback(message)


_agent_instance: IntentDetectionAgent | None = None


def get_intent_agent() -> IntentDetectionAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = IntentDetectionAgent()
    return _agent_instance
