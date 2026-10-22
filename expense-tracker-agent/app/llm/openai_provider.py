import json
import logging

from openai import OpenAI

from app.llm.base import LLMProvider
from app.llm.config import OpenAISettings

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):

    def __init__(self):
        self._cfg = OpenAISettings()
        if self._cfg.api_key is None:
            raise ValueError("OPENAI_API_KEY is not set in .env")
        self._client = OpenAI(api_key=self._cfg.api_key.get_secret_value())
        self._params = {"reasoning": {"effort": self._cfg.reasoning_effort}}
        if self._cfg.temperature is not None:
            self._params["temperature"] = self._cfg.temperature
        if self._cfg.top_p is not None:
            self._params["top_p"] = self._cfg.top_p

    def classify(self, system, messages, schema):
        resp = self._client.responses.parse(
            model=self._cfg.model_intent,   # small + cheap model: it only classifies
            **self._params,
            instructions=system,
            input=messages,
            text_format=schema,
        )
        return resp.output_parsed

    def generate(self, system, messages):
        resp = self._client.responses.create(
            model=self._cfg.model_agent,
            **self._params,
            instructions=system,
            input=messages,
        )
        return resp.output_text

    def run_with_tools(self, system, messages, tools, handlers, user_id, max_rounds=5):
        
        openai_tools = [{"type": "function", **t} for t in tools]
        
        common = dict(model=self._cfg.model_agent, instructions=system,
                      tools=openai_tools, **self._params)

        resp = self._client.responses.create(input=messages, **common)
        tool_results = []

        for _ in range(max_rounds):
            calls = [item for item in resp.output if item.type == "function_call"]
            if not calls:  # no tools wanted -> resp.output_text is the answer
                break

            outputs = []
            for call in calls:
                logger.info("tool call: %s", call.name)
                try:
                    result = handlers[call.name](user_id=user_id, **json.loads(call.arguments))
                except Exception as exc:  # unknown tool, bad args, ... -> tell the LLM
                    result = {"error": {"code": "tool_failed", "message": str(exc)}}
                tool_results.append({"tool": call.name, "result": result})
                outputs.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result),
                })

            resp = self._client.responses.create(
                input=outputs, previous_response_id=resp.id, **common)

        return resp.output_text, tool_results
