import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from backend.agents.base_agent import BaseAgent


class BillingAgent(BaseAgent):
    name = "billing"
    system_prompt = (
        "You are the Billing Agent for TechMart Electronics, a customer support AI. "
        "You handle payments, subscriptions, invoices, refunds, and EMI/financing "
        "questions. Be precise about policy details (timelines, fees, eligibility). "
        "Never invent a refund amount or timeline that isn't in the provided context. "
        "If the customer describes a specific charge dispute you cannot verify, "
        "explain the general policy and offer to escalate to a human billing "
        "specialist."
    )
