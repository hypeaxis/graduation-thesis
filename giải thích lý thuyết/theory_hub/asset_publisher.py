from __future__ import annotations

import shutil
from pathlib import Path

from .config import OUTPUT_DIR


class AssetPublisher:
    def __init__(self, source_dir: Path | None = None) -> None:
        self._source_dir = source_dir or Path(__file__).resolve().parent / "assets"

    def publish(self, output_dir: Path = OUTPUT_DIR) -> None:
        target_dir = output_dir / "assets"
        target_dir.mkdir(parents=True, exist_ok=True)

        source_files = {source_path.name for source_path in self._source_dir.iterdir() if source_path.is_file()}
        for target_path in target_dir.iterdir():
            if target_path.is_file() and target_path.name not in source_files:
                target_path.unlink()

        for source_path in self._source_dir.iterdir():
            if source_path.is_file():
                shutil.copy2(source_path, target_dir / source_path.name)