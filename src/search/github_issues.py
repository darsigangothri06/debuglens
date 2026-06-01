from typing import List, Optional

import requests

from ..parser.models import SimilarIssue


class GitHubIssuesSearch:
    """Search GitHub Issues for similar errors."""

    def search(
        self,
        error_type: str,
        message: str,
        repo_url: Optional[str] = None,
        limit: int = 5,
    ) -> List[SimilarIssue]:
        query = f"{error_type} {message[:80]}"
        if repo_url:
            owner_repo = "/".join(repo_url.rstrip("/").split("/")[-2:])
            query = f"repo:{owner_repo} {query}"

        params = {
            "q": f"{query} is:issue",
            "per_page": limit,
            "sort": "relevance",
        }
        try:
            resp = requests.get(
                "https://api.github.com/search/issues",
                params=params,
                timeout=10,
            )
            resp.raise_for_status()
        except requests.RequestException:
            return []

        results = []
        for item in resp.json().get("items", []):
            results.append(
                SimilarIssue(
                    source="github",
                    title=item["title"],
                    url=item["html_url"],
                    score=item.get("reactions", {}).get("+1", 0),
                    answer_snippet=item.get("body", "")[:500] if item.get("body") else None,
                    is_accepted=item["state"] == "closed",
                )
            )
        return results
