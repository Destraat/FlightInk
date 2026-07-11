# FlightInk

Een gratis, lokaal draaiend e-ink vluchtscherm voor vliegtuigen die over het huis vliegen. FlightInk haalt ADS-B-posities op, kiest het dichtstbijzijnde toestel en rendert een rustige zwart-witweergave met vliegtuigtype, maatschappij, hoogte, snelheid, afstand en route-informatie wanneer die beschikbaar is.

![FlightInk preview](assets/flightink-preview.svg)

## Doel

- Geen betaalde vlucht-API nodig.
- Geschikt voor Raspberry Pi en een 800×480 Waveshare e-paper display.
- Groot zijaanzicht van het vliegtuig in het middenvlak.
- Weergave van actuele weersfeer met eenvoudige wolkenpatronen.
- Eén bestemmingsvlag en een herkenbaar gebouw van de bestemming.
- Lokale fallback wanneer route-, toestel- of maatschappijgegevens ontbreken.

## Snel starten

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python flightink.py --once
```

Op Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python flightink.py --once
```

Pas in `.env` je eigen coördinaten aan. Het resultaat wordt standaard geschreven naar `output/flightink.png`.

## Datastroom

```text
Airplanes.live ADS-B endpoint
        ↓
Toestellen binnen ingestelde straal
        ↓
Dichtstbijzijnde vliegende toestel
        ↓
Type- en maatschappijmapping
        ↓
Routecache / gratis routebron / fallback onbekend
        ↓
Pillow-renderer naar 800×480 zwart-wit
        ↓
PNG-preview of Waveshare e-paper driver
```

## Projectstructuur

```text
FlightInk/
├── assets/
│   └── flightink-preview.svg
├── data/
│   ├── aircraft_types.json
│   ├── airlines.json
│   └── destinations.json
├── output/
├── tests/
├── .env.example
├── agent.md
├── flightink.py
├── requirements.txt
└── README.md
```

## E-ink hardware

De code rendert eerst naar een normale monochrome PNG. Daardoor kun je alles ontwikkelen zonder aangesloten scherm. De hardwarelaag wordt daarna gekoppeld aan de Waveshare-driver. Houd het schermtype configureerbaar, omdat de Python-module per Waveshare-revisie verschilt.

## Gratis gegevens en beperkingen

ADS-B geeft positie, koers, hoogte, snelheid, callsign, registratie en typecode wanneer die velden worden uitgezonden. Herkomst en bestemming zitten niet betrouwbaar in ADS-B. FlightInk gebruikt daarom een lokale routecache en toont `Route onbekend` wanneer geen gratis match beschikbaar is.

## Ontwikkelen

```bash
pytest
python flightink.py --demo
python flightink.py --once
```

De branch `feature/flightink-mvp` bevat de eerste werkende versie. Wijzigingen worden via een pull request naar `main` gebracht.
