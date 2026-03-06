from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nas_streamliner.config import load_settings
from nas_streamliner.preflight import run_preflight


class ConfigTests(unittest.TestCase):
    def test_load_settings_expands_environment_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            settings_path = temp_root / "settings.yaml"
            camera_map_path = temp_root / "cam_map.yaml"
            camera_map_path.write_text("cameras: []\n", encoding="utf-8")
            settings_path.write_text(
                "\n".join(
                    [
                        "project_name: NAS-Streamliner",
                        "paths:",
                        "  project_root: .",
                        "  inbound_root: ${TEST_INBOUND_ROOT:-./inbound}",
                        "  storage_root: ${TEST_STORAGE_ROOT:-./storage}",
                        "  quarantine_root: ./quarantine",
                        "  log_root: ./logs",
                        "  state_db: ./state/nas_streamliner.db",
                        "  manifest_path: ./state/manifest.jsonl",
                        "  camera_map_path: ./cam_map.yaml",
                        "watcher:",
                        "  scan_interval_seconds: 5",
                        "  stable_window_seconds: 20",
                        "  minimum_file_age_seconds: 10",
                        "  accepted_extensions: [.mp4]",
                        "  ignore_hidden_files: true",
                        "ffprobe:",
                        "  binary: ffprobe",
                        "  timeout_seconds: 20",
                        "  metadata_date_keys: [creation_time]",
                        "  metadata_model_keys: [model]",
                        "  metadata_serial_keys: [serial_number]",
                        "classification:",
                        "  timezone: Asia/Seoul",
                        "  unknown_camera_alias: Z-CAM-UNKNOWN",
                        "  unknown_date_folder: 1970-01-01",
                        "  fallback_to_file_modified_time: true",
                        "  quarantine_on_missing_date: false",
                        "  quarantine_on_missing_camera: false",
                        "  rename_original_files: true",
                        "  proxy_filename_patterns: ['(?i)(?:^|[_ -])proxy(?:$|[_ -])', '(?i)s03$']",
                        "naming:",
                        "  original_basename_template: '{capture_date_compact}_{capture_time_compact}_{camera_alias}_{source_stem}'",
                        "  duplicate_suffix_template: '__v{index:02d}'",
                        "  maximum_stem_length: 48",
                        "logging:",
                        "  level: INFO",
                        "  file_name: nas_streamliner.log",
                        "encoder:",
                        "  enabled: true",
                        "  ffmpeg_binary: ffmpeg",
                        "  timeout_seconds: 0",
                        "  auto_encode_after_classification: true",
                        "  proxy_subdir_name: Proxy",
                        "  proxy_suffix: __proxy_720p_cfr",
                        "  output_extension: .mp4",
                        "  skip_if_source_not_newer: true",
                        "  video_codec: libx264",
                        "  video_preset: veryfast",
                        "  video_crf: 23",
                        "  pixel_format: yuv420p",
                        "  max_width: 1280",
                        "  max_height: 720",
                        "  audio_codec: aac",
                        "  audio_bitrate: 160k",
                        "  movflags_faststart: true",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"TEST_STORAGE_ROOT": str(temp_root / "nas-storage")}, clear=False):
                settings = load_settings(settings_path)

            self.assertEqual(settings.paths.storage_root, (temp_root / "nas-storage").resolve())
            self.assertEqual(settings.paths.inbound_root, (temp_root / "inbound").resolve())

    def test_preflight_creates_missing_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            config_dir = temp_root / "config"
            config_dir.mkdir()
            camera_map_path = config_dir / "cam_map.yaml"
            camera_map_path.write_text("cameras: []\n", encoding="utf-8")
            settings_path = config_dir / "settings.yaml"
            settings_path.write_text(
                "\n".join(
                    [
                        "project_name: NAS-Streamliner",
                        "paths:",
                        "  project_root: ..",
                        "  inbound_root: ../runtime/inbound",
                        "  storage_root: ../runtime/storage",
                        "  quarantine_root: ../runtime/quarantine",
                        "  log_root: ../runtime/logs",
                        "  state_db: ../runtime/state/nas_streamliner.db",
                        "  manifest_path: ../runtime/state/manifest.jsonl",
                        "  camera_map_path: ./cam_map.yaml",
                        "watcher:",
                        "  scan_interval_seconds: 5",
                        "  stable_window_seconds: 20",
                        "  minimum_file_age_seconds: 10",
                        "  accepted_extensions: [.mp4]",
                        "  ignore_hidden_files: true",
                        "ffprobe:",
                        "  binary: ffprobe",
                        "  timeout_seconds: 20",
                        "  metadata_date_keys: [creation_time]",
                        "  metadata_model_keys: [model]",
                        "  metadata_serial_keys: [serial_number]",
                        "classification:",
                        "  timezone: Asia/Seoul",
                        "  unknown_camera_alias: Z-CAM-UNKNOWN",
                        "  unknown_date_folder: 1970-01-01",
                        "  fallback_to_file_modified_time: true",
                        "  quarantine_on_missing_date: false",
                        "  quarantine_on_missing_camera: false",
                        "  rename_original_files: true",
                        "  proxy_filename_patterns: ['(?i)(?:^|[_ -])proxy(?:$|[_ -])', '(?i)s03$']",
                        "naming:",
                        "  original_basename_template: '{capture_date_compact}_{capture_time_compact}_{camera_alias}_{source_stem}'",
                        "  duplicate_suffix_template: '__v{index:02d}'",
                        "  maximum_stem_length: 48",
                        "logging:",
                        "  level: INFO",
                        "  file_name: nas_streamliner.log",
                        "encoder:",
                        "  enabled: true",
                        "  ffmpeg_binary: ffmpeg",
                        "  timeout_seconds: 0",
                        "  auto_encode_after_classification: true",
                        "  proxy_subdir_name: Proxy",
                        "  proxy_suffix: __proxy_720p_cfr",
                        "  output_extension: .mp4",
                        "  skip_if_source_not_newer: true",
                        "  video_codec: libx264",
                        "  video_preset: veryfast",
                        "  video_crf: 23",
                        "  pixel_format: yuv420p",
                        "  max_width: 1280",
                        "  max_height: 720",
                        "  audio_codec: aac",
                        "  audio_bitrate: 160k",
                        "  movflags_faststart: true",
                        "preflight:",
                        "  enabled: true",
                        "  create_missing_directories: true",
                        "  verify_camera_map_exists: true",
                        "  verify_inbound_exists: true",
                        "  verify_storage_writable: true",
                        "  verify_quarantine_writable: true",
                        "  verify_log_root_writable: true",
                        "  verify_state_root_writable: true",
                        "  write_probe_file_name: .probe",
                    ]
                ),
                encoding="utf-8",
            )

            settings = load_settings(settings_path)
            run_preflight(settings)

            self.assertTrue(settings.paths.inbound_root.is_dir())
            self.assertTrue(settings.paths.storage_root.is_dir())
            self.assertTrue(settings.paths.quarantine_root.is_dir())
            self.assertTrue(settings.paths.log_root.is_dir())
            self.assertTrue(settings.paths.state_db.parent.is_dir())


if __name__ == "__main__":
    unittest.main()
