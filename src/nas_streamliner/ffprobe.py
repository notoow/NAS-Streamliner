from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import FFprobeSettings
from .models import MediaMetadata


class FFprobeError(RuntimeError):
    pass


def probe_media(
    source_path: str | Path,
    settings: FFprobeSettings,
    local_timezone: ZoneInfo,
) -> MediaMetadata:
    resolved_path = Path(source_path).resolve()
    command = [
        settings.binary,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_entries",
        "format_tags:stream_tags",
        str(resolved_path),
    ]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=settings.timeout_seconds,
            check=False,
        )
    except FileNotFoundError as exc:
        raise FFprobeError(f"ffprobe binary not found: {settings.binary}") from exc
    except subprocess.TimeoutExpired as exc:
        raise FFprobeError(f"ffprobe timed out after {settings.timeout_seconds}s") from exc

    if completed.returncode != 0:
        raise FFprobeError(completed.stderr.strip() or "unknown ffprobe error")

    payload = json.loads(completed.stdout or "{}")
    tags = _collect_tags(payload)

    return MediaMetadata(
        source_path=resolved_path,
        capture_datetime=_pick_datetime(tags, settings.metadata_date_keys, local_timezone),
        camera_model=_pick_model(tags, settings.metadata_model_keys),
        camera_serial=_pick_value(tags, settings.metadata_serial_keys),
        raw_tags=tags,
    )


def _collect_tags(payload: dict) -> dict[str, str]:
    merged: dict[str, str] = {}
    sections: list[dict[str, str]] = []

    format_section = payload.get("format", {})
    if isinstance(format_section, dict):
        sections.append(format_section.get("tags", {}) or {})

    for stream in payload.get("streams", []) or []:
        if isinstance(stream, dict):
            sections.append(stream.get("tags", {}) or {})

    for section in sections:
        for key, value in section.items():
            if value is None:
                continue
            key_string = str(key).strip()
            value_string = str(value).strip()
            if key_string and value_string and key_string not in merged:
                merged[key_string] = value_string

    return merged


def _pick_value(tags: dict[str, str], candidate_keys: tuple[str, ...]) -> str | None:
    lowered = {key.casefold(): value for key, value in tags.items()}
    for candidate in candidate_keys:
        match = lowered.get(candidate.casefold())
        if match:
            return match
    return None


def _pick_model(tags: dict[str, str], candidate_keys: tuple[str, ...]) -> str | None:
    direct_match = _pick_value(tags, candidate_keys)
    if direct_match:
        return direct_match

    lowered = {key.casefold(): value for key, value in tags.items()}
    if lowered.get("make") and lowered.get("model"):
        return f"{lowered['make']} {lowered['model']}".strip()
    return None


def _pick_datetime(
    tags: dict[str, str],
    candidate_keys: tuple[str, ...],
    local_timezone: ZoneInfo,
) -> datetime | None:
    lowered = {key.casefold(): value for key, value in tags.items()}
    for candidate in candidate_keys:
        raw_value = lowered.get(candidate.casefold())
        if not raw_value:
            continue
        parsed = _parse_datetime(raw_value, local_timezone)
        if parsed is not None:
            return parsed
    return None


def _parse_datetime(raw_value: str, local_timezone: ZoneInfo) -> datetime | None:
    normalized = raw_value.strip().replace("Z", "+00:00")
    if not normalized:
        return None

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        parsed = None

    if parsed is None:
        formats = (
            "%Y-%m-%d %H:%M:%S",
            "%Y:%m:%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
        )
        for item in formats:
            try:
                parsed = datetime.strptime(normalized, item)
                break
            except ValueError:
                continue

    if parsed is None:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=local_timezone)
    return parsed.astimezone(local_timezone)

