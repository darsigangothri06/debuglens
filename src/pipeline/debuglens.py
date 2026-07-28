from typing import Callable, Optional

from ..analyzer.root_cause import RootCauseAnalyzer
from ..fixer.fix_generator import FixGenerator
from ..locator.code_locator import CodeLocator
from ..parser.error_parser import ErrorParser
from ..parser.models import DiagnosticReport
from ..search.github_issues import GitHubIssuesSearch
from ..search.stackoverflow import StackOverflowSearch
from ..tracer.call_tracer import CallChainTracer


class DebugLensPipeline:
    """Main orchestrator: error -> analysis -> report."""

    def __init__(
        self,
        llm,
        repo_source: str,
        github_token: Optional[str] = None,
    ):
        self.parser = ErrorParser(llm=llm)
        self.locator = CodeLocator(repo_source, github_token=github_token)
        self.tracer = CallChainTracer(self.locator)
        self.analyzer = RootCauseAnalyzer(llm)
        self.so_search = StackOverflowSearch()
        self.gh_search = GitHubIssuesSearch()
        self.fixer = FixGenerator(llm)

    def analyze(
        self,
        error_text: str,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> DiagnosticReport:
        def progress(msg: str):
            if on_progress:
                on_progress(msg)

        # Step 1: Parse error
        progress("Parsing error...")
        error = self.parser.parse(error_text)

        # Step 2: Locate code and build call chain
        progress(f"Reading source code ({len(error.frames)} frames)...")
        call_chain = self.tracer.trace(error)
        chain_text = self.tracer.format_chain(call_chain)

        progress("Analyzing root cause...")
        try:
            rca = self.analyzer.analyze(error, chain_text)
        except Exception as e:
            rca = {
                "root_cause": f"LLM analysis failed: {e}",
                "confidence": "low",
                "affected_frame": 0,
            }

        progress("Searching for similar issues...")
        similar = []
        try:
            similar.extend(
                self.so_search.search(
                    error.exception_type, error.message, error.language
                )
            )
        except Exception:
            pass
        try:
            similar.extend(
                self.gh_search.search(error.exception_type, error.message)
            )
        except Exception:
            pass

        progress("Generating fix suggestion...")
        affected_idx = rca.get("affected_frame", 0)
        source_at_error = None
        if call_chain and 0 <= affected_idx < len(call_chain):
            source_at_error = call_chain[affected_idx].code_context

        try:
            fix = self.fixer.generate(rca, source_at_error, similar)
        except Exception as e:
            fix = {"fix_code": f"Fix generation failed: {e}"}

        return DiagnosticReport(
            error=error,
            call_chain=call_chain,
            root_cause=rca.get("root_cause", "Unable to determine root cause"),
            similar_issues=similar,
            suggested_fix=fix.get("fix_code", ""),
            fix_file=fix.get("fix_file"),
            fix_line=fix.get("fix_line"),
            confidence=rca.get("confidence", "medium"),
        )
