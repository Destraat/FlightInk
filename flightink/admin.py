from __future__ import annotations

import html
import os
import sqlite3
import subprocess
from pathlib import Path

from flask import Flask, Response, redirect, render_template_string, request, send_file, url_for

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
OUTPUT_PATH = ROOT / "output" / "flightink.png"
DB_PATH = ROOT / "data" / "flightink.db"
EDITABLE_KEYS = {
    "HOME_LAT", "HOME_LON", "RADIUS_NM", "REFRESH_SECONDS",
    "MAXIMUM_DISTANCE_KM", "MINIMUM_ALTITUDE_FT", "DISPLAY_BACKEND",
    "WAVESHARE_MODULE", "PREDICTION_HORIZON_SECONDS",
}


def create_admin_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index() -> str:
        config = _read_env()
        status = _service_status()
        passages = _recent_passages()
        return render_template_string(TEMPLATE, config=config, status=status, passages=passages)

    @app.post("/config")
    def save_config() -> Response:
        current = _read_env()
        for key in EDITABLE_KEYS:
            if key in request.form:
                current[key] = request.form[key].strip()
        _validate_config(current)
        _write_env(current)
        return redirect(url_for("index"))

    @app.post("/action/<name>")
    def action(name: str) -> Response:
        commands = {
            "restart": ["systemctl", "restart", "flightink"],
            "start": ["systemctl", "start", "flightink"],
            "stop": ["systemctl", "stop", "flightink"],
            "preview": [str(ROOT / ".venv/bin/python"), str(ROOT / "main.py"), "--once", "--preview"],
            "display-test": [str(ROOT / ".venv/bin/python"), str(ROOT / "main.py"), "--display-test"],
        }
        command = commands.get(name)
        if command is None:
            return Response("Onbekende actie", status=404)
        try:
            subprocess.run(command, cwd=ROOT, check=True, timeout=90, capture_output=True, text=True)
        except (subprocess.SubprocessError, OSError) as exc:
            return Response(f"Actie mislukt: {html.escape(str(exc))}", status=500)
        return redirect(url_for("index"))

    @app.get("/preview.png")
    def preview() -> Response:
        if not OUTPUT_PATH.exists():
            return Response("Nog geen preview beschikbaar", status=404)
        return send_file(OUTPUT_PATH, mimetype="image/png", max_age=0)

    @app.get("/health")
    def health() -> dict[str, object]:
        return {"ok": True, "service": _service_status(), "preview_exists": OUTPUT_PATH.exists()}

    return app


def _read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_PATH.exists():
        return values
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _write_env(values: dict[str, str]) -> None:
    temporary = ENV_PATH.with_suffix(".tmp")
    temporary.write_text("\n".join(f"{key}={values[key]}" for key in sorted(values)) + "\n", encoding="utf-8")
    temporary.replace(ENV_PATH)


def _validate_config(values: dict[str, str]) -> None:
    lat = float(values.get("HOME_LAT", "0")); lon = float(values.get("HOME_LON", "0"))
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("Ongeldige coördinaten")
    if int(values.get("REFRESH_SECONDS", "60")) < 20:
        raise ValueError("REFRESH_SECONDS moet minimaal 20 zijn")
    if values.get("DISPLAY_BACKEND", "preview") not in {"preview", "waveshare"}:
        raise ValueError("Ongeldige displaybackend")


def _service_status() -> str:
    try:
        result = subprocess.run(["systemctl", "is-active", "flightink"], capture_output=True, text=True, timeout=5)
        return result.stdout.strip() or "onbekend"
    except (subprocess.SubprocessError, OSError):
        return "niet beschikbaar"


def _recent_passages() -> list[dict[str, object]]:
    if not DB_PATH.exists():
        return []
    try:
        with sqlite3.connect(DB_PATH) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute("SELECT callsign, registration, type_code, closest_distance_km, first_seen_at FROM passages ORDER BY first_seen_at DESC LIMIT 20").fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error:
        return []


TEMPLATE = """
<!doctype html><html lang="nl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FlightInk beheer</title><style>
body{font-family:system-ui,sans-serif;background:#f3f3ef;color:#171717;margin:0}main{max-width:1100px;margin:auto;padding:24px}.grid{display:grid;grid-template-columns:1.3fr .7fr;gap:22px}.card{background:white;border:1px solid #d8d8d1;border-radius:14px;padding:20px;margin-bottom:20px}h1{margin:0 0 6px}h2{font-size:18px}label{display:block;font-size:12px;font-weight:700;margin-top:12px}input,select{width:100%;box-sizing:border-box;padding:10px;border:1px solid #bbb;border-radius:8px}button{padding:10px 14px;border:0;border-radius:8px;background:#171717;color:white;margin:4px;cursor:pointer}.muted{color:#666}img{width:100%;border:1px solid #ccc}.status{font-weight:700}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:8px;border-bottom:1px solid #eee;font-size:13px}@media(max-width:800px){.grid{grid-template-columns:1fr}}
</style></head><body><main><h1>FlightInk</h1><p class="muted">Lokale beheerpagina · service: <span class="status">{{ status }}</span></p><div class="grid"><section>
<div class="card"><h2>Live preview</h2><img src="/preview.png?x={{ range(1,999999)|random }}" onerror="this.style.display='none'"><form method="post" action="/action/preview"><button>Nieuwe preview maken</button></form></div>
<div class="card"><h2>Instellingen</h2><form method="post" action="/config">
{% for key in ['HOME_LAT','HOME_LON','RADIUS_NM','REFRESH_SECONDS','MAXIMUM_DISTANCE_KM','MINIMUM_ALTITUDE_FT','PREDICTION_HORIZON_SECONDS','WAVESHARE_MODULE'] %}<label>{{ key }}</label><input name="{{ key }}" value="{{ config.get(key,'') }}">{% endfor %}
<label>DISPLAY_BACKEND</label><select name="DISPLAY_BACKEND"><option value="preview" {% if config.get('DISPLAY_BACKEND')=='preview' %}selected{% endif %}>preview</option><option value="waveshare" {% if config.get('DISPLAY_BACKEND')=='waveshare' %}selected{% endif %}>waveshare</option></select><p><button>Opslaan</button></p></form></div></section><aside>
<div class="card"><h2>Acties</h2>{% for action,label in [('restart','Herstart service'),('start','Start service'),('stop','Stop service'),('display-test','Schermtest')] %}<form method="post" action="/action/{{ action }}"><button>{{ label }}</button></form>{% endfor %}</div>
<div class="card"><h2>Laatste passages</h2><table><tr><th>Vlucht</th><th>Type</th><th>Afstand</th></tr>{% for p in passages %}<tr><td>{{ p.callsign or p.registration }}</td><td>{{ p.type_code }}</td><td>{{ '%.1f km'|format(p.closest_distance_km or 0) }}</td></tr>{% else %}<tr><td colspan="3">Nog geen passages</td></tr>{% endfor %}</table></div></aside></div></main></body></html>
"""


def main() -> None:
    host = os.getenv("ADMIN_HOST", "0.0.0.0")
    port = int(os.getenv("ADMIN_PORT", "8080"))
    create_admin_app().run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
