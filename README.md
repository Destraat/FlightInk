# FlightInk

<p align="center">
  <img src="assets/Flightink.png" alt="FlightInk e-ink flight display" width="900">
</p>

FlightInk is a local, open-source e-ink flight display for aircraft passing near your home. It selects the aircraft most likely to pass closest to your configured location, predicts the closest point of approach, renders a recognizable aircraft silhouette and airline livery, and shows the result on a Waveshare 7.5-inch 800×480 black-and-white e-paper display.

FlightInk can use either free internet ADS-B data, your own RTL-SDR USB receiver and 1090 MHz antenna, or a hybrid setup that prefers your own receiver and falls back to the internet.

## Features

- Local aircraft reception through an RTL-SDR USB dongle, 1090 MHz antenna, and dump1090/readsb.
- Free remote ADS-B fallback through Airplanes.live.
- Current temperature, cloud cover, wind speed, and wind direction from Open-Meteo.
- Predicted closest point of approach instead of selecting only by current distance.
- Recognizable silhouettes for narrow-body aircraft, regional jets, wide-bodies, Boeing 747s, Airbus A380s, turboprops, and business jets.
- Airline liveries and aircraft metadata from local JSON catalogs.
- SQLite passage history and daily statistics.
- Cached fallback data during temporary network or API failures.
- Duplicate-frame detection to avoid unnecessary e-paper refreshes.
- PNG preview mode, physical display test, and local ADS-B receiver test.
- Local administration dashboard on port `8090`, so it does not collide with dump1090/readsb on `8080`.
- systemd services and automated tests on Python 3.11 and 3.12.

## Hardware

### Required

- Raspberry Pi Zero 2 W with GPIO headers, or a Raspberry Pi Zero W if you can tolerate slower installs and refreshes;
- Waveshare 7.5-inch black-and-white 800×480 e-Paper HAT;
- microSD card;
- 5 V micro-USB power supply;
- supplied Waveshare driver board and ribbon cable.

### Optional but recommended: your own ADS-B receiver

To receive aircraft directly instead of relying only on internet data, add:

- an RTL-SDR USB dongle suitable for 1090 MHz ADS-B;
- a 1090 MHz ADS-B antenna;
- a USB OTG adapter or powered USB hub for the Raspberry Pi Zero family;
- dump1090, dump1090-fa, dump1090-mutability, or readsb.

The USB receiver does not connect directly to FlightInk. Decoder software reads the radio signals and exposes aircraft as JSON. FlightInk reads that JSON endpoint.

Typical data flow:

```text
Aircraft transponder
        ↓ 1090 MHz
ADS-B antenna
        ↓
RTL-SDR USB dongle
        ↓ USB
Raspberry Pi + dump1090/readsb
        ↓ local JSON
FlightInk
        ↓ SPI
Waveshare e-paper display
```

The default local endpoint is:

```text
http://127.0.0.1:8080/data/aircraft.json
```

This is the common dump1090/readsb `aircraft.json` format. Change `LOCAL_ADSB_URL` when your decoder exposes another path or runs on another device.

## Aircraft source modes

Configure the source in `.env`:

```env
# Prefer your own USB receiver and use Airplanes.live as fallback
AIRCRAFT_SOURCE=hybrid
LOCAL_ADSB_URL=http://127.0.0.1:8080/data/aircraft.json
LOCAL_ADSB_TIMEOUT_SECONDS=3
```

Supported modes:

| Mode | Behaviour |
|---|---|
| `local` | Use only the local RTL-SDR/dump1090/readsb receiver. |
| `remote` | Use only Airplanes.live. No USB receiver is required. |
| `hybrid` | Prefer the local receiver and fall back to Airplanes.live. |

`hybrid` is the recommended mode. It keeps the project useful when the antenna or decoder is unavailable, while preferring aircraft received at your own location.

## Test the USB receiver

First verify that the decoder endpoint responds:

```bash
curl http://127.0.0.1:8080/data/aircraft.json
```

Then run FlightInk's diagnostic:

```bash
python main.py --adsb-test
```

The command prints the first usable locally received aircraft, including callsign, registration, type, distance, and altitude.

When no aircraft are visible, confirm that:

- the RTL-SDR dongle is detected with `lsusb`;
- dump1090/readsb is running;
- the antenna is connected and placed near a window or outdoors;
- the configured JSON URL opens locally;
- aircraft are within reception range;
- `MINIMUM_ALTITUDE_FT` and `MAXIMUM_DISTANCE_KM` are not filtering everything.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set your coordinates and choose a source:

```env
HOME_LAT=50.8514
HOME_LON=5.6910
AIRCRAFT_SOURCE=remote
DISPLAY_BACKEND=preview
```

Generate one preview frame:

```bash
python main.py --once --preview
```

Run the tests:

```bash
pytest -q
python -m compileall flightink main.py
```

## Raspberry Pi installation

FlightInk runs best on a Raspberry Pi Zero 2 W, but the same installation path also works on a Raspberry Pi Zero W. Expect the first dependency install and each screen refresh to be slower on the original Zero W.

```bash
git clone https://github.com/Destraat/FlightInk.git
cd FlightInk
chmod +x scripts/install_pi.sh
./scripts/install_pi.sh
sudo nano /opt/flightink/.env
```

The installer enables SPI when `raspi-config` is available, installs Pi-only runtime dependencies from `requirements-pi.txt`, and installs the official Waveshare Python driver inside the virtual environment.

At minimum, set:

```env
HOME_LAT=your_latitude
HOME_LON=your_longitude
AIRCRAFT_SOURCE=hybrid
LOCAL_ADSB_URL=http://127.0.0.1:8080/data/aircraft.json
DISPLAY_BACKEND=waveshare
WAVESHARE_MODULE=waveshare_epd.epd7in5_V2
```

Test before starting the service:

```bash
/opt/flightink/.venv/bin/python /opt/flightink/main.py --adsb-test
/opt/flightink/.venv/bin/python /opt/flightink/main.py --once --preview
/opt/flightink/.venv/bin/python /opt/flightink/main.py --display-test
```

Start the services:

```bash
sudo systemctl start flightink flightink-admin
sudo systemctl status flightink
journalctl -u flightink -f
```

If the Waveshare import fails, re-run the installer and check these quick diagnostics:

```bash
ls /dev/spidev*
/opt/flightink/.venv/bin/python -c "import spidev, gpiozero"
/opt/flightink/.venv/bin/python -c "import waveshare_epd.epd7in5_V2 as m; print(m.EPD_WIDTH, m.EPD_HEIGHT)"
```

## Administration dashboard

Open the local dashboard from another device on the same network:

```text
http://flightink.local:8090
```

When mDNS is unavailable, run `hostname -I` and use the Raspberry Pi IP address. Do not expose port `8090` directly to the public internet.

## Configuration

```env
HOME_LAT=----
HOME_LON=----
RADIUS_NM=10
REFRESH_SECONDS=60
MAXIMUM_DISTANCE_KM=20
MINIMUM_ALTITUDE_FT=500
REQUEST_TIMEOUT_SECONDS=15
STALE_AIRCRAFT_SECONDS=900
STALE_WEATHER_SECONDS=3600
PREDICTION_HORIZON_SECONDS=900

AIRCRAFT_SOURCE=hybrid
LOCAL_ADSB_URL=http://127.0.0.1:8080/data/aircraft.json
LOCAL_ADSB_TIMEOUT_SECONDS=3

OUTPUT_PATH=output/flightink.png
DATABASE_PATH=data/flightink.db
CACHE_PATH=data/cache.json
DISPLAY_BACKEND=preview
WAVESHARE_MODULE=waveshare_epd.epd7in5_V2
ADMIN_HOST=0.0.0.0
ADMIN_PORT=8090
```

Never commit your real home coordinates or `.env` file.

## Route data limitation

ADS-B position data does not reliably include departure and destination airports. FlightInk never guesses routes. Exact verified mappings can be added to `data/routes.json`; otherwise the display shows `Route unknown`.

## Project structure

```text
FlightInk/
├── assets/                     # README preview assets
├── data/                       # airlines, aircraft types, routes, destinations
├── deploy/                     # systemd service templates
├── flightink/
│   ├── admin.py                # local administration dashboard
│   ├── aircraft_shapes.py      # aircraft-family silhouettes
│   ├── api.py                  # local and remote ADS-B plus weather clients
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
├── .env.example
├── AGENTS.md
└── main.py
```

## Design principles

- Free data sources must remain sufficient for the core application.
- A local receiver is preferred when configured, but must not be mandatory.
- Missing data must produce an explicit fallback rather than invented information.
- Hardware-specific code must remain isolated from data retrieval and rendering.
- Screen refreshes should occur only when the visible frame changes.
- The application must continue through temporary receiver, network, and API failures.
