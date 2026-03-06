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
                        "  - alias: B-CAM",
                        "    serials: [PHONE-001]",
                        "    models: [iPhone 15 Pro]",
                    ]
                ),
                encoding="utf-8",
            )
            resolver = load_camera_resolver(camera_map_path)
            alias, matched_on = resolver.resolve(serial="FX3-001", model="ILME-FX3")
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
                    ]
                ),
                encoding="utf-8",
            )
            resolver = load_camera_resolver(camera_map_path)
            alias, matched_on = resolver.resolve(serial=None, model="ILME FX3")
            self.assertEqual(alias, "A-CAM")
            self.assertEqual(matched_on, "model")


if __name__ == "__main__":
    unittest.main()
