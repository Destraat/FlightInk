from __future__ import annotations

from dataclasses import dataclass

from .catalog import aircraft_definition


@dataclass(frozen=True, slots=True)
class Aircraft:
    hex: str
    callsign: str
    registration: str
    type_code: str
    latitude: float
    longitude: float
    altitude_ft: float | None
    speed_knots: float | None
    track: float | None
    distance_km: float

    @property
    def airline_code(self) -> str:
        value = self.callsign.strip().upper()
        return value[:3] if len(value) >= 3 and value[:3].isalpha() else "DEFAULT"

    @property
    def display_name(self) -> str:
        return str(aircraft_definition(self.type_code)["name"])

    @property
    def family(self) -> str:
        return str(aircraft_definition(self.type_code).get("family", "narrowbody"))

    @property
    def engine_count(self) -> int:
        return int(aircraft_definition(self.type_code).get("engines", 2))

    @property
    def speed_kmh(self) -> float | None:
        return None if self.speed_knots is None else self.speed_knots * 1.852

    @property
    def altitude_m(self) -> float | None:
        return None if self.altitude_ft is None else self.altitude_ft * 0.3048


@dataclass(frozen=True, slots=True)
class Weather:
    temperature_c: float | None
    cloud_cover: int | None
    weather_code: int | None
    wind_speed_kmh: float | None = None
    wind_direction: float | None = None


def aircraft_name(type_code: str) -> str:
    return str(aircraft_definition(type_code)["name"])
