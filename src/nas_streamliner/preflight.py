from __future__ import annotations

import logging
import uuid
from pathlib import Path

from .config import Settings


class SettingsValidationError(RuntimeError):
    pass


def run_preflight(settings: Settings, logger: logging.Logger | None = None) -> None:
    if not settings.preflight.enabled:
        return

    active_logger = logger or logging.getLogger("nas_streamliner")
    _validate_camera_map(settings)

    checks = (
        ("inbound_root", settings.paths.inbound_root, settings.preflight.verify_inbound_exists, False),
        ("storage_root", settings.paths.storage_root, True, settings.preflight.verify_storage_writable),
        ("quarantine_root", settings.paths.quarantine_root, True, settings.preflight.verify_quarantine_writable),
        ("log_root", settings.paths.log_root, True, settings.preflight.verify_log_root_writable),
        ("state_root", settings.paths.state_db.parent, True, settings.preflight.verify_state_root_writable),
        ("manifest_root", settings.paths.manifest_path.parent, True, settings.preflight.verify_state_root_writable),
    )

    seen: set[str] = set()
    for label, path, ensure_exists, verify_writable in checks:
        normalized = str(path.resolve())
        if normalized in seen:
            continue
        seen.add(normalized)
        if ensure_exists:
            _ensure_directory(path, label, create_missing=settings.preflight.create_missing_directories)
        if verify_writable:
            _verify_directory_writable(path, label, settings.preflight.write_probe_file_name)

    active_logger.info(
        "Preflight OK | inbound=%s | storage=%s | quarantine=%s",
        settings.paths.inbound_root,
        settings.paths.storage_root,
        settings.paths.quarantine_root,
    )


def _validate_camera_map(settings: Settings) -> None:
    if not settings.preflight.verify_camera_map_exists:
        return
    if not settings.paths.camera_map_path.is_file():
        raise SettingsValidationError(
            "camera_map_path does not exist: "
            f"{settings.paths.camera_map_path}"
        )


def _ensure_directory(path: Path, label: str, create_missing: bool) -> None:
    if path.exists():
        if not path.is_dir():
            raise SettingsValidationError(f"{label} is not a directory: {path}")
        return

    if not create_missing:
        raise SettingsValidationError(f"{label} does not exist: {path}")

    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise SettingsValidationError(f"Failed to create {label}: {path} ({exc})") from exc


def _verify_directory_writable(path: Path, label: str, probe_file_name: str) -> None:
    probe_name = f"{probe_file_name}.{uuid.uuid4().hex}.tmp"
    probe_path = path / probe_name
    try:
        with probe_path.open("w", encoding="utf-8") as handle:
            handle.write("probe")
        probe_path.unlink()
    except OSError as exc:
        raise SettingsValidationError(
            f"{label} is not writable: {path} ({exc})"
        ) from exc
