from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Observation:
    path: str
    size: int
    mtime: float
    first_seen: float
    last_seen: float
    stable_since: float | None
    status: str
    notes: str | None
    destination_path: str | None


class StateStore:
    def __init__(self, database_path: str | Path) -> None:
        self._database_path = Path(database_path).resolve()
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(self._database_path))
        self._connection.row_factory = sqlite3.Row
        self._ensure_schema()

    def close(self) -> None:
        self._connection.close()

    def record_scan(self, path: str | Path, size: int, mtime: float, seen_at: float) -> None:
        path_string = str(Path(path).resolve())
        existing = self.get(path_string)
        if existing is None:
            self._connection.execute(
                """
                INSERT INTO observations (
                    path, size, mtime, first_seen, last_seen, stable_since, status, notes, destination_path
                ) VALUES (?, ?, ?, ?, ?, NULL, 'pending', NULL, NULL)
                """,
                (path_string, size, mtime, seen_at, seen_at),
            )
            self._connection.commit()
            return

        if existing.status in {"completed", "quarantined", "failed"}:
            self._connection.execute(
                """
                UPDATE observations
                SET size = ?, mtime = ?, first_seen = ?, last_seen = ?, stable_since = NULL,
                    status = 'pending', notes = NULL, destination_path = NULL
                WHERE path = ?
                """,
                (size, mtime, seen_at, seen_at, path_string),
            )
            self._connection.commit()
            return

        changed = existing.size != size or abs(existing.mtime - mtime) > 0.001
        stable_since = None if changed else existing.stable_since or seen_at
        status = "pending" if existing.status == "processing" else existing.status

        self._connection.execute(
            """
            UPDATE observations
            SET size = ?, mtime = ?, last_seen = ?, stable_since = ?, status = ?, notes = NULL
            WHERE path = ?
            """,
            (size, mtime, seen_at, stable_since, status, path_string),
        )
        self._connection.commit()

    def get(self, path: str | Path) -> Observation | None:
        row = self._connection.execute(
            "SELECT * FROM observations WHERE path = ?",
            (str(Path(path).resolve()),),
        ).fetchone()
        return _row_to_observation(row) if row else None

    def iter_ready(self, now: float, stable_window_seconds: int, minimum_file_age_seconds: int) -> list[Observation]:
        rows = self._connection.execute(
            """
            SELECT * FROM observations
            WHERE status = 'pending'
              AND stable_since IS NOT NULL
              AND (? - stable_since) >= ?
              AND (? - mtime) >= ?
            ORDER BY stable_since ASC
            """,
            (now, stable_window_seconds, now, minimum_file_age_seconds),
        ).fetchall()
        return [_row_to_observation(row) for row in rows]

    def mark_processing(self, path: str | Path) -> None:
        self._set_status(path, "processing")

    def mark_completed(self, path: str | Path, destination_path: str | Path) -> None:
        self._set_status(path, "completed", destination_path=destination_path)

    def mark_quarantined(self, path: str | Path, destination_path: str | Path, notes: str | None) -> None:
        self._set_status(path, "quarantined", notes=notes, destination_path=destination_path)

    def mark_failed(self, path: str | Path, notes: str) -> None:
        self._set_status(path, "failed", notes=notes)

    def _set_status(
        self,
        path: str | Path,
        status: str,
        notes: str | None = None,
        destination_path: str | Path | None = None,
    ) -> None:
        path_string = str(Path(path).resolve())
        destination_string = str(Path(destination_path).resolve()) if destination_path else None
        self._connection.execute(
            """
            UPDATE observations
            SET status = ?, notes = ?, destination_path = ?
            WHERE path = ?
            """,
            (status, notes, destination_string, path_string),
        )
        self._connection.commit()

    def _ensure_schema(self) -> None:
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS observations (
                path TEXT PRIMARY KEY,
                size INTEGER NOT NULL,
                mtime REAL NOT NULL,
                first_seen REAL NOT NULL,
                last_seen REAL NOT NULL,
                stable_since REAL,
                status TEXT NOT NULL,
                notes TEXT,
                destination_path TEXT
            )
            """
        )
        self._connection.commit()


def _row_to_observation(row: sqlite3.Row) -> Observation:
    return Observation(
        path=row["path"],
        size=row["size"],
        mtime=row["mtime"],
        first_seen=row["first_seen"],
        last_seen=row["last_seen"],
        stable_since=row["stable_since"],
        status=row["status"],
        notes=row["notes"],
        destination_path=row["destination_path"],
    )
