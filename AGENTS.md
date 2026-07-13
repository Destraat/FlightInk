# AGENTS.md

## Purpose

Build and maintain FlightInk: a local, open-source e-ink flight tracker for aircraft passing near the configured home location.

## Core requirements

1. Use free data sources for all essential functionality.
2. Read the home location from `HOME_LAT` and `HOME_LON`; never hard-code real coordinates.
3. Fetch live aircraft within the configured search radius.
4. Prefer the aircraft predicted to pass closest to the home location, not merely the aircraft currently closest.
5. Show at least callsign, registration, aircraft type, altitude, speed, current distance, and predicted closest passage.
6. Render a large, clean side view of the selected aircraft.
7. Use aircraft-family silhouettes and local airline-livery metadata with a neutral fallback.
8. Mirror the aircraft horizontally according to its direction of travel; do not rotate it diagonally.
9. Show current weather from a free weather source.
10. Render primarily to an 800×480 monochrome image.
11. Keep hardware integration behind the display adapter in `flightink/display.py`.
12. Avoid unnecessary e-paper refreshes by comparing the newly rendered frame with the previous frame.
13. Continue operating during temporary network or API failures by using safe cached fallbacks.
14. Provide explicit offline, stale-data, source-error, and no-aircraft states.
15. Keep the local administration dashboard suitable for a trusted LAN only.

## Data integrity rules

- ADS-B position data does not reliably provide departure and destination airports.
- Never invent route information.
- Route mappings in `data/routes.json` must be exact and manually verified.
- Do not add broad wildcard route mappings that can produce incorrect destinations.
- Show `Route unknown` when no reliable route exists.
- Missing registration, type code, callsign, airline, weather, or route data must use clear fallbacks.
- Do not present a prediction as certainty; closest-passage calculations assume constant speed and track.

## Architecture

- `flightink/api.py`: free external data sources, HTTP retries, timeouts, and parsing.
- `flightink/catalog.py`: airline and aircraft metadata loaded from local JSON files.
- `flightink/config.py`: validated environment configuration.
- `flightink/models.py`: domain dataclasses and derived properties.
- `flightink/prediction.py`: closest-passage prediction and selection scoring.
- `flightink/aircraft_shapes.py`: recognizable aircraft-family silhouettes.
- `flightink/renderer.py`: deterministic, hardware-independent Pillow rendering.
- `flightink/display.py`: preview and Waveshare display adapters.
- `flightink/routes.py`: exact local route resolution.
- `flightink/storage.py`: SQLite passage aggregation and JSON cache.
- `flightink/admin.py`: local administration dashboard.
- `main.py`: application lifecycle, polling loop, fallback handling, and CLI modes.
- `deploy/`: systemd service templates.
- `scripts/install_pi.sh`: Raspberry Pi installation and service configuration.

## Development rules

- Support Python 3.11 and 3.12.
- Add type hints to public functions and non-trivial internal functions.
- Use timeouts for every external HTTP request.
- Use retries only for safe idempotent requests.
- A temporary external-service failure must not terminate the main loop.
- Keep the renderer deterministic and testable.
- Keep display-driver imports isolated so local development works without Raspberry Pi hardware.
- Do not commit `.env`, exact home coordinates, SQLite databases, caches, generated output, logs, or credentials.
- Do not introduce a paid API as a mandatory dependency.
- Do not expose the administration dashboard publicly without adding authentication and transport security.
- Validate all configuration changes made through the administration dashboard.
- Avoid shell commands constructed from user-controlled strings.
- Preserve explicit error states instead of hiding failures.
- Update the README and `.env.example` whenever configuration or installation behavior changes.

## Testing expectations

Add or update tests for changes affecting:

- distance calculations;
- passage prediction;
- aircraft selection;
- API parsing and fallbacks;
- airline and aircraft catalogs;
- route resolution;
- passage aggregation;
- display refresh deduplication;
- renderer output dimensions;
- aircraft-shape selection;
- administration configuration validation.

Run before merging:

```bash
pytest -q
python -m compileall flightink main.py
```

The GitHub Actions workflow must pass on both Python 3.11 and Python 3.12.

## Display guidance

- Target resolution: 800×480.
- Target colors: black and white; grayscale must remain legible after dithering.
- Use strong outlines and distinct patterns rather than subtle color differences.
- Keep critical text away from the screen edges.
- Avoid refreshing only to update a clock.
- Preserve a clear information hierarchy: aircraft first, route and passage second, weather and statistics last.
- Test major visual changes on the physical e-paper panel, not only in a desktop PNG preview.

## Acceptance criteria

A change is complete when:

- all automated tests pass;
- compilation succeeds;
- `python main.py --once --preview` generates an 800×480 PNG with valid environment settings;
- missing or malformed API data does not crash the application;
- temporary network failures produce an appropriate fallback state;
- no secrets, generated runtime files, or real home coordinates are committed;
- documentation and configuration examples are current;
- any hardware-specific change preserves preview-mode operation on a non-Raspberry Pi system.