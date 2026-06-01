from typing import Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser

from ..parser.models import CodeContext, SimilarIssue
from .prompts import FIX_SYSTEM_PROMPT, FIX_USER_PROMPT


class FixGenerator:
    """LLM-powered fix suggestion from root cause analysis."""

    def __init__(self, llm):
        self.llm = llm
        self.parser = JsonOutputParser()

    def generate(
        self,
        root_cause: Dict,
        source_context: Optional[CodeContext],
        similar_issues: List[SimilarIssue],
    ) -> Dict:
        source_text = ""
        if source_context:
            source_text = "\n".join(source_context.source_lines)
            if source_context.function_body:
                source_text += f"\n\nFull function:\n{source_context.function_body}"

        similar_text = self._format_similar_issues(similar_issues)

        user_text = FIX_USER_PROMPT.format(
            root_cause=root_cause.get("explanation", root_cause.get("root_cause", "")),
            source_code=source_text or "Source code not available",
            similar_issues=similar_text or "No similar issues found",
        )
        messages = [
            SystemMessage(content=FIX_SYSTEM_PROMPT),
            HumanMessage(content=user_text),
        ]
        response = self.llm.invoke(messages)
        return self.parser.parse(response.content)

    def _format_similar_issues(self, issues: List[SimilarIssue]) -> str:
        if not issues:
            return ""
        parts = []
        for issue in issues[:5]:
            accepted = " [ACCEPTED]" if issue.is_accepted else ""
            parts.append(
                f"- [{issue.source}] {issue.title} (score: {issue.score}){accepted}\n"
                f"  URL: {issue.url}"
            )
            if issue.answer_snippet:
                snippet = issue.answer_snippet[:200]
                parts.append(f"  Answer: {snippet}")
        return "\n".join(parts)
