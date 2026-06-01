from typing import List, Optional

import tree_sitter_python as tspython
from tree_sitter import Language, Parser


class ASTAnalyzer:
    """Uses Tree-sitter to understand code structure around errors."""

    LANG_MODULES = {
        "python": lambda: Language(tspython.language()),
    }

    def __init__(self, language: str = "python"):
        lang_factory = self.LANG_MODULES.get(language)
        if lang_factory:
            self.parser = Parser(lang_factory())
        else:
            self.parser = Parser(Language(tspython.language()))

    def find_function_at_line(self, source: str, line: int) -> Optional[str]:
        """Extract the full function body containing the given line."""
        tree = self.parser.parse(bytes(source, "utf8"))
        return self._find_node_at_line(tree.root_node, line, "function_definition")

    def find_class_at_line(self, source: str, line: int) -> Optional[str]:
        """Find the enclosing class for a given line."""
        tree = self.parser.parse(bytes(source, "utf8"))
        return self._find_node_at_line(tree.root_node, line, "class_definition")

    def get_function_calls_in_range(
        self, source: str, start: int, end: int
    ) -> List[str]:
        """List all function calls within a line range."""
        tree = self.parser.parse(bytes(source, "utf8"))
        calls: List[str] = []
        self._collect_calls(tree.root_node, start, end, calls)
        return calls

    def _find_node_at_line(self, node, line: int, node_type: str) -> Optional[str]:
        if node.type == node_type:
            if node.start_point[0] <= line - 1 <= node.end_point[0]:
                return node.text.decode("utf8")
        for child in node.children:
            result = self._find_node_at_line(child, line, node_type)
            if result:
                return result
        return None

    def _collect_calls(self, node, start: int, end: int, calls: List[str]):
        if node.type == "call" and start <= node.start_point[0] + 1 <= end:
            func_node = node.child_by_field_name("function")
            if func_node:
                calls.append(func_node.text.decode("utf8"))
        for child in node.children:
            self._collect_calls(child, start, end, calls)
