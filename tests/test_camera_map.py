from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nas_streamliner.camera_map import load_camera_resolver


class CameraMapTests(unittest.TestCase):
    def test_camera_resolver_prefers_serial_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            camera_map_path = Path(temp_dir) / "cam_map.yaml"
            camera_map_path.write_text(
                "\n".join(
                    [
                        "cameras:",
                        "  - alias: A-CAM",
                        "    serials: [FX3-001]",
                        "    models: [ILME-FX3]",
                        "    filename_hints: []",
                        "  - alias: B-CAM",
                        "    serials: [PHONE-001]",
                        "    models: [iPhone 15 Pro]",
                        "    filename_hints: []",
                    ]
                ),
                encoding="utf-8",
            )
            resolver = load_camera_resolver(camera_map_path)
            alias, matched_on = resolver.resolve(serial="FX3-001", model="ILME-FX3", source_stem="C0001")
            self.assertEqual(alias, "A-CAM")
            self.assertEqual(matched_on, "serial")

    def test_camera_resolver_falls_back_to_model(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            camera_map_path = Path(temp_dir) / "cam_map.yaml"
            camera_map_path.write_text(
                "\n".join(
                    [
                        "cameras:",
                        "  - alias: A-CAM",
                        "    serials: []",
                        "    models: [ILME-FX3]",
                        "    filename_hints: []",
                    ]
                ),
                encoding="utf-8",
            )
            resolver = load_camera_resolver(camera_map_path)
            alias, matched_on = resolver.resolve(serial=None, model="ILME FX3", source_stem="C0001")
            self.assertEqual(alias, "A-CAM")
            self.assertEqual(matched_on, "model")

    def test_camera_resolver_uses_filename_hint_when_metadata_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            camera_map_path = Path(temp_dir) / "cam_map.yaml"
            camera_map_path.write_text(
                "\n".join(
                    [
                        "cameras:",
                        "  - alias: DJI-001",
                        "    serials: []",
                        "    models: []",
                        "    filename_hints: ['(?i)^DJI_']",
                    ]
                ),
                encoding="utf-8",
            )
            resolver = load_camera_resolver(camera_map_path)
            alias, matched_on = resolver.resolve(
                serial=None,
                model=None,
                source_stem="DJI_20260131084233_0019_D-029_Proxy",
            )
            self.assertEqual(alias, "DJI-001")
            self.assertEqual(matched_on, "filename_hint")


if __name__ == "__main__":
    unittest.main()
