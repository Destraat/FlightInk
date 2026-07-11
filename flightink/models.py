from __future__ import annotations

from dataclasses import dataclass


@dataclass
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
        return value[:3] if len(value) >= 3 and value[:3].isalpha() else "UNK"


@dataclass
class Weather:
    temperature_c: float | None
    cloud_cover: int | None
    weather_code: int | None


AIRCRAFT_NAMES = {
    "B738": "Boeing 737-800",
    "B38M": "Boeing 737 MAX 8",
    "A319": "Airbus A319",
    "A320": "Airbus A320",
    "A21N": "Airbus A321neo",
    "E190": "Embraer 190",
    "E195": "Embraer 195",
    "B77W": "Boeing 777-300ER",
    "B789": "Boeing 787-9",
}


def aircraft_name(type_code: str) -> str:
    return AIRCRAFT_NAMES.get(type_code.upper(), type_code or "Onbekend vliegtuigtype")
