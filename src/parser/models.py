from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class StackFrame:
    file_path: str
    line_number: int
    function_name: str
    code_snippet: Optional[str] = None
    module: Optional[str] = None


@dataclass
class ParsedError:
    language: str
    exception_type: str
    message: str
    frames: List[StackFrame] = field(default_factory=list)
    raw_text: str = ""


@dataclass
class CodeContext:
    frame: StackFrame
    source_lines: List[str] = field(default_factory=list)
    function_body: Optional[str] = None
    class_name: Optional[str] = None
    imports: List[str] = field(default_factory=list)


@dataclass
class CallChainNode:
    frame: StackFrame
    code_context: CodeContext
    reasoning: str = ""


@dataclass
class SimilarIssue:
    source: str
    title: str
    url: str
    score: int
    answer_snippet: Optional[str] = None
    is_accepted: bool = False


@dataclass
class DiagnosticReport:
    error: ParsedError
    call_chain: List[CallChainNode]
    root_cause: str
    similar_issues: List[SimilarIssue]
    suggested_fix: str
    fix_file: Optional[str] = None
    fix_line: Optional[int] = None
    confidence: str = "medium"
