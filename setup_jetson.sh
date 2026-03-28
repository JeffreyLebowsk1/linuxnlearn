#!/usr/bin/env bash
# ============================================================================
# LinuxNLearn – Jetson Setup Script
#
# Pulls the latest code, installs dependencies, configures a Cloudflare tunnel
# (cccc-notes) to serve learn.mdilworth.com → localhost:2001, and sets up
# systemd services so both the app and tunnel survive reboots.
#
# Usage:
#   chmod +x setup_jetson.sh && ./setup_jetson.sh
#
# Prerequisites:
#   - cloudflared installed and authenticated (cloudflared login)
#   - Tunnel "cccc-notes" already created (cloudflared tunnel list)
#   - Python 3.8+ and pip installed
# ============================================================================
set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
APP_NAME="linuxnlearn"
APP_PORT=2001
TUNNEL_NAME="cccc-notes"
HOSTNAME="learn.mdilworth.com"
REPO_URL="https://github.com/JeffreyLebowsk1/linuxnlearn.git"
INSTALL_DIR="$HOME/$APP_NAME"
VENV_DIR="$INSTALL_DIR/venv"
CLOUDFLARED_CONFIG_DIR="$HOME/.cloudflared"
CLOUDFLARED_CONFIG="$CLOUDFLARED_CONFIG_DIR/config.yml"

# ── Colors ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { printf "${GREEN}[✓]${NC} %s\n" "$1"; }
warn()  { printf "${YELLOW}[!]${NC} %s\n" "$1"; }
error() { printf "${RED}[✗]${NC} %s\n" "$1"; exit 1; }

# ── Preflight checks ────────────────────────────────────────────────────────
echo ""
echo "============================================"
echo "  LinuxNLearn – Jetson Setup"
echo "============================================"
echo ""

command -v python3 >/dev/null 2>&1 || error "python3 is not installed"
command -v pip3    >/dev/null 2>&1 || command -v pip >/dev/null 2>&1 || error "pip is not installed"
command -v git     >/dev/null 2>&1 || error "git is not installed"
command -v cloudflared >/dev/null 2>&1 || error "cloudflared is not installed. Install: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"

info "All prerequisites found"

# ── Verify tunnel exists ────────────────────────────────────────────────────
if ! cloudflared tunnel list 2>/dev/null | grep -q "$TUNNEL_NAME"; then
    error "Tunnel '$TUNNEL_NAME' not found. Create it with: cloudflared tunnel create $TUNNEL_NAME"
fi
info "Tunnel '$TUNNEL_NAME' exists"

# Get the tunnel UUID for config
TUNNEL_UUID=$(cloudflared tunnel list 2>/dev/null | grep "$TUNNEL_NAME" | awk '{print $1}')
info "Tunnel UUID: $TUNNEL_UUID"

# ── Pull or clone repo ──────────────────────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
    info "Repo exists at $INSTALL_DIR – pulling latest"
    cd "$INSTALL_DIR"
    git fetch origin
    git reset --hard origin/main
    git clean -fd
else
    warn "Cloning repo to $INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi
info "Code is up to date"

# ── Python virtual environment & dependencies ────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    info "Created virtual environment"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
pip install -r requirements.txt -q
info "Python dependencies installed"

# ── Configure .env ───────────────────────────────────────────────────────────
if [ ! -f "$INSTALL_DIR/.env" ]; then
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
    # Set port and disable ngrok (using cloudflared instead)
    sed -i "s/^PORT=.*/PORT=$APP_PORT/" "$INSTALL_DIR/.env"
    sed -i "s/^NGROK_AUTH_TOKEN=.*/NGROK_AUTH_TOKEN=/" "$INSTALL_DIR/.env"
    warn "Created .env from template – edit it to add your AI provider API keys"
else
    # Ensure port is set correctly
    sed -i "s/^PORT=.*/PORT=$APP_PORT/" "$INSTALL_DIR/.env"
    # Clear ngrok token so it doesn't try to connect
    sed -i "s/^NGROK_AUTH_TOKEN=.*/NGROK_AUTH_TOKEN=/" "$INSTALL_DIR/.env"
    info ".env already exists – updated PORT to $APP_PORT and cleared ngrok token"
fi

# ── Cloudflare tunnel config ────────────────────────────────────────────────
mkdir -p "$CLOUDFLARED_CONFIG_DIR"

cat > "$CLOUDFLARED_CONFIG" <<EOF
tunnel: $TUNNEL_UUID
credentials-file: $CLOUDFLARED_CONFIG_DIR/$TUNNEL_UUID.json

ingress:
  - hostname: $HOSTNAME
    service: http://localhost:$APP_PORT
  - service: http_status:404
EOF

info "Cloudflared config written to $CLOUDFLARED_CONFIG"

# ── DNS CNAME route ─────────────────────────────────────────────────────────
echo ""
info "Setting up DNS route: $HOSTNAME → $TUNNEL_NAME"
if cloudflared tunnel route dns "$TUNNEL_NAME" "$HOSTNAME" 2>&1; then
    info "DNS CNAME created for $HOSTNAME"
else
    warn "DNS route may already exist (this is OK if it was previously set up)"
fi

# ── Systemd service: LinuxNLearn app ────────────────────────────────────────
ESCAPED_USER=$(whoami)
APP_SERVICE="/etc/systemd/system/$APP_NAME.service"

sudo tee "$APP_SERVICE" > /dev/null <<EOF
[Unit]
Description=LinuxNLearn Flask Application
After=network.target

[Service]
Type=simple
User=$ESCAPED_USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$VENV_DIR/bin/gunicorn --bind 0.0.0.0:$APP_PORT --workers 2 --timeout 120 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

info "Created systemd service: $APP_NAME"

# ── Systemd service: Cloudflare tunnel ──────────────────────────────────────
TUNNEL_SERVICE="/etc/systemd/system/cloudflared-$TUNNEL_NAME.service"

sudo tee "$TUNNEL_SERVICE" > /dev/null <<EOF
[Unit]
Description=Cloudflare Tunnel ($TUNNEL_NAME)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$ESCAPED_USER
ExecStart=$(command -v cloudflared) tunnel --config $CLOUDFLARED_CONFIG run $TUNNEL_NAME
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

info "Created systemd service: cloudflared-$TUNNEL_NAME"

# ── Enable and start services ───────────────────────────────────────────────
sudo systemctl daemon-reload
sudo systemctl enable "$APP_NAME"
sudo systemctl enable "cloudflared-$TUNNEL_NAME"
sudo systemctl restart "$APP_NAME"
sudo systemctl restart "cloudflared-$TUNNEL_NAME"

# Wait a moment for services to start
sleep 3

# ── Verify ──────────────────────────────────────────────────────────────────
echo ""
echo "============================================"
echo "  Status Check"
echo "============================================"
echo ""

if systemctl is-active --quiet "$APP_NAME"; then
    info "App service is running"
else
    warn "App service may still be starting – check: sudo journalctl -u $APP_NAME -f"
fi

if systemctl is-active --quiet "cloudflared-$TUNNEL_NAME"; then
    info "Cloudflare tunnel is running"
else
    warn "Tunnel service may still be starting – check: sudo journalctl -u cloudflared-$TUNNEL_NAME -f"
fi

echo ""
echo "============================================"
echo "  Setup Complete!"
echo "============================================"
echo ""
echo "  Local:   http://localhost:$APP_PORT"
echo "  Public:  https://$HOSTNAME"
echo ""
echo "  Useful commands:"
echo "    sudo systemctl status $APP_NAME"
echo "    sudo systemctl status cloudflared-$TUNNEL_NAME"
echo "    sudo journalctl -u $APP_NAME -f"
echo "    sudo journalctl -u cloudflared-$TUNNEL_NAME -f"
echo ""
echo "  NOTE: Edit $INSTALL_DIR/.env to add your AI API keys"
echo "        then restart: sudo systemctl restart $APP_NAME"
echo ""
