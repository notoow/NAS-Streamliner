from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from ..camera_map import CameraResolver, load_camera_resolver
from ..config import Settings
from ..ffprobe import FFprobeError, probe_media
from ..filesystem import safe_move_file
from ..manifest import ManifestWriter
from ..media_kind import detect_media_kind
from ..models import ClassificationResult, MediaMetadata
from ..naming import allocate_destination_path, build_original_basename, sanitize_path_token


class MediaClassifier:
    def __init__(self, settings: Settings, logger: logging.Logger | None = None) -> None:
        self.settings = settings
        self.logger = logger or logging.getLogger("nas_streamliner")
        self.camera_resolver: CameraResolver = load_camera_resolver(settings.paths.camera_map_path)
        self.manifest = ManifestWriter(settings.paths.manifest_path)

    def classify(self, source_path: str | Path) -> ClassificationResult:
        resolved_path = Path(source_path).resolve()

        try:
            metadata = probe_media(
                source_path=resolved_path,
                settings=self.settings.ffprobe,
                local_timezone=self.settings.classification.timezone,
            )
        except FFprobeError as exc:
            self.logger.warning("ffprobe failed for %s: %s", resolved_path, exc)
            return self._quarantine(
                source_path=resolved_path,
                metadata=_empty_metadata(resolved_path),
                camera_alias=self.settings.classification.unknown_camera_alias,
                matched_on="default",
                reason="ffprobe-failed",
            )

        metadata = self._apply_datetime_fallback(metadata)
        media_kind = detect_media_kind(
            source_stem=resolved_path.stem,
            proxy_filename_patterns=self.settings.classification.proxy_filename_patterns,
        )

        camera_alias, matched_on = self.camera_resolver.resolve(metadata.camera_serial, metadata.camera_model)
        if camera_alias is None:
            camera_alias = self.settings.classification.unknown_camera_alias

        if metadata.capture_datetime is None and self.settings.classification.quarantine_on_missing_date:
            return self._quarantine(resolved_path, metadata, camera_alias, matched_on, "missing-date")

        if camera_alias == self.settings.classification.unknown_camera_alias and self.settings.classification.quarantine_on_missing_camera:
            return self._quarantine(resolved_path, metadata, camera_alias, matched_on, "missing-camera")

        camera_directory = sanitize_path_token(camera_alias, maximum_length=24)
        date_folder = (
            metadata.capture_datetime.strftime("%Y-%m-%d")
            if metadata.capture_datetime
            else self.settings.classification.unknown_date_folder
        )
        leaf_dir_name = self.settings.encoder.proxy_subdir_name if media_kind == "proxy" else "Original"
        destination_dir = self.settings.paths.storage_root / date_folder / camera_directory / leaf_dir_name
        destination_path = allocate_destination_path(
            destination_dir=destination_dir,
            basename=self._build_storage_basename(metadata, camera_alias, resolved_path),
            suffix=resolved_path.suffix,
            duplicate_suffix_template=self.settings.naming.duplicate_suffix_template,
        )
        final_path = safe_move_file(resolved_path, destination_path)

        result = ClassificationResult(
            status="stored",
            source_path=resolved_path,
            destination_path=final_path,
            camera_alias=camera_alias,
            media_kind=media_kind,
            camera_model=metadata.camera_model,
            camera_serial=metadata.camera_serial,
            capture_datetime=metadata.capture_datetime,
            matched_on=matched_on,
            reason=None,
        )
        self.manifest.write(result)
        self.logger.info("Stored %s %s -> %s", media_kind, resolved_path.name, final_path)
        return result

    def _apply_datetime_fallback(self, metadata: MediaMetadata) -> MediaMetadata:
        if metadata.capture_datetime is not None:
            return metadata
        if not self.settings.classification.fallback_to_file_modified_time:
            return metadata

        fallback_datetime = datetime.fromtimestamp(
            metadata.source_path.stat().st_mtime,
            tz=self.settings.classification.timezone,
        )
        return replace(metadata, capture_datetime=fallback_datetime)

    def _build_storage_basename(self, metadata: MediaMetadata, camera_alias: str, source_path: Path) -> str:
        if self.settings.classification.rename_original_files and metadata.capture_datetime is not None:
            return build_original_basename(
                capture_datetime=metadata.capture_datetime,
                camera_alias=camera_alias,
                source_stem=source_path.stem,
                naming_settings=self.settings.naming,
            )

        alias_token = sanitize_path_token(camera_alias, maximum_length=24)
        source_token = sanitize_path_token(source_path.stem, self.settings.naming.maximum_stem_length)
        return f"unknown-date_{alias_token}_{source_token}"

    def _quarantine(
        self,
        source_path: Path,
        metadata: MediaMetadata,
        camera_alias: str,
        matched_on: str,
        reason: str,
    ) -> ClassificationResult:
        quarantine_date = (
            metadata.capture_datetime.strftime("%Y-%m-%d")
            if metadata.capture_datetime
            else datetime.now(tz=self.settings.classification.timezone).strftime("%Y-%m-%d")
        )
        reason_token = sanitize_path_token(reason, maximum_length=24).lower()
        quarantine_dir = self.settings.paths.quarantine_root / quarantine_date / reason_token
        timestamp = datetime.now(tz=self.settings.classification.timezone).strftime("%Y%m%d_%H%M%S")
        basename = f"{timestamp}_{reason_token}_{sanitize_path_token(source_path.stem, self.settings.naming.maximum_stem_length)}"
        destination_path = allocate_destination_path(
            destination_dir=quarantine_dir,
            basename=basename,
            suffix=source_path.suffix,
            duplicate_suffix_template=self.settings.naming.duplicate_suffix_template,
        )
        final_path = safe_move_file(source_path, destination_path)

        result = ClassificationResult(
            status="quarantined",
            source_path=source_path,
            destination_path=final_path,
            camera_alias=camera_alias,
            media_kind="unknown",
            camera_model=metadata.camera_model,
            camera_serial=metadata.camera_serial,
            capture_datetime=metadata.capture_datetime,
            matched_on=matched_on,
            reason=reason_token,
        )
        self.manifest.write(result)
        self.logger.warning("Quarantined %s -> %s (%s)", source_path.name, final_path, reason_token)
        return result


def _empty_metadata(source_path: Path) -> MediaMetadata:
    return MediaMetadata(
        source_path=source_path,
        capture_datetime=None,
        camera_model=None,
        camera_serial=None,
        raw_tags={},
    )
