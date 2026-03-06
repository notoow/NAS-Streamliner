from __future__ import annotations

import logging
import time
from pathlib import Path

from ..config import Settings
from ..state_store import Observation, StateStore
from .classifier import MediaClassifier


class InboundWatcher:
    def __init__(self, settings: Settings, logger: logging.Logger | None = None) -> None:
        self.settings = settings
        self.logger = logger or logging.getLogger("nas_streamliner")
        self.state_store = StateStore(settings.paths.state_db)
        self.classifier = MediaClassifier(settings=settings, logger=self.logger)

    def run_forever(self) -> None:
        self.logger.info("Watching inbound directory: %s", self.settings.paths.inbound_root)
        while True:
            self.run_once()
            time.sleep(self.settings.watcher.scan_interval_seconds)

    def run_once(self) -> int:
        now = time.time()
        for file_path in self._iter_candidate_files():
            try:
                stats = file_path.stat()
            except OSError as exc:
                self.logger.warning("Skipping unreadable file %s: %s", file_path, exc)
                continue
            self.state_store.record_scan(file_path, stats.st_size, stats.st_mtime, now)

        ready_items = self.state_store.iter_ready(
            now=now,
            stable_window_seconds=self.settings.watcher.stable_window_seconds,
            minimum_file_age_seconds=self.settings.watcher.minimum_file_age_seconds,
        )
        for observation in ready_items:
            self._process_observation(observation)
        return len(ready_items)

    def close(self) -> None:
        self.state_store.close()

    def _iter_candidate_files(self) -> list[Path]:
        accepted_extensions = set(self.settings.watcher.accepted_extensions)
        candidates: list[Path] = []
        for path in sorted(self.settings.paths.inbound_root.iterdir()):
            if not path.is_file():
                continue
            if self.settings.watcher.ignore_hidden_files and path.name.startswith("."):
                continue
            if accepted_extensions and path.suffix.lower() not in accepted_extensions:
                continue
            candidates.append(path)
        return candidates

    def _process_observation(self, observation: Observation) -> None:
        source_path = Path(observation.path)
        if not source_path.exists():
            self.state_store.mark_failed(source_path, "missing-before-processing")
            self.logger.warning("Observed file disappeared before processing: %s", source_path)
            return

        self.state_store.mark_processing(source_path)
        try:
            result = self.classifier.classify(source_path)
        except Exception as exc:
            self.state_store.mark_failed(source_path, str(exc))
            self.logger.exception("Failed to classify %s", source_path)
            return

        if result.status == "quarantined":
            self.state_store.mark_quarantined(source_path, result.destination_path, result.reason)
        else:
            self.state_store.mark_completed(source_path, result.destination_path)

