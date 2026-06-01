import pytest

from src.locator.code_locator import CodeLocator
from src.parser.models import CodeContext, ParsedError, StackFrame
from src.tracer.call_tracer import CallChainTracer

SAMPLE_CODE = """def foo():
    return bar()

def bar():
    raise ValueError("oops")
"""


@pytest.fixture
def temp_repo(tmp_path):
    (tmp_path / "app.py").write_text(SAMPLE_CODE)
    return tmp_path


@pytest.fixture
def locator(temp_repo):
    return CodeLocator(str(temp_repo))


@pytest.fixture
def tracer(locator):
    return CallChainTracer(locator)


class TestCallChainTracer:
    def test_trace_builds_chain(self, tracer):
        error = ParsedError(
            language="python",
            exception_type="ValueError",
            message="oops",
            frames=[
                StackFrame(file_path="app.py", line_number=5, function_name="bar"),
                StackFrame(file_path="app.py", line_number=2, function_name="foo"),
            ],
        )
        chain = tracer.trace(error)
        assert len(chain) == 2
        assert chain[0].frame.function_name == "bar"
        assert chain[1].frame.function_name == "foo"

    def test_trace_handles_missing_files(self, tracer):
        error = ParsedError(
            language="python",
            exception_type="Error",
            message="msg",
            frames=[
                StackFrame(
                    file_path="missing.py", line_number=1, function_name="nope"
                ),
            ],
        )
        chain = tracer.trace(error)
        assert len(chain) == 1
        assert chain[0].code_context.source_lines == []

    def test_format_chain(self, tracer):
        error = ParsedError(
            language="python",
            exception_type="ValueError",
            message="oops",
            frames=[
                StackFrame(file_path="app.py", line_number=5, function_name="bar"),
            ],
        )
        chain = tracer.trace(error)
        text = tracer.format_chain(chain)
        assert "Frame 1" in text
        assert "bar" in text
        assert "app.py:5" in text
