import tempfile
from pathlib import Path

import pytest

from src.locator.local_repo import LocalRepoReader
from src.locator.code_locator import CodeLocator
from src.parser.models import StackFrame

SAMPLE_PYTHON = """import os

class Calculator:
    def __init__(self):
        self.history = []

    def divide(self, a, b):
        result = a / b
        self.history.append(result)
        return result

    def add(self, a, b):
        return a + b
"""


@pytest.fixture
def temp_repo(tmp_path):
    src = tmp_path / "calculator.py"
    src.write_text(SAMPLE_PYTHON)
    return tmp_path


class TestLocalRepoReader:
    def test_read_existing_file(self, temp_repo):
        reader = LocalRepoReader(str(temp_repo))
        content = reader.read_file("calculator.py")
        assert content is not None
        assert "class Calculator" in content

    def test_read_nonexistent_file(self, temp_repo):
        reader = LocalRepoReader(str(temp_repo))
        content = reader.read_file("nonexistent.py")
        assert content is None

    def test_read_by_filename_fallback(self, temp_repo):
        subdir = temp_repo / "sub"
        subdir.mkdir()
        (subdir / "helper.py").write_text("x = 1")
        reader = LocalRepoReader(str(temp_repo))
        content = reader.read_file("helper.py")
        assert content is not None
        assert "x = 1" in content


class TestCodeLocator:
    def test_get_context_with_valid_frame(self, temp_repo):
        locator = CodeLocator(str(temp_repo))
        frame = StackFrame(
            file_path="calculator.py",
            line_number=8,
            function_name="divide",
        )
        ctx = locator.get_context(frame, context_lines=3)
        assert len(ctx.source_lines) > 0
        assert ctx.frame == frame

    def test_get_context_with_missing_file(self, temp_repo):
        locator = CodeLocator(str(temp_repo))
        frame = StackFrame(
            file_path="missing.py",
            line_number=1,
            function_name="foo",
        )
        ctx = locator.get_context(frame)
        assert ctx.source_lines == []

    def test_imports_extracted(self, temp_repo):
        locator = CodeLocator(str(temp_repo))
        frame = StackFrame(
            file_path="calculator.py",
            line_number=8,
            function_name="divide",
        )
        ctx = locator.get_context(frame)
        assert any("import os" in imp for imp in ctx.imports)
