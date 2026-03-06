from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class MediaMetadata:
    source_path: Path
    capture_datetime: datetime | None
    camera_model: str | None
    camera_serial: str | None
    raw_tags: dict[str, str]


@dataclass(frozen=True)
class ClassificationResult:
    status: str
    source_path: Path
    destination_path: Path
    camera_alias: str
    camera_model: str | None
    camera_serial: str | None
    capture_datetime: datetime | None
    matched_on: str
    reason: str | None = None

    def to_record(self) -> dict[str, str | None]:
        return {
            "status": self.status,
            "source_path": str(self.source_path),
            "destination_path": str(self.destination_path),
            "camera_alias": self.camera_alias,
            "camera_model": self.camera_model,
            "camera_serial": self.camera_serial,
            "capture_datetime": self.capture_datetime.isoformat() if self.capture_datetime else None,
            "matched_on": self.matched_on,
            "reason": self.reason,
        }

