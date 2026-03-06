from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .config import NamingSettings


INVALID_PATH_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
WHITESPACE = re.compile(r"\s+")
SEPARATOR_RUN = re.compile(r"[_-]{2,}")


def sanitize_path_token(value: str, maximum_length: int) -> str:
    if not value:
        return "untitled"

    cleaned = INVALID_PATH_CHARS.sub("_", value.strip())
    cleaned = WHITESPACE.sub("_", cleaned)
    cleaned = SEPARATOR_RUN.sub("_", cleaned)
    cleaned = cleaned.strip("._- ")
    if not cleaned:
        return "untitled"
    return cleaned[:maximum_length]


def build_original_basename(
    capture_datetime: datetime,
    camera_alias: str,
    source_stem: str,
    naming_settings: NamingSettings,
) -> str:
    return naming_settings.original_basename_template.format(
        capture_date_compact=capture_datetime.strftime("%Y%m%d"),
        capture_time_compact=capture_datetime.strftime("%H%M%S"),
        camera_alias=sanitize_path_token(camera_alias, maximum_length=24),
        source_stem=sanitize_path_token(source_stem, naming_settings.maximum_stem_length),
    )


def allocate_destination_path(
    destination_dir: Path,
    basename: str,
    suffix: str,
    duplicate_suffix_template: str,
) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    candidate = destination_dir / f"{basename}{suffix.lower()}"
    if not candidate.exists():
        return candidate

    index = 2
    while True:
        duplicate_suffix = duplicate_suffix_template.format(index=index)
        candidate = destination_dir / f"{basename}{duplicate_suffix}{suffix.lower()}"
        if not candidate.exists():
            return candidate
        index += 1

