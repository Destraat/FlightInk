from flightink.routes import RouteResolver


def test_opensky_window_is_clamped_to_two_utc_days() -> None:
    now = 1_752_899_000
    begin = RouteResolver._clamp_to_two_utc_days(now - (36 * 3600), now)

    assert begin == ((now - (now % 86400)) - 86400)
