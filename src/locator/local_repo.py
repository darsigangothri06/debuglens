from pathlib import Path
from typing import Optional


class LocalRepoReader:
    def __init__(self, repo_path: str):
        self.root = Path(repo_path)

    def read_file(self, file_path: str) -> Optional[str]:
        full_path = self.root / file_path
        if full_path.exists():
            return full_path.read_text(errors="replace")
        for match in self.root.rglob(Path(file_path).name):
            return match.read_text(errors="replace")
        return None
