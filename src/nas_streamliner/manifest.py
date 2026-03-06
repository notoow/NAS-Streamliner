from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .models import ClassificationResult


class ManifestWriter:
    def __init__(self, manifest_path: str | Path) -> None:
        self._manifest_path = Path(manifest_path).resolve()
        self._manifest_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, result: ClassificationResult) -> None:
        self.write_record(result.to_record())

    def write_record(self, payload: dict[str, object]) -> None:
        serializable_payload = dict(payload)
        serializable_payload["recorded_at"] = datetime.now().astimezone().isoformat()
        with self._manifest_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(serializable_payload, ensure_ascii=False))
            handle.write("\n")
