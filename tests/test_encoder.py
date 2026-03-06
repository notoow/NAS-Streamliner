from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nas_streamliner.services.encoder import build_proxy_output_path


class EncoderPathTests(unittest.TestCase):
    def test_build_proxy_output_path_uses_sibling_proxy_for_originals(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "2026-02-27" / "A-CAM" / "Original" / "clip.mp4"
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.touch()

            result = build_proxy_output_path(
                source_path=source_path,
                proxy_subdir_name="Proxy",
                proxy_suffix="__proxy_720p_cfr",
                output_extension=".mp4",
            )

            self.assertEqual(
                result,
                source_path.parent.parent / "Proxy" / "clip__proxy_720p_cfr.mp4",
            )

    def test_build_proxy_output_path_uses_child_proxy_folder_outside_original(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "samples" / "clip.mov"
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.touch()

            result = build_proxy_output_path(
                source_path=source_path,
                proxy_subdir_name="Proxy",
                proxy_suffix="__proxy_720p_cfr",
                output_extension=".mp4",
            )

            self.assertEqual(
                result,
                source_path.parent / "Proxy" / "clip__proxy_720p_cfr.mp4",
            )


if __name__ == "__main__":
    unittest.main()
