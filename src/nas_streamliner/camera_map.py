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
            serial_matches = self._find_matching_aliases(
                normalized_lookup_value=normalized_serial,
                rule_values_getter=lambda rule: rule.serials,
            )
            if len(serial_matches) == 1:
                return serial_matches[0], "serial"
            if len(serial_matches) > 1:
                return None, "serial_ambiguous"

        normalized_model = _normalize_lookup_value(model)
        if normalized_model:
            model_matches = self._find_matching_aliases(
                normalized_lookup_value=normalized_model,
                rule_values_getter=lambda rule: rule.models,
            )
            if len(model_matches) == 1:
                return model_matches[0], "model"
            if len(model_matches) > 1:
                # Multiple bodies can share one model (for example several FX3 units).
                # In that case we avoid a wrong body assignment and continue to filename hints.
                model = None

        if source_stem:
            for rule in self._rules:
                for hint in rule.filename_hints:
                    if re.search(hint, source_stem):
                        return rule.alias, "filename_hint"

        if model is None and normalized_model:
            return None, "model_ambiguous"
        return None, "default"

    def _find_matching_aliases(
        self,
        normalized_lookup_value: str,
        rule_values_getter,
    ) -> list[str]:
        matches: list[str] = []
        for rule in self._rules:
            normalized_values = {_normalize_lookup_value(item) for item in rule_values_getter(rule)}
            if normalized_lookup_value in normalized_values:
                matches.append(rule.alias)
        return matches


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
