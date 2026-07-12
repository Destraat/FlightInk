#!/usr/bin/env bash
set -euo pipefail

APP_DIR=/opt/flightink
REPO_URL=https://github.com/Destraat/FlightInk.git

sudo apt-get update
sudo apt-get install -y git python3 python3-venv python3-pip python3-pil python3-numpy fonts-dejavu-core

if [ ! -d "$APP_DIR/.git" ]; then
  sudo git clone "$REPO_URL" "$APP_DIR"
else
  sudo git -C "$APP_DIR" pull --ff-only
fi
sudo chown -R "$USER":"$USER" "$APP_DIR"
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

if [ ! -f "$APP_DIR/.env" ]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  echo "Pas eerst $APP_DIR/.env aan met je eigen coördinaten."
fi

sudo cp "$APP_DIR/deploy/flightink.service" /etc/systemd/system/flightink.service
sudo systemctl daemon-reload
sudo systemctl enable flightink.service

echo "Installatie klaar. Test met: $APP_DIR/.venv/bin/python $APP_DIR/main.py --once --preview"
echo "Start daarna met: sudo systemctl start flightink"
