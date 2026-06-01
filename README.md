# DebugLens — Production Error Root-Cause Analyzer

Paste a stack trace, error log, or Sentry error — DebugLens reads your codebase (local repo or GitHub URL), traces the call chain from the crash point to the root cause, searches StackOverflow and GitHub Issues for similar known problems, and suggests a concrete fix with exact file + line references.

## Quick Start

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
# Edit .env with your API keys

# 5. Start API server
uvicorn src.api.main:app --reload --port 8000

# 6. Start UI (separate terminal)
streamlit run ui/app.py --server.port 8501

# Open http://localhost:8501
```

## How It Works

1. **Error Parser** — Regex + LLM hybrid parsing for Python, JavaScript, Java, Dart stack traces
2. **Code Locator** — Reads source at each stack frame (local filesystem or GitHub API)
3. **Call Chain Tracer** — Traces execution path with Tree-sitter AST analysis
4. **Root Cause Analyzer** — LLM reasons through code + chain to find actual cause
5. **Similar Issues Search** — StackOverflow API + GitHub Issues search
6. **Fix Suggestion Generator** — Concrete code fix with file:line, prevention tips

## API

```
POST /api/analyze    — Full analysis pipeline
POST /api/parse      — Quick parse without LLM analysis
GET  /api/health     — Health check
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `gemini` | `openai` or `gemini` |
| `LLM_API_KEY` | — | Your LLM API key |
| `LLM_MODEL` | auto | `gpt-4o-mini` or `gemini-2.5-flash` |
| `GITHUB_TOKEN` | — | For private GitHub repos |

## Testing

```bash
pytest tests/ -v
```

## Docker

```bash
docker build -t debuglens .
docker run -p 8000:8000 debuglens
```

## Tech Stack

- Python 3.11+, LangChain 0.3.x, FastAPI, Streamlit
- Tree-sitter for AST analysis
- OpenAI / Google Gemini for LLM
- StackOverflow + GitHub APIs for similar issue search
