# DebugLens — Production Error Root-Cause Analyzer

> Build spec for Cursor/Claude agents. Follow this document to build and deploy the project.

## Purpose

Paste a stack trace, error log, or Sentry error — DebugLens reads your codebase (local repo or GitHub URL), traces the call chain from the crash point to the root cause, searches StackOverflow and GitHub Issues for similar known problems, and suggests a concrete fix with exact file + line references.

**Problem it solves:** Developers spend 30-60 minutes per production error manually reading stack traces, tracing code paths, and searching for known issues. DebugLens automates this into a 30-second pipeline.

## Architecture

```
Input (stack trace / error log / Sentry URL)
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                    ANALYSIS PIPELINE                     │
│                                                          │
│  1. Error Parser                                         │
│     Regex + LLM hybrid parsing                           │
│     Output: exception type, message, frame list          │
│         │                                                │
│         ▼                                                │
│  2. Code Locator                                         │
│     Reads source at each stack frame (local/GitHub)      │
│     Tree-sitter AST for structure understanding          │
│         │                                                │
│         ▼                                                │
│  3. Call Chain Tracer                                     │
│     Traces execution path upward through frames          │
│     Builds visual call chain with context                │
│         │                                                │
│         ▼                                                │
│  4. Root Cause Analyzer (LLM)                            │
│     Reasons through code + chain to find actual cause    │
│         │                                                │
│         ▼                                                │
│  5. Similar Issues Search                                │
│     StackOverflow API + GitHub Issues search             │
│     Returns top matches with accepted answers            │
│         │                                                │
│         ▼                                                │
│  6. Fix Suggestion Generator (LLM)                       │
│     Root cause + similar issues + source code            │
│     Output: explanation, code diff fix, prevention tips  │
└─────────────────────────────────────────────────────────┘
    │
    ▼
Structured Report: root cause, call chain, fix, similar issues
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| LLM orchestration | LangChain 0.3.x |
| LLM | OpenAI `gpt-4o-mini` OR Google `gemini-2.5-flash` (user-configured) |
| Code parsing | Tree-sitter (Python, JavaScript, TypeScript, Dart, Java grammars) |
| GitHub access | PyGithub + GitHub REST API |
| Search | StackOverflow API (StackExchange), GitHub Search API |
| API server | FastAPI + Uvicorn |
| Frontend | Streamlit |
| Python version | 3.11+ |

## Directory Structure

```
debuglens/
├── src/
│   ├── __init__.py
│   ├── config.py                    # Environment + settings management
│   ├── parser/
│   │   ├── __init__.py
│   │   ├── error_parser.py          # Stack trace parsing (regex + LLM fallback)
│   │   ├── patterns.py              # Language-specific regex patterns
│   │   └── models.py                # ParsedError, StackFrame dataclasses
│   ├── locator/
│   │   ├── __init__.py
│   │   ├── code_locator.py          # Read source code at file:line
│   │   ├── local_repo.py            # Local filesystem reader
│   │   ├── github_repo.py           # GitHub API reader
│   │   └── ast_analyzer.py          # Tree-sitter AST parsing
│   ├── tracer/
│   │   ├── __init__.py
│   │   └── call_tracer.py           # Build call chain from frames
│   ├── analyzer/
│   │   ├── __init__.py
│   │   ├── root_cause.py            # LLM root-cause reasoning
│   │   └── prompts.py               # Analysis prompt templates
│   ├── search/
│   │   ├── __init__.py
│   │   ├── stackoverflow.py         # StackOverflow API search
│   │   └── github_issues.py         # GitHub Issues search
│   ├── fixer/
│   │   ├── __init__.py
│   │   ├── fix_generator.py         # LLM fix suggestion
│   │   └── prompts.py               # Fix generation prompts
│   ├── pipeline/
│   │   ├── __init__.py
│   │   └── debuglens.py             # Main pipeline orchestrator
│   └── api/
│       ├── __init__.py
│       ├── main.py                  # FastAPI app
│       ├── routes.py                # API endpoints
│       └── schemas.py               # Request/response Pydantic models
├── ui/
│   └── app.py                       # Streamlit interface
├── tests/
│   ├── __init__.py
│   ├── test_parser.py               # Error parsing tests
│   ├── test_locator.py              # Code location tests
│   ├── test_tracer.py               # Call chain tests
│   ├── test_pipeline.py             # Integration tests
│   └── fixtures/                    # Sample stack traces for testing
│       ├── python_traceback.txt
│       ├── javascript_error.txt
│       ├── java_stacktrace.txt
│       └── dart_error.txt
├── .env.example
├── .gitignore
├── requirements.txt
├── Dockerfile
└── README.md
```

## Data Models

### `src/parser/models.py`

```python
from dataclasses import dataclass, field

@dataclass
class StackFrame:
    file_path: str
    line_number: int
    function_name: str
    code_snippet: str | None = None
    module: str | None = None

@dataclass
class ParsedError:
    language: str                    # python, javascript, java, dart
    exception_type: str              # e.g., "TypeError", "NullPointerException"
    message: str                     # The error message
    frames: list[StackFrame] = field(default_factory=list)
    raw_text: str = ""               # Original input

@dataclass
class CodeContext:
    frame: StackFrame
    source_lines: list[str]          # Lines around the error (±10 lines)
    function_body: str | None = None # Full function containing the error
    class_name: str | None = None    # Enclosing class if any
    imports: list[str] = field(default_factory=list)

@dataclass
class CallChainNode:
    frame: StackFrame
    code_context: CodeContext
    reasoning: str = ""              # Why this frame matters

@dataclass
class SimilarIssue:
    source: str                      # "stackoverflow" or "github"
    title: str
    url: str
    score: int
    answer_snippet: str | None = None
    is_accepted: bool = False

@dataclass
class DiagnosticReport:
    error: ParsedError
    call_chain: list[CallChainNode]
    root_cause: str                  # LLM-generated root cause explanation
    similar_issues: list[SimilarIssue]
    suggested_fix: str               # LLM-generated fix with code
    fix_file: str | None = None      # File to apply fix in
    fix_line: int | None = None      # Line number for fix
    confidence: str = "medium"       # low, medium, high
```

## Implementation Guide

### 1. Error Parser (`src/parser/error_parser.py`)

Parses stack traces from multiple languages using regex first, LLM fallback for unusual formats.

```python
import re
from .models import ParsedError, StackFrame
from .patterns import PATTERNS

class ErrorParser:
    """Parse stack traces from Python, JavaScript, Java, Dart."""

    def parse(self, error_text: str) -> ParsedError:
        language = self._detect_language(error_text)
        frames = self._extract_frames(error_text, language)
        exc_type, message = self._extract_exception(error_text, language)

        if not frames:
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

    def _extract_frames(self, text: str, language: str) -> list[StackFrame]:
        pattern = PATTERNS.get(language)
        if not pattern:
            return []
        frames = []
        for match in re.finditer(pattern, text):
            frames.append(StackFrame(
                file_path=match.group("file"),
                line_number=int(match.group("line")),
                function_name=match.group("func") or "<unknown>",
            ))
        return frames

    def _extract_exception(self, text: str, language: str) -> tuple[str, str]:
        # Language-specific exception extraction
        if language == "python":
            match = re.search(r'^(\w+(?:\.\w+)*Error|\w+Exception): (.+)$', text, re.MULTILINE)
            if match:
                return match.group(1), match.group(2)
        return "UnknownError", text.split('\n')[-1]

    def _llm_fallback_parse(self, text: str) -> ParsedError:
        # Use LLM to parse unusual/custom error formats
        # Structured output: {language, exception_type, message, frames[]}
        pass
```

### `src/parser/patterns.py`

```python
PATTERNS = {
    "python": r'File "(?P<file>[^"]+)", line (?P<line>\d+), in (?P<func>\w+)',
    "javascript": r'at (?P<func>[^\s]+) \((?P<file>[^:]+):(?P<line>\d+):\d+\)',
    "java": r'at (?P<func>[^\(]+)\((?P<file>[^:]+):(?P<line>\d+)\)',
    "dart": r'#\d+\s+(?P<func>[^\s]+) \((?P<file>[^:]+):(?P<line>\d+):\d+\)',
}
```

### 2. Code Locator (`src/locator/`)

**code_locator.py** — Factory that reads source from local repo or GitHub:

```python
class CodeLocator:
    """Reads source code at stack frame locations."""

    def __init__(self, repo_source: str):
        if repo_source.startswith("https://github.com"):
            self.reader = GitHubRepoReader(repo_source)
        else:
            self.reader = LocalRepoReader(repo_source)

    def get_context(self, frame: StackFrame, context_lines: int = 15) -> CodeContext:
        source = self.reader.read_file(frame.file_path)
        if not source:
            return CodeContext(frame=frame, source_lines=[])

        lines = source.split('\n')
        start = max(0, frame.line_number - context_lines - 1)
        end = min(len(lines), frame.line_number + context_lines)
        context = lines[start:end]

        function_body = self._extract_function(lines, frame)
        class_name = self._find_enclosing_class(lines, frame)
        imports = self._extract_imports(lines)

        return CodeContext(
            frame=frame,
            source_lines=context,
            function_body=function_body,
            class_name=class_name,
            imports=imports,
        )
```

**local_repo.py:**
```python
from pathlib import Path

class LocalRepoReader:
    def __init__(self, repo_path: str):
        self.root = Path(repo_path)

    def read_file(self, file_path: str) -> str | None:
        full_path = self.root / file_path
        if full_path.exists():
            return full_path.read_text()
        # Try relative path resolution
        for match in self.root.rglob(Path(file_path).name):
            return match.read_text()
        return None
```

**github_repo.py:**
```python
from github import Github

class GitHubRepoReader:
    def __init__(self, repo_url: str, token: str | None = None):
        self.gh = Github(token) if token else Github()
        self.repo = self._parse_repo(repo_url)
        self._file_cache: dict[str, str] = {}

    def read_file(self, file_path: str) -> str | None:
        if file_path in self._file_cache:
            return self._file_cache[file_path]
        try:
            content = self.repo.get_contents(file_path)
            decoded = content.decoded_content.decode('utf-8')
            self._file_cache[file_path] = decoded
            return decoded
        except Exception:
            return None

    def _parse_repo(self, url: str):
        # Extract owner/repo from URL
        parts = url.rstrip('/').split('/')
        return self.gh.get_repo(f"{parts[-2]}/{parts[-1]}")
```

**ast_analyzer.py** — Tree-sitter for deeper code understanding:
```python
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

class ASTAnalyzer:
    """Uses Tree-sitter to understand code structure around errors."""

    def __init__(self, language: str = "python"):
        self.parser = Parser(Language(tspython.language()))

    def find_function_at_line(self, source: str, line: int) -> str | None:
        """Extract the full function body containing the given line."""
        tree = self.parser.parse(bytes(source, "utf8"))
        return self._find_node_at_line(tree.root_node, line, "function_definition")

    def find_class_at_line(self, source: str, line: int) -> str | None:
        """Find the enclosing class for a given line."""
        tree = self.parser.parse(bytes(source, "utf8"))
        return self._find_node_at_line(tree.root_node, line, "class_definition")

    def get_function_calls_in_range(self, source: str, start: int, end: int) -> list[str]:
        """List all function calls within a line range."""
        tree = self.parser.parse(bytes(source, "utf8"))
        calls = []
        self._collect_calls(tree.root_node, start, end, calls)
        return calls

    def _find_node_at_line(self, node, line: int, node_type: str) -> str | None:
        if node.type == node_type:
            if node.start_point[0] <= line - 1 <= node.end_point[0]:
                return node.text.decode("utf8")
        for child in node.children:
            result = self._find_node_at_line(child, line, node_type)
            if result:
                return result
        return None

    def _collect_calls(self, node, start: int, end: int, calls: list):
        if node.type == "call" and start <= node.start_point[0] + 1 <= end:
            func_node = node.child_by_field_name("function")
            if func_node:
                calls.append(func_node.text.decode("utf8"))
        for child in node.children:
            self._collect_calls(child, start, end, calls)
```

### 3. Call Chain Tracer (`src/tracer/call_tracer.py`)

```python
class CallChainTracer:
    """Builds a traced call chain from stack frames with source context."""

    def __init__(self, locator: CodeLocator):
        self.locator = locator

    def trace(self, error: ParsedError) -> list[CallChainNode]:
        chain = []
        for frame in error.frames:
            context = self.locator.get_context(frame)
            chain.append(CallChainNode(
                frame=frame,
                code_context=context,
            ))
        return chain

    def format_chain(self, chain: list[CallChainNode]) -> str:
        """Format call chain as readable text for LLM input."""
        parts = []
        for i, node in enumerate(chain):
            parts.append(
                f"--- Frame {i + 1}: {node.frame.function_name} ---\n"
                f"File: {node.frame.file_path}:{node.frame.line_number}\n"
                f"Code:\n{chr(10).join(node.code_context.source_lines)}\n"
            )
            if node.code_context.function_body:
                parts.append(f"Full function:\n{node.code_context.function_body}\n")
        return "\n".join(parts)
```

### 4. Root Cause Analyzer (`src/analyzer/root_cause.py`)

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

class RootCauseAnalyzer:
    """LLM-powered root cause analysis from call chain + error."""

    def __init__(self, llm):
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", ROOT_CAUSE_SYSTEM_PROMPT),
            ("human", ROOT_CAUSE_USER_PROMPT),
        ])
        self.chain = self.prompt | self.llm | JsonOutputParser()

    def analyze(self, error: ParsedError, call_chain_text: str) -> dict:
        result = self.chain.invoke({
            "error_type": error.exception_type,
            "error_message": error.message,
            "language": error.language,
            "call_chain": call_chain_text,
        })
        return result
        # Returns: {root_cause, confidence, affected_frame, explanation}
```

### `src/analyzer/prompts.py`

```python
ROOT_CAUSE_SYSTEM_PROMPT = """You are an expert debugger analyzing production errors.
Given a stack trace and the source code at each frame, identify the ROOT CAUSE — not just the
symptom. Think step by step through the call chain.

Output JSON:
{
    "root_cause": "One sentence: what actually caused this error",
    "explanation": "2-3 paragraphs explaining the reasoning chain",
    "affected_frame": 0,  // 0-indexed frame number where the root cause is
    "confidence": "low|medium|high",
    "category": "null_reference|type_error|async_race|missing_validation|config_error|dependency|logic_error|other"
}"""

ROOT_CAUSE_USER_PROMPT = """Error: {error_type}: {error_message}
Language: {language}

Call Chain (from innermost to outermost):
{call_chain}

Analyze the call chain and identify the root cause."""

FIX_SYSTEM_PROMPT = """You are an expert debugger. Given a root cause analysis, the relevant source
code, and similar issues found online, suggest a concrete fix.

Output JSON:
{
    "explanation": "What went wrong and why",
    "fix_description": "What the fix does",
    "fix_code": "The corrected code (full function, not a diff)",
    "fix_file": "file path to apply the fix",
    "fix_line": 42,
    "prevention": "How to prevent this class of bug in the future",
    "tests_to_add": "What test would catch this"
}"""

FIX_USER_PROMPT = """Root Cause Analysis:
{root_cause}

Source Code at Error Location:
{source_code}

Similar Issues Found Online:
{similar_issues}

Suggest a concrete fix."""
```

### 5. Similar Issues Search (`src/search/`)

**stackoverflow.py:**
```python
import requests

class StackOverflowSearch:
    """Search StackOverflow for similar errors."""

    BASE_URL = "https://api.stackexchange.com/2.3"

    def search(self, error_type: str, message: str, language: str, limit: int = 5) -> list[SimilarIssue]:
        query = f"{language} {error_type} {message[:100]}"
        params = {
            "order": "desc",
            "sort": "relevance",
            "intitle": error_type,
            "tagged": language,
            "site": "stackoverflow",
            "filter": "withbody",
            "pagesize": limit,
        }
        resp = requests.get(f"{self.BASE_URL}/search/advanced", params={**params, "q": query})
        results = []
        for item in resp.json().get("items", []):
            results.append(SimilarIssue(
                source="stackoverflow",
                title=item["title"],
                url=item["link"],
                score=item["score"],
                answer_snippet=self._get_accepted_answer(item.get("accepted_answer_id")),
                is_accepted=item.get("is_answered", False),
            ))
        return results

    def _get_accepted_answer(self, answer_id: int | None) -> str | None:
        if not answer_id:
            return None
        resp = requests.get(
            f"{self.BASE_URL}/answers/{answer_id}",
            params={"site": "stackoverflow", "filter": "withbody"},
        )
        items = resp.json().get("items", [])
        if items:
            return items[0].get("body", "")[:500]
        return None
```

**github_issues.py:**
```python
class GitHubIssuesSearch:
    """Search GitHub Issues for similar errors."""

    def search(self, error_type: str, message: str, repo_url: str | None = None, limit: int = 5) -> list[SimilarIssue]:
        query = f"{error_type} {message[:80]}"
        if repo_url:
            owner_repo = "/".join(repo_url.rstrip("/").split("/")[-2:])
            query = f"repo:{owner_repo} {query}"

        params = {"q": f"{query} is:issue", "per_page": limit, "sort": "relevance"}
        resp = requests.get("https://api.github.com/search/issues", params=params)
        results = []
        for item in resp.json().get("items", []):
            results.append(SimilarIssue(
                source="github",
                title=item["title"],
                url=item["html_url"],
                score=item.get("reactions", {}).get("+1", 0),
                answer_snippet=item.get("body", "")[:500],
                is_accepted=item["state"] == "closed",
            ))
        return results
```

### 6. Main Pipeline (`src/pipeline/debuglens.py`)

```python
class DebugLensPipeline:
    """Main orchestrator: error → analysis → report."""

    def __init__(self, llm, repo_source: str):
        self.parser = ErrorParser()
        self.locator = CodeLocator(repo_source)
        self.tracer = CallChainTracer(self.locator)
        self.analyzer = RootCauseAnalyzer(llm)
        self.so_search = StackOverflowSearch()
        self.gh_search = GitHubIssuesSearch()
        self.fixer = FixGenerator(llm)

    def analyze(self, error_text: str, on_progress=None) -> DiagnosticReport:
        # Step 1: Parse error
        if on_progress:
            on_progress("Parsing error...")
        error = self.parser.parse(error_text)

        # Step 2: Locate code and build call chain
        if on_progress:
            on_progress(f"Reading source code ({len(error.frames)} frames)...")
        call_chain = self.tracer.trace(error)
        chain_text = self.tracer.format_chain(call_chain)

        # Step 3: Root cause analysis
        if on_progress:
            on_progress("Analyzing root cause...")
        rca = self.analyzer.analyze(error, chain_text)

        # Step 4: Search for similar issues
        if on_progress:
            on_progress("Searching for similar issues...")
        similar = (
            self.so_search.search(error.exception_type, error.message, error.language)
            + self.gh_search.search(error.exception_type, error.message)
        )

        # Step 5: Generate fix
        if on_progress:
            on_progress("Generating fix suggestion...")
        source_at_error = call_chain[rca.get("affected_frame", 0)].code_context if call_chain else None
        fix = self.fixer.generate(rca, source_at_error, similar)

        return DiagnosticReport(
            error=error,
            call_chain=call_chain,
            root_cause=rca["root_cause"],
            similar_issues=similar,
            suggested_fix=fix["fix_code"],
            fix_file=fix.get("fix_file"),
            fix_line=fix.get("fix_line"),
            confidence=rca.get("confidence", "medium"),
        )
```

### 7. FastAPI Server (`src/api/`)

**main.py:**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import router

app = FastAPI(
    title="DebugLens",
    description="Production Error Root-Cause Analyzer",
    version="1.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router, prefix="/api")
```

**routes.py:**
```python
from fastapi import APIRouter
from .schemas import AnalyzeRequest, AnalyzeResponse, SettingsRequest

router = APIRouter()

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_error(request: AnalyzeRequest):
    """Analyze a stack trace and return root cause + fix."""
    pass

@router.post("/parse")
async def parse_only(request: AnalyzeRequest):
    """Parse a stack trace without full analysis (quick preview)."""
    pass

@router.get("/health")
async def health():
    return {"status": "ok"}
```

**schemas.py:**
```python
from pydantic import BaseModel

class AnalyzeRequest(BaseModel):
    error_text: str
    repo_source: str              # Local path or GitHub URL
    github_token: str | None = None
    llm_provider: str = "gemini"  # "openai" or "gemini"
    llm_api_key: str = ""
    llm_model: str | None = None

class FrameResponse(BaseModel):
    file_path: str
    line_number: int
    function_name: str
    code_snippet: list[str]

class SimilarIssueResponse(BaseModel):
    source: str
    title: str
    url: str
    score: int
    is_accepted: bool

class AnalyzeResponse(BaseModel):
    error_type: str
    error_message: str
    language: str
    root_cause: str
    confidence: str
    call_chain: list[FrameResponse]
    similar_issues: list[SimilarIssueResponse]
    suggested_fix: str
    fix_file: str | None
    fix_line: int | None
```

### 8. Streamlit UI (`ui/app.py`)

Layout:
- **Sidebar:** Settings (API keys, LLM provider, repo source), stored in `st.session_state`
- **Main area:**
  - Text area: paste stack trace / error log
  - "Analyze" button
  - Progress steps displayed as they complete
  - Results in collapsible sections:
    - **Error Summary** — parsed error type, message, language
    - **Call Chain** — visual trace with code snippets at each frame
    - **Root Cause** — LLM analysis with confidence badge
    - **Similar Issues** — links to StackOverflow/GitHub with relevance scores
    - **Suggested Fix** — code diff with file:line, copy button
    - **Prevention Tips** — how to avoid this class of bug

```python
import streamlit as st

st.set_page_config(page_title="DebugLens", page_icon="🔍", layout="wide")

# Sidebar — Settings
with st.sidebar:
    st.header("Settings")
    provider = st.selectbox("LLM Provider", ["gemini", "openai"])
    api_key = st.text_input("API Key", type="password")
    repo_source = st.text_input("Repository", placeholder="/path/to/repo or https://github.com/user/repo")
    github_token = st.text_input("GitHub Token (optional)", type="password")

# Main
st.title("DebugLens")
st.caption("Paste a stack trace. Get the root cause and fix.")

error_text = st.text_area("Stack Trace / Error Log", height=250, placeholder="Paste your error here...")

if st.button("Analyze", type="primary", disabled=not error_text or not api_key):
    with st.status("Analyzing...", expanded=True) as status:
        # Run pipeline with progress callbacks
        # Display results in expanders
        pass
```

## Environment Variables

```env
# LLM (user configures via UI, but .env works for API mode)
LLM_PROVIDER=gemini
LLM_API_KEY=your-api-key
LLM_MODEL=gemini-2.5-flash

# GitHub (optional, for private repos)
GITHUB_TOKEN=your-github-token

# Server
API_HOST=0.0.0.0
API_PORT=8000
```

## Dependencies (`requirements.txt`)

```
langchain>=0.3.0
langchain-openai>=0.3.0
langchain-google-genai>=2.0.0
fastapi>=0.115.0
uvicorn>=0.30.0
streamlit>=1.40.0
PyGithub>=2.0.0
tree-sitter>=0.23.0
tree-sitter-python>=0.23.0
tree-sitter-javascript>=0.23.0
requests>=2.32.0
python-dotenv>=1.0.0
pydantic>=2.0.0
```

## Setup & Run

```bash
# 1. Clone
git clone https://github.com/darsigangothri06/debuglens.git
cd debuglens

# 2. Virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install
pip install -r requirements.txt

# 4. Environment (optional — can use UI settings instead)
cp .env.example .env

# 5. Start API server
uvicorn src.api.main:app --reload --port 8000

# 6. Start UI (separate terminal)
streamlit run ui/app.py --server.port 8501

# Open http://localhost:8501
```

## Testing

```bash
# Run tests
pytest tests/ -v

# Test with sample traces
python -m src.pipeline.debuglens --file tests/fixtures/python_traceback.txt --repo /path/to/repo
```

## Deployment

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## GitHub Repository Setup

> **CRITICAL — READ BEFORE ANY GIT OPERATION**
>
> This project MUST be pushed to the **personal** GitHub account ONLY.
> - **CORRECT account:** `darsigangothri06` (gangothri.darsi@gmail.com)
> - **DO NOT USE:** `gangothri-bryt` / `gangothri@bryt.in` — this is the company work account. NEVER push personal projects to the work account.
> - **DO NOT modify global git config** (`--global`). Only set LOCAL config inside this repo.
> - **VERIFY before every push:** Run `git config user.name && git config user.email` and confirm it shows `darsigangothri06` / `gangothri.darsi@gmail.com`. If it doesn't, STOP and fix it.

```bash
# 1. Create repo on GitHub first (via browser or gh cli with personal account)
gh repo create darsigangothri06/debuglens --public --description "Production error root-cause analyzer with LLM-powered debugging"

# 2. Initialize local repo
git init

# 3. SET LOCAL GIT IDENTITY (NOT --global)
git config user.name "darsigangothri06"
git config user.email "gangothri.darsi@gmail.com"

# 4. VERIFY identity before proceeding
git config user.name   # Must show: darsigangothri06
git config user.email  # Must show: gangothri.darsi@gmail.com

# 5. Add remote and push
git remote add origin https://github.com/darsigangothri06/debuglens.git
git add .
git commit -m "feat: DebugLens — production error root-cause analyzer with LLM"
git push -u origin main
```

If `gh` CLI is authenticated as the work account, authenticate personal account first:
```bash
gh auth login  # Choose: github.com → HTTPS → Login with browser → authenticate as darsigangothri06
```
