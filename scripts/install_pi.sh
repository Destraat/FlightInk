#!/usr/bin/env bash
set -euo pipefail

APP_DIR=${FLIGHTINK_DIR:-/opt/flightink}
REPO_URL=https://github.com/Destraat/FlightInk.git
INSTALL_USER=${SUDO_USER:-$USER}
INSTALL_GROUP=$(id -gn "$INSTALL_USER")
SERVICE_TEMPLATE="$APP_DIR/deploy/flightink.service"
SERVICE_TARGET=/etc/systemd/system/flightink.service

sudo apt-get update
sudo apt-get install -y git python3 python3-venv python3-pip python3-pil python3-numpy fonts-dejavu-core

if [ ! -d "$APP_DIR/.git" ]; then
  sudo git clone "$REPO_URL" "$APP_DIR"
else
  sudo git -C "$APP_DIR" pull --ff-only
fi
sudo chown -R "$INSTALL_USER":"$INSTALL_GROUP" "$APP_DIR"

sudo -u "$INSTALL_USER" python3 -m venv "$APP_DIR/.venv"
sudo -u "$INSTALL_USER" "$APP_DIR/.venv/bin/pip" install --upgrade pip
sudo -u "$INSTALL_USER" "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

if [ ! -f "$APP_DIR/.env" ]; then
  sudo -u "$INSTALL_USER" cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  echo "Pas eerst $APP_DIR/.env aan met je eigen coördinaten."
fi

sed \
  -e "s|__FLIGHTINK_USER__|$INSTALL_USER|g" \
  -e "s|__FLIGHTINK_DIR__|$APP_DIR|g" \
  "$SERVICE_TEMPLATE" | sudo tee "$SERVICE_TARGET" >/dev/null

sudo systemctl daemon-reload
sudo systemctl enable flightink.service

echo "Installatie klaar voor gebruiker $INSTALL_USER."
echo "Previewtest: $APP_DIR/.venv/bin/python $APP_DIR/main.py --once --preview"
echo "Hardwaretest: $APP_DIR/.venv/bin/python $APP_DIR/main.py --display-test"
echo "Start daarna met: sudo systemctl start flightink"
