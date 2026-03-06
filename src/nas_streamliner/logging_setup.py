from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .config import LoggingSettings, PathSettings


def configure_logging(logging_settings: LoggingSettings, path_settings: PathSettings) -> logging.Logger:
    logger = logging.getLogger("nas_streamliner")
    logger.setLevel(logging_settings.level.upper())
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    path_settings.log_root.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        path_settings.log_root / logging_settings.file_name,
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger
