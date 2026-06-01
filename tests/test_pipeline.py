from unittest.mock import MagicMock, patch

import pytest

from src.parser.error_parser import ErrorParser
from src.parser.models import DiagnosticReport, ParsedError, StackFrame


class TestPipelineIntegration:
    """Integration tests that mock the LLM but test the rest of the pipeline."""

    def test_parser_to_tracer_flow(self, tmp_path):
        """Verify parsed error feeds correctly into the tracer."""
        (tmp_path / "app.py").write_text("def main():\n    x = 1 / 0\n")
        parser = ErrorParser()
        text = (
            "Traceback (most recent call last):\n"
            '  File "app.py", line 2, in main\n'
            "ZeroDivisionError: division by zero"
        )
        error = parser.parse(text)
        assert error.language == "python"
        assert error.exception_type == "ZeroDivisionError"

        from src.locator.code_locator import CodeLocator
        from src.tracer.call_tracer import CallChainTracer

        locator = CodeLocator(str(tmp_path))
        tracer = CallChainTracer(locator)
        chain = tracer.trace(error)
        assert len(chain) == 1
        assert len(chain[0].code_context.source_lines) > 0

    def test_diagnostic_report_structure(self):
        """Verify DiagnosticReport holds all required fields."""
        error = ParsedError(
            language="python",
            exception_type="KeyError",
            message="'name'",
        )
        report = DiagnosticReport(
            error=error,
            call_chain=[],
            root_cause="Missing key in dict",
            similar_issues=[],
            suggested_fix="Use dict.get()",
            fix_file="app.py",
            fix_line=10,
            confidence="high",
        )
        assert report.error.exception_type == "KeyError"
        assert report.confidence == "high"
        assert report.fix_file == "app.py"
        assert report.fix_line == 10
