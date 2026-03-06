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


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify one or more media files into the storage structure.")
    parser.add_argument("paths", nargs="*", help="Source media files to classify.")
    parser.add_argument("--config", default="config/settings.yaml", help="Path to the settings YAML file.")
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

    for raw_path in args.paths:
        result = classifier.classify(raw_path)
        logger.info("Result: %s -> %s (%s)", result.source_path, result.destination_path, result.status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
