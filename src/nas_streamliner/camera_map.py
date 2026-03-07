from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class CameraRule:
    alias: str
    serials: tuple[str, ...]
    models: tuple[str, ...]
    filename_hints: tuple[str, ...]


class CameraResolver:
    def __init__(self, rules: list[CameraRule]) -> None:
        self._rules = rules

    def resolve(self, serial: str | None, model: str | None, source_stem: str | None = None) -> tuple[str | None, str]:
        normalized_serial = _normalize_lookup_value(serial)
        if normalized_serial:
            for rule in self._rules:
                if normalized_serial in {_normalize_lookup_value(item) for item in rule.serials}:
                    return rule.alias, "serial"

        normalized_model = _normalize_lookup_value(model)
        if normalized_model:
            for rule in self._rules:
                if normalized_model in {_normalize_lookup_value(item) for item in rule.models}:
                    return rule.alias, "model"

        if source_stem:
            for rule in self._rules:
                for hint in rule.filename_hints:
                    if re.search(hint, source_stem):
                        return rule.alias, "filename_hint"

        return None, "default"


def load_camera_resolver(camera_map_path: str | Path) -> CameraResolver:
    resolved_path = Path(camera_map_path).resolve()
    with resolved_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    rules: list[CameraRule] = []
    for item in raw.get("cameras", []):
        rules.append(
            CameraRule(
                alias=str(item["alias"]),
                serials=tuple(str(value) for value in item.get("serials", [])),
                models=tuple(str(value) for value in item.get("models", [])),
                filename_hints=tuple(str(value) for value in item.get("filename_hints", [])),
            )
        )
    return CameraResolver(rules)


def _normalize_lookup_value(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^0-9A-Za-z]+", "", value.casefold())
