from typing import List, Optional

import requests

from ..parser.models import SimilarIssue


class StackOverflowSearch:
    """Search StackOverflow for similar errors."""

    BASE_URL = "https://api.stackexchange.com/2.3"

    def search(
        self,
        error_type: str,
        message: str,
        language: str,
        limit: int = 5,
    ) -> List[SimilarIssue]:
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
        try:
            resp = requests.get(
                f"{self.BASE_URL}/search/advanced",
                params={**params, "q": query},
                timeout=10,
            )
            resp.raise_for_status()
        except requests.RequestException:
            return []

        results = []
        for item in resp.json().get("items", []):
            results.append(
                SimilarIssue(
                    source="stackoverflow",
                    title=item["title"],
                    url=item["link"],
                    score=item["score"],
                    answer_snippet=self._get_accepted_answer(
                        item.get("accepted_answer_id")
                    ),
                    is_accepted=item.get("is_answered", False),
                )
            )
        return results

    def _get_accepted_answer(self, answer_id: Optional[int]) -> Optional[str]:
        if not answer_id:
            return None
        try:
            resp = requests.get(
                f"{self.BASE_URL}/answers/{answer_id}",
                params={"site": "stackoverflow", "filter": "withbody"},
                timeout=10,
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
            if items:
                return items[0].get("body", "")[:500]
        except requests.RequestException:
            pass
        return None
