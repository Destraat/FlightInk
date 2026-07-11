from flightink.catalog import aircraft_definition, airline_catalog, airline_livery


def test_known_airline_livery() -> None:
    klm = airline_livery("KLM")
    assert klm["name"] == "KLM Royal Dutch Airlines"
    assert klm["country"] == "NL"
    assert 0 <= klm["body_gray"] <= 255


def test_unknown_airline_uses_default() -> None:
    assert airline_livery("ZZZ")["name"] == "Unknown operator"


def test_known_aircraft_type() -> None:
    aircraft = aircraft_definition("B738")
    assert aircraft["name"] == "Boeing 737-800"
    assert aircraft["engines"] == 2


def test_catalog_has_common_european_airlines() -> None:
    catalog = airline_catalog()
    for code in ["KLM", "TRA", "RYR", "EZY", "DLH", "BAW", "AFR", "SAS", "WZZ"]:
        assert code in catalog
