# FlightInk

<p align="center">
  <img src="assets/Flightink.png" alt="FlightInk e-ink flight display" width="900">
</p>

FlightInk is a local, open-source e-ink flight display for aircraft passing near your home. It selects the aircraft most likely to pass closest to your configured location, predicts the closest point of approach, renders a recognizable aircraft silhouette and airline livery, and shows the result on a Waveshare 7.5-inch 800×480 black-and-white e-paper display.

The core application uses free data sources and performs all rendering and storage locally.

## Features

- Live ADS-B aircraft positions from Airplanes.live.
- Current temperature, cloud cover, wind speed, and wind direction from Open-Meteo.
- Predicted closest point of approach instead of selecting only by current distance.
- Configurable search radius, minimum altitude, maximum distance, and prediction horizon.
- Recognizable silhouettes for narrow-body aircraft, regional jets, wide-bodies, Boeing 747s, Airbus A380s, turboprops, and business jets.
- Airline liveries and aircraft metadata from local JSON catalogs.
- Exact local route mappings with a safe `Route unknown` fallback.
- SQLite passage history and daily statistics.
- Cached fallback data during temporary network or API failures.
- Duplicate-frame detection to avoid unnecessary e-paper refreshes.
- Clear live, offline, stale-data, source-error, and no-aircraft display states.
- PNG preview mode for development.
- Configurable Waveshare display adapter.
- Hardware test mode for validating the display before running live data.
- Local administration dashboard on port `8080`.
- systemd services for both the display and the administration dashboard.
- Automated tests on Python 3.11 and 3.12 through GitHub Actions.

## Hardware

The reference build uses:

- Raspberry Pi Zero 2 W with GPIO headers;
- Waveshare 7.5-inch black-and-white e-Paper HAT;
- 800×480 resolution;
- microSD card;
- 5 V micro-USB power supply;
- the supplied Waveshare ribbon cable and driver board.

The default driver module is:

```env
WAVESHARE_MODULE=waveshare_epd.epd7in5_V2
```

Waveshare has produced multiple revisions. Confirm the module name for the exact revision printed on your panel or driver board.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set your own coordinates in `.env`:

```env
HOME_LAT=52.0000
HOME_LON=6.0000
DISPLAY_BACKEND=preview
```

Generate one preview frame:

```bash
python main.py --once --preview
```

The generated image is written to:

```text
output/flightink.png
```

Run the tests:

```bash
pytest -q
python -m compileall flightink main.py
```

## Raspberry Pi installation

```bash
git clone https://github.com/Destraat/FlightInk.git
cd FlightInk
chmod +x scripts/install_pi.sh
./scripts/install_pi.sh
```

The installer places the application in `/opt/flightink`, creates a virtual environment, installs the dependencies, and configures the systemd services for the detected Linux user.

Edit the configuration:

```bash
sudo nano /opt/flightink/.env
```

At minimum, set:

```env
HOME_LAT=your_latitude
HOME_LON=your_longitude
DISPLAY_BACKEND=waveshare
WAVESHARE_MODULE=waveshare_epd.epd7in5_V2
```

## Test before enabling the live service

Create a normal PNG preview:

```bash
/opt/flightink/.venv/bin/python /opt/flightink/main.py --once --preview
```

Run the physical display test:

```bash
/opt/flightink/.venv/bin/python /opt/flightink/main.py --display-test
```

The display test verifies the screen dimensions, solid black and white areas, line rendering, and basic text output.

## Start the services

```bash
sudo systemctl start flightink
sudo systemctl start flightink-admin
sudo systemctl status flightink
sudo systemctl status flightink-admin
```

Follow the live application log:

```bash
journalctl -u flightink -f
```

## Administration dashboard

The local administration dashboard provides:

- current service status;
- live preview image;
- editable coordinates and runtime settings;
- display backend selection;
- preview and display-test actions;
- start, stop, and restart controls;
- recent aircraft passages;
- a local health endpoint.

Open it from another device on the same local network:

```text
http://flightink.local:8080
```

When mDNS is unavailable, use the Raspberry Pi address:

```bash
hostname -I
```

Then open, for example:

```text
http://192.168.1.50:8080
```

The dashboard is intended only for a trusted local network. Do not expose port `8080` directly to the public internet.

## Configuration

Important environment variables include:

```env
HOME_LAT=52.5600
HOME_LON=5.9100
RADIUS_NM=10
REFRESH_SECONDS=60
MAXIMUM_DISTANCE_KM=20
MINIMUM_ALTITUDE_FT=500
SELECTION_HOLD_SECONDS=90
REQUEST_TIMEOUT_SECONDS=15
STALE_AIRCRAFT_SECONDS=900
STALE_WEATHER_SECONDS=3600
PREDICTION_HORIZON_SECONDS=900
OUTPUT_PATH=output/flightink.png
DATABASE_PATH=data/flightink.db
CACHE_PATH=data/cache.json
DISPLAY_BACKEND=preview
WAVESHARE_MODULE=waveshare_epd.epd7in5_V2
ADMIN_HOST=0.0.0.0
ADMIN_PORT=8080
```

Never commit your real home coordinates or `.env` file.

## Route data limitation

Free ADS-B position data does not reliably include the departure and destination airports for every flight. FlightInk therefore does not guess routes.

Exact, verified mappings can be added to:

```text
data/routes.json
```

When no reliable mapping exists, the display shows `Route unknown`.

## Project structure

```text
FlightInk/
├── assets/                     # README preview assets
├── data/                       # airlines, aircraft types, routes, destinations
├── deploy/                     # systemd service templates
├── flightink/
│   ├── admin.py                # local administration dashboard
│   ├── aircraft_shapes.py      # aircraft-family silhouettes
│   ├── api.py                  # external data clients
│   ├── catalog.py              # local metadata catalogs
│   ├── config.py               # environment configuration
│   ├── display.py              # preview and Waveshare adapters
│   ├── models.py               # domain models
│   ├── prediction.py           # closest-passage prediction
│   ├── renderer.py             # hardware-independent renderer
│   ├── routes.py               # exact route resolution
│   └── storage.py              # SQLite history and local cache
├── scripts/install_pi.sh
├── tests/
├── .github/workflows/test.yml
├── .env.example
├── AGENTS.md
└── main.py
```

## Design principles

- Free data sources must remain sufficient for the core application.
- Missing data must produce an explicit fallback rather than invented information.
- Hardware-specific code must remain isolated from data retrieval and rendering.
- Screen refreshes should occur only when the visible frame changes.
- The application must continue running through temporary network and API failures.
- Exact home coordinates, generated databases, caches, and output images must not be committed.
