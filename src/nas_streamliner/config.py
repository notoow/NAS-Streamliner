from __future__ import annotations

import os
import re
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
class EncoderSettings:
    enabled: bool
    ffmpeg_binary: str
    timeout_seconds: int
    auto_encode_after_classification: bool
    proxy_subdir_name: str
    proxy_suffix: str
    output_extension: str
    skip_if_source_not_newer: bool
    video_codec: str
    video_preset: str
    video_crf: int
    pixel_format: str
    max_width: int
    max_height: int
    audio_codec: str
    audio_bitrate: str
    movflags_faststart: bool


@dataclass(frozen=True)
class PreflightSettings:
    enabled: bool
    create_missing_directories: bool
    verify_camera_map_exists: bool
    verify_inbound_exists: bool
    verify_storage_writable: bool
    verify_quarantine_writable: bool
    verify_log_root_writable: bool
    verify_state_root_writable: bool
    write_probe_file_name: str


@dataclass(frozen=True)
class Settings:
    project_name: str
    paths: PathSettings
    watcher: WatcherSettings
    ffprobe: FFprobeSettings
    classification: ClassificationSettings
    naming: NamingSettings
    logging: LoggingSettings
    encoder: EncoderSettings
    preflight: PreflightSettings


ENV_PATTERN = re.compile(r"\$\{(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?::-(?P<default>[^}]*))?\}")


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
        encoder=_build_encoder_settings(raw.get("encoder", {})),
        preflight=_build_preflight_settings(raw.get("preflight", {})),
    )
    return settings


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


def _build_encoder_settings(raw: dict) -> EncoderSettings:
    defaults = {
        "enabled": True,
        "ffmpeg_binary": "ffmpeg",
        "timeout_seconds": 0,
        "auto_encode_after_classification": True,
        "proxy_subdir_name": "Proxy",
        "proxy_suffix": "__proxy_720p_cfr",
        "output_extension": ".mp4",
        "skip_if_source_not_newer": True,
        "video_codec": "libx264",
        "video_preset": "veryfast",
        "video_crf": 23,
        "pixel_format": "yuv420p",
        "max_width": 1280,
        "max_height": 720,
        "audio_codec": "aac",
        "audio_bitrate": "160k",
        "movflags_faststart": True,
    }
    merged = {**defaults, **raw}
    return EncoderSettings(
        enabled=bool(merged["enabled"]),
        ffmpeg_binary=str(merged["ffmpeg_binary"]),
        timeout_seconds=int(merged["timeout_seconds"]),
        auto_encode_after_classification=bool(merged["auto_encode_after_classification"]),
        proxy_subdir_name=str(merged["proxy_subdir_name"]),
        proxy_suffix=str(merged["proxy_suffix"]),
        output_extension=str(merged["output_extension"]),
        skip_if_source_not_newer=bool(merged["skip_if_source_not_newer"]),
        video_codec=str(merged["video_codec"]),
        video_preset=str(merged["video_preset"]),
        video_crf=int(merged["video_crf"]),
        pixel_format=str(merged["pixel_format"]),
        max_width=int(merged["max_width"]),
        max_height=int(merged["max_height"]),
        audio_codec=str(merged["audio_codec"]),
        audio_bitrate=str(merged["audio_bitrate"]),
        movflags_faststart=bool(merged["movflags_faststart"]),
    )


def _build_preflight_settings(raw: dict) -> PreflightSettings:
    defaults = {
        "enabled": True,
        "create_missing_directories": True,
        "verify_camera_map_exists": True,
        "verify_inbound_exists": True,
        "verify_storage_writable": True,
        "verify_quarantine_writable": True,
        "verify_log_root_writable": True,
        "verify_state_root_writable": True,
        "write_probe_file_name": ".nas-streamliner-write-test",
    }
    merged = {**defaults, **raw}
    return PreflightSettings(
        enabled=bool(merged["enabled"]),
        create_missing_directories=bool(merged["create_missing_directories"]),
        verify_camera_map_exists=bool(merged["verify_camera_map_exists"]),
        verify_inbound_exists=bool(merged["verify_inbound_exists"]),
        verify_storage_writable=bool(merged["verify_storage_writable"]),
        verify_quarantine_writable=bool(merged["verify_quarantine_writable"]),
        verify_log_root_writable=bool(merged["verify_log_root_writable"]),
        verify_state_root_writable=bool(merged["verify_state_root_writable"]),
        write_probe_file_name=str(merged["write_probe_file_name"]),
    )


def _resolve_path(base_dir: Path, raw_path: str) -> Path:
    expanded = _expand_env_placeholders(str(raw_path))
    path = Path(os.path.expanduser(expanded))
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path


def _expand_env_placeholders(raw_value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group("name")
        default = match.group("default")
        value = os.environ.get(name)
        if value not in (None, ""):
            return value
        if default is not None:
            return default
        raise ValueError(f"Environment variable '{name}' is not set for path value '{raw_value}'")

    return ENV_PATTERN.sub(replace, raw_value)
