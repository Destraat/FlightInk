# Planespotters photos on the e-ink display

FlightInk can look up the latest aircraft photo by registration and then by ICAO24 hex code. With explicit permission from Planespotters, it can download the returned thumbnail once, prepare it for the 800×480 monochrome display, and reuse the local processed PNG.

## Enable the integration

Set the following values in `.env`:

```env
PHOTO_PROVIDER=planespotters
PLANESPOTTERS_USER_AGENT=FlightInk/1.0 (+https://github.com/Destraat/FlightInk)
PLANESPOTTERS_IMAGE_CACHE_ENABLED=true
PLANESPOTTERS_IMAGE_CACHE_DIR=data/aircraft_photos
PLANESPOTTERS_IMAGE_WIDTH=500
PLANESPOTTERS_IMAGE_HEIGHT=268
```

The user agent must remain unique and descriptive and should include a contact URL or email.

`PLANESPOTTERS_IMAGE_CACHE_ENABLED` is deliberately disabled by default. The standard public Photo API terms prohibit downloading and storing image binaries. Enable it only for an implementation for which Planespotters has explicitly granted permission.

## Lookup and fallback order

1. Cached/API result for the aircraft registration.
2. Cached/API result for the aircraft ICAO24 hex code.
3. Existing FlightInk aircraft-family illustration.

API JSON is cached for at most 24 hours. The approved local e-ink image is stored as a processed grayscale PNG together with a small credit manifest. If the API is temporarily unavailable, FlightInk can reuse that local image and attribution.

## Display behaviour

The downloaded thumbnail is:

- fitted into a fixed e-ink area without stretching;
- converted to grayscale;
- auto-contrasted and slightly sharpened;
- stored under `data/aircraft_photos/`;
- credited on-screen with the photographer name and `Planespotters.net`.

FlightInk never commits the cached photos to Git because `data/aircraft_photos/` is ignored.
