from __future__ import annotations

import shutil
from pathlib import Path


def safe_move_file(source_path: str | Path, destination_path: str | Path) -> Path:
    source = Path(source_path).resolve()
    destination = Path(destination_path).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    if source.anchor.casefold() == destination.anchor.casefold():
        source.replace(destination)
        return destination

    temporary_destination = destination.with_name(f"{destination.name}.part")
    if temporary_destination.exists():
        temporary_destination.unlink()

    try:
        shutil.copy2(source, temporary_destination)
        if source.stat().st_size != temporary_destination.stat().st_size:
            raise IOError("copied size does not match source size")
        temporary_destination.replace(destination)
        source.unlink()
    except Exception:
        if temporary_destination.exists():
            temporary_destination.unlink()
        raise

    return destination

