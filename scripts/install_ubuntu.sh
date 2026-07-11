#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# install_ubuntu.sh — Fresh install of minesweeper.org on Ubuntu 22.04+
#
# Usage:
#   chmod +x scripts/install_ubuntu.sh
#   sudo scripts/install_ubuntu.sh
#
# What this script does:
#   1. Installs system packages (Python, Node, MySQL, Apache2)
#   2. Creates the MySQL database and user
#   3. Sets up the Python virtual environment and installs dependencies
#   4. Copies .env_example → .env (you must fill in credentials)
#   5. Generates database.py from database_template.py
#   6. Installs the systemd service
#   7. Configures Apache2 as a reverse proxy
#   8. Installs the cron-based auto-deploy
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
APP_USER="ubuntu"
REPO_DIR="/home/${APP_USER}/minesweeper"
VENV_DIR="${REPO_DIR}/venv"
# Split across two services: a multi-worker gunicorn pool for general HTTP
# traffic, and a single-worker instance that owns duel.py's in-memory
# game/matchmaking state (only /duel, /duelold, /pvp, /pvpbeta, /ws/ route
# there — see the Apache vhost below). Both must restart on every deploy;
# scripts/minesweeper_service_update_and_restart.sh already does this.
SERVICE_WEB="minesweeper-web"
SERVICE_PVP="minesweeper-pvp"
WEB_PORT=8000
PVP_PORT=8050
DOMAIN="minesweeper.org"

# ── Helpers ───────────────────────────────────────────────────────────────────
info()  { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
ok()    { echo -e "\033[1;32m[ OK ]\033[0m  $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
die()   { echo -e "\033[1;31m[ERR ]\033[0m  $*" >&2; exit 1; }

[[ $EUID -ne 0 ]] && die "Run this script as root (sudo)."
[[ -d "$REPO_DIR" ]] || die "Repo not found at $REPO_DIR. Clone it first:\n  git clone https://github.com/ajaxchess/minesweeper.org $REPO_DIR"

# ── 1. System packages ────────────────────────────────────────────────────────
info "Installing system packages..."
apt-get update -qq
apt-get install -y -qq \
    python3 python3-pip python3-venv \
    nodejs npm \
    mysql-server \
    apache2 \
    certbot python3-certbot-apache
ok "System packages installed."

# ── Enable Apache modules ─────────────────────────────────────────────────────
info "Enabling Apache modules..."
a2enmod proxy proxy_http proxy_wstunnel headers rewrite ssl
ok "Apache modules enabled."

# ── 2. MySQL setup ────────────────────────────────────────────────────────────
info "Setting up MySQL database..."
# Prompt for DB password
read -rsp "Enter a password for the MySQL root user: " DB_PASS
echo
sudo mysql -p <<SQL
CREATE DATABASE IF NOT EXISTS minesweeper CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'minesweeper_user'@'localhost' IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON minesweeper.* TO 'minesweeper_user'@'localhost';
FLUSH PRIVILEGES;
SQL
ok "MySQL database and user created."

# ── 3. Python virtual environment ─────────────────────────────────────────────
info "Creating Python virtual environment..."
sudo -u "$APP_USER" python3 -m venv "$VENV_DIR"
sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install --quiet --upgrade pip
sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install --quiet -r "$REPO_DIR/requirements.txt"
ok "Python dependencies installed."

# ── 4. Node.js minification tools ─────────────────────────────────────────────
info "Installing JS/CSS minification tools..."
npm install -g --silent terser csso-cli
ok "terser and csso-cli installed globally."

# ── 5. Environment configuration ─────────────────────────────────────────────
info "Setting up .env..."
if [[ ! -f "${REPO_DIR}/.env" ]]; then
    cp "${REPO_DIR}/.env_example" "${REPO_DIR}/.env"
    # Pre-fill DB credentials we already know
    sed -i "s/^DB_NAME=.*/DB_NAME=minesweeper/" "${REPO_DIR}/.env"
    sed -i "s/^DB_USER=.*/DB_USER=minesweeper_user/" "${REPO_DIR}/.env"
    sed -i "s/^DB_PASS=.*/DB_PASS=${DB_PASS}/" "${REPO_DIR}/.env"
    # Generate a random SECRET_KEY
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/^SECRET_KEY=.*/SECRET_KEY=${SECRET_KEY}/" "${REPO_DIR}/.env"
    chown "$APP_USER:$APP_USER" "${REPO_DIR}/.env"
    chmod 600 "${REPO_DIR}/.env"
    warn ".env created from .env_example. Edit it to fill in:"
    warn "  GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GA_TAG, ADMIN_EMAILS"
else
    warn ".env already exists — skipping."
fi

# ── 6. Generate database.py ───────────────────────────────────────────────────
info "Generating database.py from template..."
source "${REPO_DIR}/.env"
cp "${REPO_DIR}/database_template.py" "${REPO_DIR}/database.py"
sed -i "s/the_minesweeper_user/${DB_USER}/g" "${REPO_DIR}/database.py"
sed -i "s/the_password/${DB_PASS}/g"         "${REPO_DIR}/database.py"
sed -i "s/the_db_name/${DB_NAME}/g"          "${REPO_DIR}/database.py"
chown "$APP_USER:$APP_USER" "${REPO_DIR}/database.py"
ok "database.py generated."

# ── 7. Build static assets ────────────────────────────────────────────────────
info "Building minified static assets..."
sudo -u "$APP_USER" bash "${REPO_DIR}/scripts/build_assets.sh" || warn "Asset build failed (continuing)."

# ── 8. systemd services ───────────────────────────────────────────────────────
info "Installing systemd services..."
cat > "/etc/systemd/system/${SERVICE_WEB}.service" <<SERVICE
[Unit]
Description=Minesweeper FastAPI app (web pool — general HTTP traffic)
After=network.target mysql.service

[Service]
User=${APP_USER}
WorkingDirectory=${REPO_DIR}
# Do NOT route /duel, /duelold, /pvp, /pvpbeta, or /ws/ here — that traffic
# depends on in-memory state (duel.py's _games / matchmaking queues) that
# only exists inside a single process. It goes to ${SERVICE_PVP} instead.
# --workers: size to vCPU count (2x cores is a reasonable starting point).
ExecStart=${VENV_DIR}/bin/gunicorn main:app \\
    --worker-class uvicorn.workers.UvicornWorker \\
    --workers 4 \\
    --bind 127.0.0.1:${WEB_PORT} \\
    --timeout 120 \\
    --graceful-timeout 30 \\
    --keep-alive 5 \\
    --access-logfile - \\
    --error-logfile -
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

cat > "/etc/systemd/system/${SERVICE_PVP}.service" <<SERVICE
[Unit]
Description=Minesweeper FastAPI app (pvp/duel — single worker, owns in-memory game state)
After=network.target mysql.service

[Service]
User=${APP_USER}
WorkingDirectory=${REPO_DIR}
# Runs the SAME app (main:app) as ${SERVICE_WEB}, but Apache only routes
# /duel, /duelold, /pvp, /pvpbeta, and /ws/ here. Those routes read/write
# duel.py's module-level _games dict and matchmaking queues directly, which
# only works if every request for a given game lands on the same process —
# stays a SINGLE worker. Don't raise --workers without moving that state
# into something shared (e.g. Redis) first.
ExecStart=${VENV_DIR}/bin/gunicorn main:app \\
    --worker-class uvicorn.workers.UvicornWorker \\
    --workers 1 \\
    --bind 127.0.0.1:${PVP_PORT} \\
    --timeout 120 \\
    --graceful-timeout 30 \\
    --keep-alive 5 \\
    --access-logfile - \\
    --error-logfile -
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable "$SERVICE_WEB" "$SERVICE_PVP"
systemctl start  "$SERVICE_WEB" "$SERVICE_PVP"
ok "systemd services '${SERVICE_WEB}' and '${SERVICE_PVP}' installed and started."

# ── 9. Apache virtual host ────────────────────────────────────────────────────
info "Configuring Apache reverse proxy..."
cat > "/etc/apache2/sites-available/${DOMAIN}.conf" <<APACHE
<VirtualHost *:80>
    ServerName ${DOMAIN}
    ServerAlias www.${DOMAIN}

    ProxyPreserveHost On
    ProxyPass        /static/ !
    Alias /static ${REPO_DIR}/static
    <Directory ${REPO_DIR}/static>
        Require all granted
        Header set Cache-Control "max-age=31536000, public, immutable"
    </Directory>

    AddOutputFilterByType DEFLATE text/html text/css application/javascript application/json text/plain

    # PVP / duel — pinned to the single-worker instance (in-memory game +
    # matchmaking state in duel.py). Apache matches ProxyPass in declaration
    # order, so these specific paths must come before the catch-all "/" below.
    ProxyPass        /ws/       ws://127.0.0.1:${PVP_PORT}/ws/      upgrade=websocket retry=0
    ProxyPassReverse /ws/       ws://127.0.0.1:${PVP_PORT}/ws/

    ProxyPass        /duel      http://127.0.0.1:${PVP_PORT}/duel    retry=0
    ProxyPassReverse /duel      http://127.0.0.1:${PVP_PORT}/duel

    ProxyPass        /duelold   http://127.0.0.1:${PVP_PORT}/duelold retry=0
    ProxyPassReverse /duelold   http://127.0.0.1:${PVP_PORT}/duelold

    ProxyPass        /pvp       http://127.0.0.1:${PVP_PORT}/pvp     retry=0
    ProxyPassReverse /pvp       http://127.0.0.1:${PVP_PORT}/pvp

    ProxyPass        /pvpbeta   http://127.0.0.1:${PVP_PORT}/pvpbeta retry=0
    ProxyPassReverse /pvpbeta   http://127.0.0.1:${PVP_PORT}/pvpbeta

    # Everything else — scaled across the gunicorn worker pool
    ProxyPass        / http://127.0.0.1:${WEB_PORT}/
    ProxyPassReverse / http://127.0.0.1:${WEB_PORT}/

    ErrorLog  \${APACHE_LOG_DIR}/${DOMAIN}-error.log
    CustomLog \${APACHE_LOG_DIR}/${DOMAIN}-access.log combined
</VirtualHost>
APACHE

a2ensite "${DOMAIN}.conf"
a2dissite 000-default.conf 2>/dev/null || true
systemctl reload apache2
ok "Apache configured for ${DOMAIN}."

# ── 10. Cron auto-deploy ──────────────────────────────────────────────────────
info "Installing cron auto-deploy (every 5 minutes)..."
CRON_LINE="*/5 * * * * ${APP_USER} bash ${REPO_DIR}/scripts/minesweeper_service_update_and_restart.sh >> /var/log/minesweeper-deploy.log 2>&1"
CRON_FILE="/etc/cron.d/minesweeper-deploy"
echo "$CRON_LINE" > "$CRON_FILE"
chmod 644 "$CRON_FILE"
ok "Cron job installed at ${CRON_FILE}."

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════"
ok "Installation complete!"
echo ""
echo "  Next steps:"
echo "  1. Edit ${REPO_DIR}/.env and fill in:"
echo "       GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET"
echo "       GA_TAG, ADMIN_EMAILS"
echo "  2. Get an SSL certificate:"
echo "       sudo certbot --apache -d ${DOMAIN} -d www.${DOMAIN}"
echo "  3. Restart the services:"
echo "       sudo systemctl restart ${SERVICE_WEB} ${SERVICE_PVP}"
echo "  4. Check logs:"
echo "       sudo journalctl -u ${SERVICE_WEB} -f"
echo "       sudo journalctl -u ${SERVICE_PVP} -f"
echo "═══════════════════════════════════════════════════════════"
