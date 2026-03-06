from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nas_streamliner.config import NamingSettings
from nas_streamliner.naming import allocate_destination_path, build_original_basename, sanitize_path_token


class NamingTests(unittest.TestCase):
    def test_sanitize_path_token_replaces_invalid_characters(self) -> None:
        result = sanitize_path_token('  clip:01 / final?  ', maximum_length=32)
        self.assertEqual(result, "clip_01_final")

    def test_build_original_basename_uses_standard_template(self) -> None:
        naming_settings = NamingSettings(
            original_basename_template="{capture_date_compact}_{capture_time_compact}_{camera_alias}_{source_stem}",
            duplicate_suffix_template="__v{index:02d}",
            maximum_stem_length=32,
        )
        result = build_original_basename(
            capture_datetime=datetime(2026, 3, 6, 18, 45, 12),
            camera_alias="A-CAM",
            source_stem="FX3 Clip 001",
            naming_settings=naming_settings,
        )
        self.assertEqual(result, "20260306_184512_A-CAM_FX3_Clip_001")

    def test_allocate_destination_path_appends_version_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            (base_dir / "20260306_184512_A-CAM_clip.mp4").touch()
            result = allocate_destination_path(
                destination_dir=base_dir,
                basename="20260306_184512_A-CAM_clip",
                suffix=".mp4",
                duplicate_suffix_template="__v{index:02d}",
            )
            self.assertEqual(result.name, "20260306_184512_A-CAM_clip__v02.mp4")


if __name__ == "__main__":
    unittest.main()

