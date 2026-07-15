import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from backend import config
from backend.agents.base_agent import BaseAgent


class ComplaintAgent(BaseAgent):
    name = "complaint"
    system_prompt = (
        "You are the Complaint Agent for TechMart Electronics, a customer support "
        "AI. You handle complaints, escalations, and dissatisfied customers. "
        "Acknowledge frustration genuinely and briefly, without being obsequious. "
        "Focus on the concrete next step (refund, replacement, escalation to a "
        "human, etc.) rather than over-apologizing. If the message expresses "
        "strong dissatisfaction, confirm that you are escalating to a human "
        "support representative."
    )

    def is_escalation(self, query: str) -> bool:
        lowered = query.lower()
        return any(keyword in lowered for keyword in config.COMPLAINT_ESCALATION_KEYWORDS)

    def handle(self, query: str, conversation_context: str = "") -> dict:
        result = super().handle(query, conversation_context)
        result["escalated"] = self.is_escalation(query)
        if result["escalated"]:
            result["reply"] += (
                "\n\nI've flagged this conversation for a human support "
                "representative, who will follow up with you shortly."
            )
        return result
