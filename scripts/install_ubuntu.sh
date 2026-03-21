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
SERVICE_NAME="minesweeper"
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
    libapache2-mod-proxy-uwsgi \
    certbot python3-certbot-apache
ok "System packages installed."

# ── Enable Apache modules ─────────────────────────────────────────────────────
info "Enabling Apache modules..."
a2enmod proxy proxy_http proxy_wstunnel headers rewrite ssl
ok "Apache modules enabled."

# ── 2. MySQL setup ────────────────────────────────────────────────────────────
info "Setting up MySQL database..."
# Prompt for DB password
read -rsp "Enter a password for the MySQL minesweeper user: " DB_PASS
echo
mysql -u root <<SQL
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
chown "$APP_USER:$APP_USER" "${REPO_DIR}/database.py"
ok "database.py generated."

# ── 7. Build static assets ────────────────────────────────────────────────────
info "Building minified static assets..."
sudo -u "$APP_USER" bash "${REPO_DIR}/scripts/build_assets.sh" || warn "Asset build failed (continuing)."

# ── 8. systemd service ────────────────────────────────────────────────────────
info "Installing systemd service..."
cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<SERVICE
[Unit]
Description=Minesweeper FastAPI App
After=network.target mysql.service

[Service]
User=${APP_USER}
WorkingDirectory=${REPO_DIR}
ExecStart=${VENV_DIR}/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl start  "$SERVICE_NAME"
ok "systemd service '${SERVICE_NAME}' installed and started."

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
    </Directory>

    ProxyPass        /ws/ ws://127.0.0.1:8000/ws/
    ProxyPassReverse /ws/ ws://127.0.0.1:8000/ws/

    ProxyPass        / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/

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
echo "  3. Restart the service:"
echo "       sudo systemctl restart ${SERVICE_NAME}"
echo "  4. Check logs:"
echo "       sudo journalctl -u ${SERVICE_NAME} -f"
echo "═══════════════════════════════════════════════════════════"
