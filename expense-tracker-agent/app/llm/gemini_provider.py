from app.llm.base import LLMProvider

class GeminiProvider(LLMProvider):

    def classify(self, system, messages, schema):
        raise NotImplementedError("Gemini provider is not implemented yet")

    def generate(self, system, messages):
        raise NotImplementedError("Gemini provider is not implemented yet")

    def run_with_tools(self, system, messages, tools, handlers, user_id, max_rounds=5):
        raise NotImplementedError("Gemini provider is not implemented yet")
