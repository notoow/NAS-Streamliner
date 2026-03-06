from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml


@dataclass(frozen=True)
class PathSettings:
    project_root: Path
    inbound_root: Path
    storage_root: Path
    quarantine_root: Path
    log_root: Path
    state_db: Path
    manifest_path: Path
    camera_map_path: Path


@dataclass(frozen=True)
class WatcherSettings:
    scan_interval_seconds: int
    stable_window_seconds: int
    minimum_file_age_seconds: int
    accepted_extensions: tuple[str, ...]
    ignore_hidden_files: bool


@dataclass(frozen=True)
class FFprobeSettings:
    binary: str
    timeout_seconds: int
    metadata_date_keys: tuple[str, ...]
    metadata_model_keys: tuple[str, ...]
    metadata_serial_keys: tuple[str, ...]


@dataclass(frozen=True)
class ClassificationSettings:
    timezone_name: str
    unknown_camera_alias: str
    unknown_date_folder: str
    fallback_to_file_modified_time: bool
    quarantine_on_missing_date: bool
    quarantine_on_missing_camera: bool
    rename_original_files: bool

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)


@dataclass(frozen=True)
class NamingSettings:
    original_basename_template: str
    duplicate_suffix_template: str
    maximum_stem_length: int


@dataclass(frozen=True)
class LoggingSettings:
    level: str
    file_name: str


@dataclass(frozen=True)
class Settings:
    project_name: str
    paths: PathSettings
    watcher: WatcherSettings
    ffprobe: FFprobeSettings
    classification: ClassificationSettings
    naming: NamingSettings
    logging: LoggingSettings


def load_settings(settings_path: str | Path) -> Settings:
    resolved_settings_path = Path(settings_path).resolve()
    with resolved_settings_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    config_dir = resolved_settings_path.parent
    path_section = raw["paths"]
    settings = Settings(
        project_name=str(raw["project_name"]),
        paths=PathSettings(
            project_root=_resolve_path(config_dir, path_section["project_root"]),
            inbound_root=_resolve_path(config_dir, path_section["inbound_root"]),
            storage_root=_resolve_path(config_dir, path_section["storage_root"]),
            quarantine_root=_resolve_path(config_dir, path_section["quarantine_root"]),
            log_root=_resolve_path(config_dir, path_section["log_root"]),
            state_db=_resolve_path(config_dir, path_section["state_db"]),
            manifest_path=_resolve_path(config_dir, path_section["manifest_path"]),
            camera_map_path=_resolve_path(config_dir, path_section["camera_map_path"]),
        ),
        watcher=_build_watcher_settings(raw["watcher"]),
        ffprobe=_build_ffprobe_settings(raw["ffprobe"]),
        classification=_build_classification_settings(raw["classification"]),
        naming=_build_naming_settings(raw["naming"]),
        logging=LoggingSettings(
            level=str(raw["logging"]["level"]),
            file_name=str(raw["logging"]["file_name"]),
        ),
    )
    ensure_runtime_directories(settings)
    return settings


def ensure_runtime_directories(settings: Settings) -> None:
    roots = (
        settings.paths.inbound_root,
        settings.paths.storage_root,
        settings.paths.quarantine_root,
        settings.paths.log_root,
        settings.paths.state_db.parent,
        settings.paths.manifest_path.parent,
    )
    for root in roots:
        root.mkdir(parents=True, exist_ok=True)


def _build_watcher_settings(raw: dict) -> WatcherSettings:
    return WatcherSettings(
        scan_interval_seconds=int(raw["scan_interval_seconds"]),
        stable_window_seconds=int(raw["stable_window_seconds"]),
        minimum_file_age_seconds=int(raw["minimum_file_age_seconds"]),
        accepted_extensions=tuple(str(item).lower() for item in raw["accepted_extensions"]),
        ignore_hidden_files=bool(raw["ignore_hidden_files"]),
    )


def _build_ffprobe_settings(raw: dict) -> FFprobeSettings:
    return FFprobeSettings(
        binary=str(raw["binary"]),
        timeout_seconds=int(raw["timeout_seconds"]),
        metadata_date_keys=tuple(str(item) for item in raw["metadata_date_keys"]),
        metadata_model_keys=tuple(str(item) for item in raw["metadata_model_keys"]),
        metadata_serial_keys=tuple(str(item) for item in raw["metadata_serial_keys"]),
    )


def _build_classification_settings(raw: dict) -> ClassificationSettings:
    return ClassificationSettings(
        timezone_name=str(raw["timezone"]),
        unknown_camera_alias=str(raw["unknown_camera_alias"]),
        unknown_date_folder=str(raw["unknown_date_folder"]),
        fallback_to_file_modified_time=bool(raw["fallback_to_file_modified_time"]),
        quarantine_on_missing_date=bool(raw["quarantine_on_missing_date"]),
        quarantine_on_missing_camera=bool(raw["quarantine_on_missing_camera"]),
        rename_original_files=bool(raw["rename_original_files"]),
    )


def _build_naming_settings(raw: dict) -> NamingSettings:
    return NamingSettings(
        original_basename_template=str(raw["original_basename_template"]),
        duplicate_suffix_template=str(raw["duplicate_suffix_template"]),
        maximum_stem_length=int(raw["maximum_stem_length"]),
    )


def _resolve_path(base_dir: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path

