from typing import List, Optional

from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    error_text: str
    repo_source: str
    github_token: Optional[str] = None
    llm_provider: str = "gemini"
    llm_api_key: str = ""
    llm_model: Optional[str] = None


class FrameResponse(BaseModel):
    file_path: str
    line_number: int
    function_name: str
    code_snippet: List[str]


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
    call_chain: List[FrameResponse]
    similar_issues: List[SimilarIssueResponse]
    suggested_fix: str
    fix_file: Optional[str]
    fix_line: Optional[int]
