# ExoCortex — Deployment Guide

After following this guide you will have a fully functional ExoCortex instance
running behind HTTPS with all services containerised. AI keys, Stripe keys,
Telegram token, and agent prompts are configured in the Admin UI — not in
environment files.

---

## Prerequisites

- Linux server (Ubuntu 22.04+ recommended), min 4 GB RAM
- Docker Engine 24+ and Docker Compose v2
- A domain name with DNS A records pointing to the server:
  - `yourdomain.com` → server IP
  - `auth.yourdomain.com` → server IP
  - `grafana.yourdomain.com` → server IP
- Ports 80 and 443 open in firewall

---

## Step 1 — Clone the repository

```bash
git clone https://github.com/your-org/exocortex.git
cd exocortex
```

---

## Step 2 — Create the environment file

```bash
cp .env.production.example .env
nano .env
```

Fill in every `CHANGE_ME_*` value. Use the commands shown in the file to generate
secrets. The file only contains infrastructure secrets. **Do not add AI or Stripe
keys here** — those go in the Admin UI.

---

## Step 3 — Replace YOUR_DOMAIN in Nginx config

```bash
sed -i 's/YOUR_DOMAIN/yourdomain.com/g' infrastructure/nginx/nginx.conf
```

---

## Step 4 — Issue TLS certificates

Nginx needs certs to start HTTPS, but Certbot needs a running web server to pass
the ACME challenge. Solve with Certbot's **standalone** mode (temporarily binds
port 80 itself — no Nginx needed):

```bash
# Make sure nothing is already on port 80
docker compose -f docker-compose.prod.yml run --rm --service-ports certbot \
  certbot certonly --standalone \
    -d yourdomain.com \
    -d auth.yourdomain.com \
    -d grafana.yourdomain.com \
    --email your@email.com \
    --agree-tos \
    --no-eff-email
```

This writes certificates to the `certbot_certs` Docker volume, which Nginx
mounts at `/etc/letsencrypt`. Subsequent renewals (handled by the certbot
service in docker-compose.prod.yml) use the `--webroot` method with Nginx
already running.

---

## Step 5 — Start all services

```bash
docker compose -f docker-compose.prod.yml up -d
```

Watch startup logs (all critical services including arq-worker):

```bash
docker compose -f docker-compose.prod.yml logs -f api arq-worker keycloak
```

Wait until both services are healthy (usually 2–3 minutes):

```bash
docker compose -f docker-compose.prod.yml ps
```

---

## Step 6 — Run database migrations

Migrations run automatically when the `api` container starts (see `command` in
docker-compose.prod.yml). Verify:

```bash
docker compose -f docker-compose.prod.yml exec api alembic current
# Expected: 0014 (head)
```

If you need to run them manually:

```bash
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

---

## Step 7 — Create the first admin user in Keycloak

1. Open `https://auth.yourdomain.com` in your browser
2. Log in with `KEYCLOAK_ADMIN` / `KEYCLOAK_ADMIN_PASSWORD`
3. Switch to the **exocortex** realm
4. Go to **Users** → **Add user**
5. Create your account with email and username
6. Set a password under **Credentials** tab
7. Under **Role Mappings** → assign roles: `user`, `admin`, `system_admin`

---

## Step 8 — Open the web UI and enter API keys

1. Open `https://yourdomain.com` in your browser
2. Log in with your Keycloak account
3. Navigate to **Admin → Settings**
4. Enter your API keys and tokens:
   - **Anthropic API key** — from console.anthropic.com
   - **OpenAI API key** — from platform.openai.com (optional fallback)
   - **Stripe secret key** — from dashboard.stripe.com (optional)
   - **Stripe webhook secret** — from Stripe → Webhooks
   - **Telegram bot token** — from @BotFather (optional)
   - **Google Calendar client ID** — from Google Cloud Console → OAuth 2.0 Clients (optional)
   - **Google Calendar client secret** — same OAuth 2.0 Client (optional)
5. Customise **agent prompts** if desired (defaults work out of the box)
6. Click **Save** on each row — keys are encrypted in the database

The system is now operational. ✓

---

## Daily backups

Set up automated daily backups with cron:

```bash
chmod +x scripts/backup.sh
crontab -e
# Add:
0 3 * * * /path/to/exocortex/scripts/backup.sh >> /var/log/exocortex-backup.log 2>&1
```

Backups are stored in `./backups/` (kept for 14 days).

To restore a backup:

```bash
gunzip -c backups/exocortex_20260101_030000.sql.gz \
  | docker compose -f docker-compose.prod.yml exec -T postgres \
      psql -U exocortex -d exocortex
```

---

## Monitoring

- **Grafana**: `https://grafana.yourdomain.com` — traces, logs, metrics
- **Keycloak Admin**: `https://auth.yourdomain.com`
- **API health**: `https://yourdomain.com/api/v1/health`

---

## Updating to a new version

```bash
git pull
docker compose -f docker-compose.prod.yml build api frontend
docker compose -f docker-compose.prod.yml up -d
# Migrations run automatically on api startup
```

---

## Rollback

```bash
# Tag current state before upgrading
git tag v1.x.x-pre-upgrade

# To roll back:
git checkout v1.x.x-pre-upgrade
docker compose -f docker-compose.prod.yml build api frontend
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec api alembic downgrade -1
```
