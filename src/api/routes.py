from fastapi import APIRouter, HTTPException

from ..config import Settings
from ..parser.error_parser import ErrorParser
from ..pipeline.debuglens import DebugLensPipeline
from .schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    FrameResponse,
    SimilarIssueResponse,
)

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_error(request: AnalyzeRequest):
    """Analyze a stack trace and return root cause + fix."""
    if not request.llm_api_key:
        raise HTTPException(status_code=400, detail="LLM API key is required")

    settings = Settings(
        llm_provider=request.llm_provider,
        llm_api_key=request.llm_api_key,
        llm_model=request.llm_model,
        github_token=request.github_token,
    )
    llm = settings.get_llm()
    pipeline = DebugLensPipeline(
        llm=llm,
        repo_source=request.repo_source,
        github_token=request.github_token,
    )
    report = pipeline.analyze(request.error_text)

    return AnalyzeResponse(
        error_type=report.error.exception_type,
        error_message=report.error.message,
        language=report.error.language,
        root_cause=report.root_cause,
        confidence=report.confidence,
        call_chain=[
            FrameResponse(
                file_path=node.frame.file_path,
                line_number=node.frame.line_number,
                function_name=node.frame.function_name,
                code_snippet=node.code_context.source_lines,
            )
            for node in report.call_chain
        ],
        similar_issues=[
            SimilarIssueResponse(
                source=issue.source,
                title=issue.title,
                url=issue.url,
                score=issue.score,
                is_accepted=issue.is_accepted,
            )
            for issue in report.similar_issues
        ],
        suggested_fix=report.suggested_fix,
        fix_file=report.fix_file,
        fix_line=report.fix_line,
    )


@router.post("/parse")
async def parse_only(request: AnalyzeRequest):
    """Parse a stack trace without full analysis (quick preview)."""
    parser = ErrorParser()
    error = parser.parse(request.error_text)
    return {
        "language": error.language,
        "exception_type": error.exception_type,
        "message": error.message,
        "frame_count": len(error.frames),
        "frames": [
            {
                "file_path": f.file_path,
                "line_number": f.line_number,
                "function_name": f.function_name,
            }
            for f in error.frames
        ],
    }


@router.get("/health")
async def health():
    return {"status": "ok"}
