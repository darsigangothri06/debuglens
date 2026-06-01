import re
from typing import List, Optional, Tuple

from .models import ParsedError, StackFrame
from .patterns import PATTERNS


class ErrorParser:
    """Parse stack traces from Python, JavaScript, Java, Dart."""

    def __init__(self, llm=None):
        self.llm = llm

    def parse(self, error_text: str) -> ParsedError:
        language = self._detect_language(error_text)
        frames = self._extract_frames(error_text, language)
        exc_type, message = self._extract_exception(error_text, language)

        if not frames and self.llm:
            return self._llm_fallback_parse(error_text)

        return ParsedError(
            language=language,
            exception_type=exc_type,
            message=message,
            frames=frames,
            raw_text=error_text,
        )

    def _detect_language(self, text: str) -> str:
        if "Traceback (most recent call last)" in text:
            return "python"
        if "at Object." in text or "at new " in text or ".js:" in text:
            return "javascript"
        if "Exception in thread" in text or ".java:" in text:
            return "java"
        if "dart:" in text or ".dart:" in text:
            return "dart"
        return "unknown"

    def _extract_frames(self, text: str, language: str) -> List[StackFrame]:
        pattern = PATTERNS.get(language)
        if not pattern:
            return []
        frames = []
        for match in re.finditer(pattern, text):
            frames.append(
                StackFrame(
                    file_path=match.group("file"),
                    line_number=int(match.group("line")),
                    function_name=match.group("func") or "<unknown>",
                )
            )
        return frames

    def _extract_exception(self, text: str, language: str) -> Tuple[str, str]:
        if language == "python":
            match = re.search(
                r"^(\w+(?:\.\w+)*Error|\w+Exception): (.+)$", text, re.MULTILINE
            )
            if match:
                return match.group(1), match.group(2)
        elif language == "javascript":
            match = re.search(
                r"^(\w*Error|\w*Exception): (.+)$", text, re.MULTILINE
            )
            if match:
                return match.group(1), match.group(2)
        elif language == "java":
            match = re.search(
                r"^(?:Exception in thread .+ )?(\S+(?:Error|Exception)): (.+)$",
                text,
                re.MULTILINE,
            )
            if match:
                return match.group(1), match.group(2)
        elif language == "dart":
            match = re.search(
                r"^(\w+(?:\.\w+)*Error|\w+Exception): (.+)$", text, re.MULTILINE
            )
            if not match:
                match = re.search(
                    r"Unhandled exception:\s*\n?\s*(\S+): (.+)$", text, re.MULTILINE
                )
            if match:
                return match.group(1), match.group(2)
        last_line = text.strip().split("\n")[-1]
        return "UnknownError", last_line

    def _llm_fallback_parse(self, text: str) -> ParsedError:
        """Use LLM to parse unusual/custom error formats via structured output."""
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_core.output_parsers import JsonOutputParser

        messages = [
            SystemMessage(
                content=(
                    "You are an expert at parsing error messages and stack traces. "
                    "Parse the following error text and return JSON with: "
                    "language (python/javascript/java/dart/unknown), "
                    "exception_type, message, and frames (list of "
                    "{file_path, line_number, function_name})."
                )
            ),
            HumanMessage(content=text),
        ]
        response = self.llm.invoke(messages)
        result = JsonOutputParser().parse(response.content)

        frames = [
            StackFrame(
                file_path=f.get("file_path", ""),
                line_number=int(f.get("line_number", 0)),
                function_name=f.get("function_name", "<unknown>"),
            )
            for f in result.get("frames", [])
        ]
        return ParsedError(
            language=result.get("language", "unknown"),
            exception_type=result.get("exception_type", "UnknownError"),
            message=result.get("message", text.split("\n")[-1]),
            frames=frames,
            raw_text=text,
        )
