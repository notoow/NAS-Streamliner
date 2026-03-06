from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nas_streamliner.media_kind import detect_media_kind


class MediaKindTests(unittest.TestCase):
    def test_detects_proxy_keyword(self) -> None:
        result = detect_media_kind(
            source_stem="DJI_20260131084233_0019_D-029_Proxy",
            proxy_filename_patterns=(r"(?i)(?:^|[_ -])proxy(?:$|[_ -])", r"(?i)s03$"),
        )
        self.assertEqual(result, "proxy")

    def test_detects_sony_s03_suffix(self) -> None:
        result = detect_media_kind(
            source_stem="C0001S03",
            proxy_filename_patterns=(r"(?i)(?:^|[_ -])proxy(?:$|[_ -])", r"(?i)s03$"),
        )
        self.assertEqual(result, "proxy")

    def test_defaults_to_original(self) -> None:
        result = detect_media_kind(
            source_stem="C0001",
            proxy_filename_patterns=(r"(?i)(?:^|[_ -])proxy(?:$|[_ -])", r"(?i)s03$"),
        )
        self.assertEqual(result, "original")


if __name__ == "__main__":
    unittest.main()
