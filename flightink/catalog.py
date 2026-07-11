from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


@lru_cache(maxsize=1)
def airline_catalog() -> dict[str, dict[str, Any]]:
    return _load_json("airlines.json")


@lru_cache(maxsize=1)
def aircraft_catalog() -> dict[str, dict[str, Any]]:
    return _load_json("aircraft_types.json")


def airline_livery(icao_code: str | None) -> dict[str, Any]:
    catalog = airline_catalog()
    code = (icao_code or "DEFAULT").strip().upper()
    return catalog.get(code, catalog["DEFAULT"])


def aircraft_definition(type_code: str | None) -> dict[str, Any]:
    catalog = aircraft_catalog()
    code = (type_code or "DEFAULT").strip().upper()
    return catalog.get(code, {**catalog["DEFAULT"], "name": code or catalog["DEFAULT"]["name"]})


def _load_json(filename: str) -> dict[str, dict[str, Any]]:
    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict) or "DEFAULT" not in payload:
        raise ValueError(f"Ongeldige catalogus: {path}")
    return payload
