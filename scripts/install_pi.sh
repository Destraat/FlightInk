#!/usr/bin/env bash
set -euo pipefail

APP_DIR=${FLIGHTINK_DIR:-/opt/flightink}
REPO_URL=https://github.com/Destraat/FlightInk.git
WAVESHARE_DRIVER_URL=${WAVESHARE_DRIVER_URL:-git+https://github.com/waveshareteam/e-Paper.git#subdirectory=RaspberryPi_JetsonNano/python}
INSTALL_USER=${SUDO_USER:-$USER}
INSTALL_GROUP=$(id -gn "$INSTALL_USER")

sudo apt-get update
sudo apt-get install -y git python3 python3-venv python3-pip python3-dev build-essential python3-pil python3-numpy fonts-dejavu-core

if command -v raspi-config >/dev/null 2>&1; then
  sudo raspi-config nonint do_spi 0
fi

if [ ! -d "$APP_DIR/.git" ]; then
  sudo git clone "$REPO_URL" "$APP_DIR"
else
  sudo git -C "$APP_DIR" pull --ff-only
fi
sudo chown -R "$INSTALL_USER":"$INSTALL_GROUP" "$APP_DIR"

sudo -u "$INSTALL_USER" python3 -m venv "$APP_DIR/.venv"
sudo -u "$INSTALL_USER" "$APP_DIR/.venv/bin/pip" install --upgrade pip
sudo -u "$INSTALL_USER" "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"
sudo -u "$INSTALL_USER" "$APP_DIR/.venv/bin/pip" install --upgrade "$WAVESHARE_DRIVER_URL"

if [ ! -f "$APP_DIR/.env" ]; then
  sudo -u "$INSTALL_USER" cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  echo "Edit $APP_DIR/.env with your own coordinates before starting the service."
fi

install_service() {
  local template=$1
  local target=$2
  sed -e "s|__FLIGHTINK_USER__|$INSTALL_USER|g" -e "s|__FLIGHTINK_DIR__|$APP_DIR|g" "$template" | sudo tee "$target" >/dev/null
}

install_service "$APP_DIR/deploy/flightink.service" /etc/systemd/system/flightink.service
install_service "$APP_DIR/deploy/flightink-admin.service" /etc/systemd/system/flightink-admin.service

sudo systemctl daemon-reload
sudo systemctl enable flightink.service flightink-admin.service

ADMIN_PORT=$(awk -F= '/^ADMIN_PORT=/{print $2}' "$APP_DIR/.env" | tail -n 1)
ADMIN_PORT=${ADMIN_PORT:-8090}
HOST_IP=$(hostname -I | awk '{print $1}')
echo "Installation complete for user $INSTALL_USER."
echo "Preview test: $APP_DIR/.venv/bin/python $APP_DIR/main.py --once --preview"
echo "Hardware test: $APP_DIR/.venv/bin/python $APP_DIR/main.py --display-test"
echo "Start: sudo systemctl start flightink flightink-admin"
echo "Admin page: http://${HOST_IP:-flightink.local}:$ADMIN_PORT"
