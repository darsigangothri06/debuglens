# DebugLens — AI-Powered Error Root Cause Analyzer

> Paste a stack trace. It traces the call chain through your codebase, identifies the root cause via LLM reasoning, searches StackOverflow and GitHub Issues, and suggests a fix.

**[GitHub](https://github.com/darsigangothri06/debuglens)**

---

## What It Does

DebugLens takes a raw stack trace and a codebase (local directory or GitHub repo URL), then:

1. **Parses the stack trace** — extracts file paths, function names, line numbers
2. **Traces the call chain** — uses **Tree-sitter AST parsing** to follow function calls through your actual source code
3. **Identifies root cause** — LLM analyzes the traced code path with the error context to pinpoint what went wrong
4. **Searches for solutions** — queries StackOverflow and GitHub Issues for similar errors
5. **Suggests a fix** — combines code context + community solutions into an actionable fix recommendation

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│ Stack Trace  │────▶│ Stack Parser │────▶│  Tree-sitter │
│ (raw text)   │     │ (extract     │     │  AST Analysis│
└─────────────┘     │  frames)     │     │  (trace call │
                    └──────────────┘     │   chain)     │
                                        └──────┬───────┘
                                               │
                    ┌──────────────┐     ┌──────▼───────┐
                    │ StackOverflow│◀────│  LLM Root    │
                    │ + GitHub     │     │  Cause       │
                    │ Issue Search │     │  Analysis    │
                    └──────┬───────┘     └──────────────┘
                           │
                    ┌──────▼───────┐
                    │  Fix         │
                    │  Suggestion  │
                    └──────────────┘
```

## What Makes This Interesting

- **Not just another "paste error, get answer" tool** — it actually reads your codebase and traces the execution path through AST analysis
- **Tree-sitter for code understanding** — language-agnostic AST parsing (Python, JavaScript, TypeScript, Java, etc.) to follow function calls across files
- **GitHub repo support** — point it at a GitHub URL and it clones + analyzes the repo
- **Community knowledge** — integrates StackOverflow and GitHub Issues search so the fix suggestion includes real-world solutions

## Tech Stack

`Python` `LangChain` `Tree-sitter` `FastAPI` `Streamlit`

## Quick Start

```bash
git clone https://github.com/darsigangothri06/debuglens.git
cd debuglens

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start API
uvicorn src.api.main:app --reload --port 8000

# Start UI (separate terminal)
streamlit run ui/app.py --server.port 8501
```

## How to Use

1. Open the Streamlit UI
2. Paste a stack trace (Python, JavaScript, Java, etc.)
3. Point to your codebase — either a local directory path or a GitHub repo URL
4. Configure your LLM API key (Gemini or OpenAI) in the sidebar
5. Click "Analyze" — watch DebugLens trace through your code and identify the root cause

## Project Structure

```
debuglens/
├── src/
│   ├── analysis/
│   │   ├── stack_parser.py    # Stack trace parsing (multi-language)
│   │   ├── code_tracer.py     # Tree-sitter AST call chain tracing
│   │   └── root_cause.py      # LLM-powered root cause analysis
│   ├── search/
│   │   ├── stackoverflow.py   # StackOverflow API search
│   │   └── github_issues.py   # GitHub Issues search
│   ├── api/
│   │   ├── main.py            # FastAPI app
│   │   └── routes.py          # REST endpoints
│   └── config.py
├── ui/
│   └── app.py                 # Streamlit interface
├── requirements.txt
└── Dockerfile
```

## Key Technical Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Code parsing | **Tree-sitter** | Language-agnostic AST parsing — works with Python, JS, TS, Java, Go without separate parsers |
| Call chain tracing | **Custom AST walker** | Follow function calls across files by resolving imports and tracing call expressions in the AST |
| LLM reasoning | **Structured output** | LLM receives the traced call chain + error context and outputs structured root cause analysis |
| External search | **StackOverflow + GitHub Issues API** | Community solutions complement LLM reasoning with battle-tested fixes |

## Author

**Gangothri Darsi** — [GitHub](https://github.com/darsigangothri06) | [LinkedIn](https://www.linkedin.com/in/darsigangothri06) | [Portfolio](https://gangothridarsi.vercel.app)
