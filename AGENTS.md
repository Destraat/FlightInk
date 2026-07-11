# AGENTS.md

## Doel

Bouw en onderhoud FlightInk: een gratis, lokaal draaiende e-ink flight tracker voor vliegtuigen die over het huis vliegen.

## Functionele eisen

1. Gebruik uitsluitend gratis databronnen.
2. Haal live vliegtuigen op binnen een configureerbare straal rond `HOME_LAT` en `HOME_LON`.
3. Selecteer standaard het dichtstbijzijnde toestel met geldige positie.
4. Toon minimaal callsign, registratie, vliegtuigtype, hoogte, snelheid en afstand.
5. Render een groot, clean zijaanzicht van het toestel in het middenvlak.
6. Bepaal eenvoudige livery op basis van airline/callsign en gebruik een neutrale fallback.
7. Spiegel het toestel horizontaal op basis van de koers; roteer het niet schuin.
8. Toon actuele temperatuur en bewolking via een gratis weerbron.
9. Render primair naar een 800×480 monochrome PNG.
10. Hardware-integratie moet via een aparte adapter verlopen.

## Databeperkingen

- ADS-B bevat niet betrouwbaar vertrek- en bestemmingsluchthaven.
- Toon nooit verzonnen route-informatie.
- Gebruik later een lokale routecache of een aantoonbaar vrije bron.
- Toon `Route onbekend` wanneer geen betrouwbare match bestaat.
- Ontbrekende registratie, typecode of callsign moeten nette fallbacks krijgen.

## Architectuur

- `flightink/api.py`: externe gratis databronnen en parsing.
- `flightink/config.py`: configuratie uit environment variables.
- `flightink/models.py`: dataclasses en typebenamingen.
- `flightink/renderer.py`: hardware-onafhankelijke Pillow-renderer.
- `main.py`: polling-loop en foutafhandeling.
- Voeg hardwaredrivers toe onder `flightink/displays/`.
- Voeg routecachelogica toe onder `flightink/routes/`.

## Ontwikkelregels

- Python 3.11 of hoger.
- Voeg type hints toe aan publieke functies.
- Gebruik time-outs voor iedere HTTP-call.
- Laat een tijdelijke API-storing de applicatie niet beëindigen.
- Bewaar geen exacte thuiscoördinaten in Git.
- Commit geen `.env`, cachebestanden of gegenereerde output.
- Houd rendering deterministisch en testbaar.
- Voeg tests toe voor afstandsberekening, selectie, callsignmapping en fallbacks.
- Introduceer geen betaalde API als verplichte dependency.

## Eerstvolgende taken

1. Voeg een `--once` en `--demo` CLI-modus toe.
2. Schrijf unit tests voor `haversine_km` en model-fallbacks.
3. Voeg een lokale SQLite-routecache toe.
4. Voeg configurabele airline-liveries toe vanuit JSON.
5. Maak een Waveshare 7.5-inch display-adapter.
6. Voeg volledige refresh na een configureerbaar aantal partial refreshes toe.
7. Voeg caching toe zodat hetzelfde toestel niet onnodig opnieuw wordt gerenderd.

## Acceptatiecriteria

Een wijziging is gereed wanneer:

- `pytest` slaagt;
- `python main.py` met geldige environment variables een PNG maakt;
- ontbrekende API-data niet tot een crash leidt;
- er geen geheimen of thuiscoördinaten zijn vastgelegd;
- README en configuratievoorbeelden actueel zijn.
