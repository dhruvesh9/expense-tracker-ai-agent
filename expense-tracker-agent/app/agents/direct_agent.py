"""Handles non-domain messages: a short reply, no tools."""
from app.llm.factory import get_llm

PROMPT = """You are Expense Tracker Agent, a friendly expense-tracking assistant.
The user said something unrelated to their expenses. Reply in one or two short sentences
and mention that you can add, find, summarise or delete their expenses."""


def reply(messages: list[dict], user: any) -> str:
    return get_llm().generate(PROMPT+f" User Details: {user}", messages)
