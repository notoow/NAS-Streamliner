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
from nas_streamliner.services.watcher import InboundWatcher


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch the inbound directory and classify stable files.")
    parser.add_argument("--config", default="config/settings.yaml", help="Path to the settings YAML file.")
    parser.add_argument("--once", action="store_true", help="Run a single scan cycle and exit.")
    args = parser.parse_args()

    settings = load_settings(args.config)
    logger = configure_logging(settings.logging, settings.paths)
    watcher = InboundWatcher(settings=settings, logger=logger)

    try:
        if args.once:
            processed = watcher.run_once()
            logger.info("Single scan completed. ready files processed=%s", processed)
        else:
            watcher.run_forever()
    except KeyboardInterrupt:
        logger.info("Watcher interrupted by user.")
    finally:
        watcher.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

