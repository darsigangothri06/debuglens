from typing import Dict, Optional

from github import Github


class GitHubRepoReader:
    def __init__(self, repo_url: str, token: Optional[str] = None):
        self.gh = Github(token) if token else Github()
        self.repo = self._parse_repo(repo_url)
        self._file_cache: Dict[str, str] = {}

    def read_file(self, file_path: str) -> Optional[str]:
        if file_path in self._file_cache:
            return self._file_cache[file_path]
        try:
            content = self.repo.get_contents(file_path)
            decoded = content.decoded_content.decode("utf-8")
            self._file_cache[file_path] = decoded
            return decoded
        except Exception:
            return None

    def _parse_repo(self, url: str):
        parts = url.rstrip("/").split("/")
        return self.gh.get_repo(f"{parts[-2]}/{parts[-1]}")
