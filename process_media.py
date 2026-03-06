from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nas_streamliner.config import load_settings
from nas_streamliner.logging_setup import configure_logging
from nas_streamliner.preflight import run_preflight
from nas_streamliner.services.classifier import MediaClassifier
from nas_streamliner.services.encoder import ProxyEncoder


def main() -> int:
    parser = argparse.ArgumentParser(description="Run classify + proxy encode for one or more media files.")
    parser.add_argument("paths", nargs="*", help="Source files to process.")
    parser.add_argument("--config", default="config/settings.yaml", help="Path to the settings YAML file.")
    parser.add_argument("--skip-encode", action="store_true", help="Only classify; do not generate a proxy.")
    parser.add_argument("--validate-only", action="store_true", help="Validate NAS paths and configuration, then exit.")
    args = parser.parse_args()

    settings = load_settings(args.config)
    logger = configure_logging(settings.logging, settings.paths)
    run_preflight(settings, logger)

    if args.validate_only:
        logger.info("Configuration validation completed successfully.")
        return 0

    if not args.paths:
        parser.error("At least one source path is required unless --validate-only is used.")

    classifier = MediaClassifier(settings=settings, logger=logger)
    encoder = ProxyEncoder(settings=settings, logger=logger)

    for raw_path in args.paths:
        classification_result = classifier.classify(raw_path)
        logger.info(
            "Classified: %s -> %s (%s, %s)",
            classification_result.source_path,
            classification_result.destination_path,
            classification_result.status,
            classification_result.media_kind,
        )
        if (
            classification_result.status != "stored"
            or classification_result.media_kind != "original"
            or args.skip_encode
            or not settings.encoder.enabled
        ):
            continue

        proxy_result = encoder.encode(classification_result.destination_path)
        logger.info(
            "Proxy: %s -> %s (%s)",
            proxy_result.source_path,
            proxy_result.destination_path,
            proxy_result.status,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
