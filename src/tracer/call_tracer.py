from typing import List

from ..locator.code_locator import CodeLocator
from ..parser.models import CallChainNode, ParsedError


class CallChainTracer:
    """Builds a traced call chain from stack frames with source context."""

    def __init__(self, locator: CodeLocator):
        self.locator = locator

    def trace(self, error: ParsedError) -> List[CallChainNode]:
        chain = []
        for frame in error.frames:
            context = self.locator.get_context(frame)
            chain.append(
                CallChainNode(
                    frame=frame,
                    code_context=context,
                )
            )
        return chain

    def format_chain(self, chain: List[CallChainNode]) -> str:
        """Format call chain as readable text for LLM input."""
        parts = []
        for i, node in enumerate(chain):
            source_text = "\n".join(node.code_context.source_lines)
            parts.append(
                f"--- Frame {i + 1}: {node.frame.function_name} ---\n"
                f"File: {node.frame.file_path}:{node.frame.line_number}\n"
                f"Code:\n{source_text}\n"
            )
            if node.code_context.function_body:
                parts.append(f"Full function:\n{node.code_context.function_body}\n")
        return "\n".join(parts)
