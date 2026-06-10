from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from domain.models import LocalLawMetadata
from domain.text import slugify_title


class LawStorage:
    def __init__(self, laws_dir: Path, state_dir: Path) -> None:
        self.laws_dir = laws_dir
        self.state_dir = state_dir
        self.index_path = state_dir / "law_index.json"

    def prepare(self) -> None:
        self.laws_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def load_index(self) -> dict[str, dict[str, Any]]:
        if not self.index_path.exists():
            return {}
        with self.index_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def save_index(self, index: dict[str, dict[str, Any]]) -> None:
        tmp_path = self.index_path.with_suffix(".json.tmp")
        with tmp_path.open("w", encoding="utf-8") as file:
            json.dump(index, file, ensure_ascii=False, indent=2, sort_keys=True)
            file.write("\n")
        tmp_path.replace(self.index_path)

    def law_dir(self, title: str) -> Path:
        return self.laws_dir / slugify_title(title)

    def write_law(self, metadata: LocalLawMetadata, text: str) -> Path:
        law_dir = self.law_dir(metadata.title)
        law_dir.mkdir(parents=True, exist_ok=True)
        text_path = law_dir / "law.txt"
        metadata_path = law_dir / "metadata.json"

        text_path.write_text(text, encoding="utf-8")
        metadata.text_path = str(text_path.relative_to(self.laws_dir.parent))
        metadata_path.write_text(
            json.dumps(metadata.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return law_dir
