import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Environment + settings management for DebugLens."""

    def __init__(
        self,
        llm_provider: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_model: Optional[str] = None,
        github_token: Optional[str] = None,
    ):
        self.llm_provider = llm_provider or os.getenv("LLM_PROVIDER", "gemini")
        self.llm_api_key = llm_api_key or os.getenv("LLM_API_KEY", "")
        self.llm_model = llm_model or os.getenv("LLM_MODEL")
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("API_PORT", "8000"))

    @property
    def default_model(self) -> str:
        if self.llm_model:
            return self.llm_model
        return {
            "openai": "gpt-4o-mini",
            "gemini": "gemini-2.5-flash",
        }.get(self.llm_provider, "gpt-4o-mini")

    def get_llm(self):
        """Build the LangChain LLM instance based on provider config."""
        if self.llm_provider == "openai":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=self.default_model,
                api_key=self.llm_api_key,
                temperature=0.1,
                timeout=60,
            )
        elif self.llm_provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=self.default_model,
                google_api_key=self.llm_api_key,
                temperature=0.1,
                timeout=60,
                thinking_budget=0,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")
