from flightink.models import Aircraft
from flightink.prediction import predict_passage, selection_score


def aircraft(lat: float, lon: float, track: float, speed: float = 360) -> Aircraft:
    return Aircraft(
        hex="abc123",
        callsign="KLM123",
        registration="PH-ABC",
        type_code="B738",
        latitude=lat,
        longitude=lon,
        altitude_ft=10000,
        speed_knots=speed,
        track=track,
        distance_km=5.0,
    )


def test_eastbound_aircraft_approaches_home() -> None:
    item = aircraft(52.0, 4.9, 90)
    prediction = predict_passage(item, 52.0, 5.0)
    assert prediction.approaching is True
    assert prediction.seconds_until_closest is not None
    assert prediction.closest_distance_km < 0.2


def test_aircraft_flying_away_is_not_approaching() -> None:
    item = aircraft(52.0, 4.9, 270)
    prediction = predict_passage(item, 52.0, 5.0)
    assert prediction.approaching is False
    assert prediction.closest_distance_km > 0


def test_closer_predicted_passage_wins() -> None:
    direct = predict_passage(aircraft(52.0, 4.9, 90), 52.0, 5.0)
    offset = predict_passage(aircraft(52.05, 4.9, 90), 52.0, 5.0)
    assert selection_score(aircraft(52.0, 4.9, 90), direct) < selection_score(aircraft(52.05, 4.9, 90), offset)
