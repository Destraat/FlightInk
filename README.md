# FlightInk

![FlightInk preview](assets/flightink-preview.svg)

FlightInk toont automatisch het vliegtuig dat het dichtst bij je huis vliegt op een 800×480 e-inkscherm. De applicatie gebruikt gratis databronnen en lokale rendering.

## Wat werkt

- live ADS-B-posities via Airplanes.live;
- selectie van het dichtstbijzijnde toestel;
- callsign, registratie, type, hoogte, snelheid en afstand;
- een groot vliegtuig in zijaanzicht, volledig getekend met Python/Pillow;
- eenvoudige maatschappij-aankleding op basis van het callsign;
- spiegeling op basis van de vliegrichting;
- actuele temperatuur en bewolking via Open-Meteo;
- zwart-wit PNG-uitvoer voor e-ink naar `output/flightink.png`.

Herkomst en bestemming zitten niet betrouwbaar in gratis ADS-B-data. Hiervoor volgt later een lokale routecache met een duidelijke `Route onbekend`-fallback.

## Installeren

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Vul je eigen coördinaten in en start:

```bash
set -a
source .env
set +a
python main.py
```

Windows PowerShell:

```powershell
$env:HOME_LAT="52.0000"
$env:HOME_LON="6.0000"
$env:RADIUS_NM="10"
python main.py
```

## Structuur

```text
FlightInk/
├── assets/flightink-preview.svg
├── flightink/
│   ├── __init__.py
│   ├── api.py
│   ├── config.py
│   ├── models.py
│   └── renderer.py
├── AGENTS.md
├── main.py
├── requirements.txt
└── .env.example
```

## E-inkhardware

De MVP rendert eerst naar een normale monochrome PNG. Voeg daarna een aparte adapter toe voor het exacte Waveshare-model. De API-, selectie- en renderlogica mogen niet rechtstreeks afhankelijk worden van een hardwaredriver.

Gebruik een verversinterval van ongeveer 30–60 seconden en voer periodiek een volledige refresh uit om ghosting te beperken.
