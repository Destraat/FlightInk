from flightink.api import fetch_aircraft, fetch_local_aircraft
from flightink.config import Settings


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(self.payload)


def settings(**changes):
    values = {
        "home_lat": 52.0,
        "home_lon": 5.0,
        "minimum_altitude_ft": 500,
        "maximum_distance_km": 20,
        "aircraft_source": "local",
        "local_adsb_url": "http://127.0.0.1:8080/data/aircraft.json",
    }
    values.update(changes)
    return Settings(**values)


def test_parses_dump1090_aircraft_json():
    session = FakeSession({"aircraft": [{
        "hex": "484abc", "flight": "KLM123 ", "lat": 52.01, "lon": 5.01,
        "alt_baro": 12000, "gs": 410, "track": 95, "r": "PH-ABC", "t": "B738"
    }]})
    aircraft = fetch_local_aircraft(settings(), session)
    assert len(aircraft) == 1
    assert aircraft[0].callsign == "KLM123"
    assert aircraft[0].registration == "PH-ABC"
    assert aircraft[0].type_code == "B738"


def test_hybrid_uses_local_feed_when_available():
    session = FakeSession({"aircraft": [{
        "hex": "484abc", "flight": "TRA456", "lat": 52.01, "lon": 5.01,
        "alt_geom": 9000, "gs": 300, "track": 180
    }]})
    aircraft = fetch_aircraft(settings(aircraft_source="hybrid"), session)
    assert len(aircraft) == 1
    assert len(session.calls) == 1


def test_filters_ground_aircraft():
    session = FakeSession({"aircraft": [{
        "hex": "ground1", "flight": "TEST", "lat": 52.01, "lon": 5.01,
        "alt_baro": "ground", "gs": 0, "track": 0
    }]})
    assert fetch_local_aircraft(settings(), session) == []
