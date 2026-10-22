from abc import ABC, abstractmethod


class LLMProvider(ABC):

    @abstractmethod
    def classify(self, system: str, messages: list[dict], schema):
        """Answer in the shape of a Pydantic class (`schema`) and return that object."""

    @abstractmethod
    def generate(self, system: str, messages: list[dict]) -> str:
        """Plain text answer, no tools."""

    @abstractmethod
    def run_with_tools(self, system: str, messages: list[dict], tools: list[dict],
                       handlers: dict, user_id: int, max_rounds: int = 5):
        """Let the LLM call tools until it has an answer. Returns (text, tool_results).

        `tools` are provider-neutral schemas: {"name", "description", "parameters"}.
        `user_id` is injected into every handler call by our code, never by the LLM.
        """
