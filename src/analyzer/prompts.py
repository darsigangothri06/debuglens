ROOT_CAUSE_SYSTEM_PROMPT = """You are an expert debugger analyzing production errors.
Given a stack trace and the source code at each frame, identify the ROOT CAUSE — not just the
symptom. Think step by step through the call chain.

Output JSON:
{
    "root_cause": "One sentence: what actually caused this error",
    "explanation": "2-3 paragraphs explaining the reasoning chain",
    "affected_frame": 0,
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
