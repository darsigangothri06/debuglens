import re
from typing import List, Optional

from ..parser.models import CodeContext, StackFrame
from .ast_analyzer import ASTAnalyzer
from .github_repo import GitHubRepoReader
from .local_repo import LocalRepoReader


class CodeLocator:
    """Reads source code at stack frame locations from local repo or GitHub."""

    def __init__(self, repo_source: str, github_token: Optional[str] = None):
        if repo_source.startswith("https://github.com"):
            self.reader = GitHubRepoReader(repo_source, token=github_token)
        else:
            self.reader = LocalRepoReader(repo_source)
        self._ast_cache = {}

    def get_context(self, frame: StackFrame, context_lines: int = 15) -> CodeContext:
        source = self.reader.read_file(frame.file_path)
        if not source:
            return CodeContext(frame=frame, source_lines=[])

        lines = source.split("\n")
        start = max(0, frame.line_number - context_lines - 1)
        end = min(len(lines), frame.line_number + context_lines)
        context = lines[start:end]

        function_body = self._extract_function(source, frame)
        class_name = self._find_enclosing_class(source, frame)
        imports = self._extract_imports(lines)

        return CodeContext(
            frame=frame,
            source_lines=context,
            function_body=function_body,
            class_name=class_name,
            imports=imports,
        )

    def _get_ast(self, language: str) -> ASTAnalyzer:
        if language not in self._ast_cache:
            self._ast_cache[language] = ASTAnalyzer(language)
        return self._ast_cache[language]

    def _extract_function(self, source: str, frame: StackFrame) -> Optional[str]:
        try:
            ast = self._get_ast("python")
            return ast.find_function_at_line(source, frame.line_number)
        except Exception:
            return None

    def _find_enclosing_class(self, source: str, frame: StackFrame) -> Optional[str]:
        try:
            ast = self._get_ast("python")
            class_body = ast.find_class_at_line(source, frame.line_number)
            if class_body:
                first_line = class_body.split("\n")[0]
                match = re.match(r"class\s+(\w+)", first_line)
                if match:
                    return match.group(1)
            return None
        except Exception:
            return None

    def _extract_imports(self, lines: List[str]) -> List[str]:
        imports = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                imports.append(stripped)
        return imports
