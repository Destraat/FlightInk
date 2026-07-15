# FlightInk Agent Instructions

## Role

You are the software agent for FlightInk. Build and maintain a reliable Python application that converts free ADS-B data into a calm 800x480 e-ink screen for aircraft passing near the configured home point.

## Primary Goal

Deliver a working Raspberry Pi application that:

1. Fetches free live aircraft positions.
2. Selects the most relevant aircraft over or near the configured home point.
3. Shows aircraft type, airline, registration, altitude, speed, heading, and distance.
4. Determines origin and destination when free and reliable data is available.
5. Renders a large, correct side view of the aircraft.
6. Translates current local weather into a simple e-ink background.
7. Shows one flag and one recognizable destination landmark when reliable destination data exists.
8. Can create a PNG preview without attached hardware.
9. Can optionally drive a Waveshare e-paper display.

## Non-Negotiable Requirements

- Do not make a paid API a required dependency.
- The application must keep working when route, weather, or metadata is missing.
- Do not hard-code API keys, coordinates, or personal data.
- Every external request must have a timeout, clear User-Agent, and error handling.
- The main process must not crash because one API call fails.
- Render to a Pillow image first; keep hardware output in a separate adapter.
- Account for ghosting: do not refresh an e-ink display unnecessarily.
- Use type hints, dataclasses, and small testable functions.
- Add tests for every change in selection, distance, mapping, or rendering logic.
- Do not add aircraft photos or logos with unclear copyright status.

## Desired Architecture

```text
flightink/
|-- api/            # ADS-B, weather, and optional free route sources
|-- domain/         # dataclasses, selection, and calculations
|-- render/         # layout, aircraft shapes, weather background
|-- display/        # PNG and Waveshare adapters
|-- data/           # local mappings and cache
`-- main.py         # orchestration and CLI
```

The first MVP may live in a single `flightink.py`, but split it once the file grows beyond roughly 500 lines.

## Aircraft Display

- Always show the aircraft as a clean side view.
- Mirror horizontally based on heading, but do not rotate the aircraft diagonally.
- Use a generic vector shape per category when the exact type is missing:
  - narrow-body jet;
  - wide-body jet;
  - regional jet;
  - turboprop;
  - helicopter;
  - unknown.
- Use airline styling only when it reliably follows from callsign or operator data.
- Special liveries may only be applied through a registration-specific local override.
- For black-and-white e-ink, translate logos and color blocks into patterns, grayscale, or dithering.

## Relevant Aircraft Selection

For every aircraft, calculate at least:

- horizontal distance to the home point with haversine;
- valid airborne status;
- approaching or departing state based on the previous measurement;
- estimated time to closest passage when enough data exists.

Preference order:

1. Aircraft whose predicted track passes closest to the home point.
2. Then approaching aircraft.
3. Then smallest current horizontal distance.
4. Ignore ground vehicles and aircraft below a configurable minimum altitude.

## Route Data

Origin and destination are not reliably present in ADS-B. Implement route resolution in steps:

1. Local cache by callsign plus date.
2. Optional free route source.
3. Inference only when reliable.
4. Otherwise explicitly show `Route unknown`.

Never invent a route based only on airline or flight direction.

## Weather

Use a free source without a required paid key, such as Open-Meteo. Cache the result for at least ten minutes. Translate the current condition into simple backgrounds such as clear, partly cloudy, cloudy, rain, fog, or snow. Clouds are decorative and must not make the aircraft unreadable.

## Layout

Target resolution: 800x480.

- Left and center: large aircraft with generous white space.
- Right column: flight, route, altitude, speed, heading, and distance.
- Bottom right: one destination card with a landmark and one flag.
- Bottom edge: time, date, weather, and last update.
- Use clear typographic hierarchy and high contrast.
- Avoid small text below roughly 14 px at 800x480.

## Execution

Support at least:

```bash
python flightink.py --demo
python flightink.py --once
python flightink.py --loop
```

- `--demo`: fully offline example.
- `--once`: one live fetch and PNG render.
- `--loop`: periodic refresh with fault tolerance.

## Testing and Acceptance

Run for every pull request:

```bash
pytest
python flightink.py --demo
```

Acceptance criteria:

- A valid 800x480 PNG is created.
- No aircraft results in a clean waiting state.
- Missing type code, callsign, registration, or altitude does not crash.
- Haversine distances are tested.
- Horizontal mirroring follows the heading rules.
- The flag appears at most once.
- The destination landmark is not placed in the main aircraft area.

## Git Process

- Work on a feature branch.
- Make small, descriptive commits.
- Open a pull request to `main`.
- In the PR, describe what works, which free sources are used, known limitations, and how it was tested locally.
- Do not merge automatically when tests are missing or hardware behavior is not demonstrably safe.
