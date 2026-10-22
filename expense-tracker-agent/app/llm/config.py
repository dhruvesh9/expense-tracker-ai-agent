from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenAISettings(BaseSettings):
    """Only the OpenAI provider reads this. Env vars are OPENAI_<FIELD>."""
    model_config = SettingsConfigDict(env_file=".env", env_prefix="OPENAI_", extra="ignore")

    # SecretStr hides the value if the object is ever printed or logged.
    api_key: SecretStr | None = None
    model_intent: str = "gpt-5-nano"   # small + cheap: just classifies
    model_agent: str = "gpt-5-mini"    # stronger: picks tools, writes answers
    reasoning_effort: str = "low"
    # optional: left unset they are not sent (reasoning models may reject them)
    temperature: float | None = None
    top_p: float | None = None
