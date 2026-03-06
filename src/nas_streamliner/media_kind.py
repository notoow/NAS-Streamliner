from __future__ import annotations

import re


def detect_media_kind(source_stem: str, proxy_filename_patterns: tuple[str, ...]) -> str:
    for pattern in proxy_filename_patterns:
        if re.search(pattern, source_stem):
            return "proxy"
    return "original"
