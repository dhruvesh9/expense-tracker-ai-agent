from app.llm.factory import get_llm
from app.models import IntentResult

PROMPT = """You classify messages for an expense-tracking assistant.
domain: the user wants to add, view, search, summarise, change or delete THEIR OWN expenses
        (this includes short follow-ups like "yes, delete it" or "and last month?").
non_domain: greetings, small talk, general questions, anything not about their own expenses.
Return only the intent."""


def classify_intent(messages: list[dict]) -> str:
    return get_llm().classify(PROMPT, messages, IntentResult).intent
