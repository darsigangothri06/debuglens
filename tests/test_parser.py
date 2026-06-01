from pathlib import Path

import pytest

from src.parser.error_parser import ErrorParser
from src.parser.models import ParsedError

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def parser():
    return ErrorParser()


class TestLanguageDetection:
    def test_detects_python(self, parser):
        text = 'Traceback (most recent call last):\n  File "app.py", line 1, in main\nKeyError: "x"'
        result = parser.parse(text)
        assert result.language == "python"

    def test_detects_javascript(self, parser):
        text = "TypeError: x is not a function\n    at Object.run (app.js:10:5)"
        result = parser.parse(text)
        assert result.language == "javascript"

    def test_detects_java(self, parser):
        text = 'Exception in thread "main" java.lang.NullPointerException\n    at com.App.main(App.java:5)'
        result = parser.parse(text)
        assert result.language == "java"

    def test_detects_dart(self, parser):
        text = "#0      main (package:myapp/main.dart:5:3)"
        result = parser.parse(text)
        assert result.language == "dart"

    def test_unknown_language(self, parser):
        text = "some random error with no recognizable pattern"
        result = parser.parse(text)
        assert result.language == "unknown"


class TestPythonParsing:
    def test_parse_python_traceback(self, parser):
        text = FIXTURES_DIR.joinpath("python_traceback.txt").read_text()
        result = parser.parse(text)
        assert result.language == "python"
        assert result.exception_type == "KeyError"
        assert "'name'" in result.message
        assert len(result.frames) == 3

    def test_python_frame_details(self, parser):
        text = FIXTURES_DIR.joinpath("python_traceback.txt").read_text()
        result = parser.parse(text)
        first = result.frames[0]
        assert first.file_path == "/app/services/user_service.py"
        assert first.line_number == 45
        assert first.function_name == "get_user_profile"


class TestJavaScriptParsing:
    def test_parse_js_error(self, parser):
        text = FIXTURES_DIR.joinpath("javascript_error.txt").read_text()
        result = parser.parse(text)
        assert result.language == "javascript"
        assert result.exception_type == "TypeError"
        assert len(result.frames) == 3

    def test_js_frame_details(self, parser):
        text = FIXTURES_DIR.joinpath("javascript_error.txt").read_text()
        result = parser.parse(text)
        first = result.frames[0]
        assert first.file_path == "src/components/UserList.js"
        assert first.line_number == 24
        assert first.function_name == "Object.renderList"


class TestJavaParsing:
    def test_parse_java_stacktrace(self, parser):
        text = FIXTURES_DIR.joinpath("java_stacktrace.txt").read_text()
        result = parser.parse(text)
        assert result.language == "java"
        assert len(result.frames) == 3

    def test_java_frame_details(self, parser):
        text = FIXTURES_DIR.joinpath("java_stacktrace.txt").read_text()
        result = parser.parse(text)
        first = result.frames[0]
        assert first.file_path == "StringHelper.java"
        assert first.line_number == 28


class TestDartParsing:
    def test_parse_dart_error(self, parser):
        text = FIXTURES_DIR.joinpath("dart_error.txt").read_text()
        result = parser.parse(text)
        assert result.language == "dart"
        assert len(result.frames) == 3

    def test_dart_frame_details(self, parser):
        text = FIXTURES_DIR.joinpath("dart_error.txt").read_text()
        result = parser.parse(text)
        first = result.frames[0]
        assert "user_model.dart" in first.file_path
        assert first.line_number == 34
        assert first.function_name == "UserModel.toJson"


class TestParsedErrorModel:
    def test_default_values(self):
        err = ParsedError(language="python", exception_type="Error", message="msg")
        assert err.frames == []
        assert err.raw_text == ""
