from typing import Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser

from ..parser.models import ParsedError
from .prompts import ROOT_CAUSE_SYSTEM_PROMPT, ROOT_CAUSE_USER_PROMPT


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
        response = self.llm.invoke(messages)
        return self.parser.parse(response.content)
