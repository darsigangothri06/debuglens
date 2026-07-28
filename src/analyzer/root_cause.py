import time
import logging
from typing import Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser

from ..parser.models import ParsedError
from .prompts import ROOT_CAUSE_SYSTEM_PROMPT, ROOT_CAUSE_USER_PROMPT

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BASE_DELAY = 2


def _is_rate_limit(err: Exception) -> bool:
    msg = str(err).lower()
    return "429" in msg or "rate" in msg or "quota" in msg


class RootCauseAnalyzer:
    """LLM-powered root cause analysis from call chain + error."""

    def __init__(self, llm):
        self.llm = llm
        self.parser = JsonOutputParser()

    def analyze(self, error: ParsedError, call_chain_text: str) -> Dict:
        user_text = ROOT_CAUSE_USER_PROMPT.format(
            error_type=error.exception_type,
            error_message=error.message,
            language=error.language,
            call_chain=call_chain_text,
        )
        messages = [
            SystemMessage(content=ROOT_CAUSE_SYSTEM_PROMPT),
            HumanMessage(content=user_text),
        ]

        for attempt in range(MAX_RETRIES):
            try:
                response = self.llm.invoke(messages)
                return self.parser.parse(response.content)
            except Exception as e:
                if _is_rate_limit(e) and attempt < MAX_RETRIES - 1:
                    delay = BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        f"Rate limited in root cause analyzer, retrying in {delay}s "
                        f"(attempt {attempt + 1}/{MAX_RETRIES})"
                    )
                    time.sleep(delay)
                else:
                    raise
