# ExoCortex 2.0 — Complete Deployment Checklist

> Zero-to-production. Every step is actionable; every command is exact.
> Estimated time: 45–90 minutes on a clean VPS.

---

## Phase 0 — Server Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 GB | 8 GB |
| Disk | 40 GB SSD | 80 GB SSD |
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |
| Ports open | 80, 443 | 80, 443 (+ 22 for SSH) |

```bash
# Install Docker + Compose v2
curl -fsSL https://get.docker.com | bash
docker compose version   # must be 2.x
```

---

## Phase 1 — DNS Records

In your DNS provider, create the following **A records** pointing to your VPS IP:

| Hostname | Type | Value |
|----------|------|-------|
| `yourdomain.com` | A | `VPS_IP` |
| `auth.yourdomain.com` | A | `VPS_IP` |
| `grafana.yourdomain.com` | A | `VPS_IP` |

Wait for propagation before continuing (`dig yourdomain.com +short` must return the IP).

---

## Phase 2 — Repository & Secrets Setup

```bash
# Clone the repo
git clone https://github.com/YOUR_ORG/exocortex.git /opt/exocortex
cd /opt/exocortex

# Create .env from template
cp .env.production.example .env
```

Open `.env` and fill in every `CHANGE_ME` value:

### 2.1 Generate all secrets

```bash
# EXOCORTEX_SECRET_KEY — Fernet key (encrypts Admin UI secrets in DB)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# NEXTAUTH_SECRET
openssl rand -base64 32

# POSTGRES_PASSWORD
openssl rand -base64 32

# REDIS_PASSWORD
openssl rand -base64 32

# KEYCLOAK_ADMIN_PASSWORD
openssl rand -base64 32

# GRAFANA_PASSWORD
openssl rand -base64 16
```

### 2.2 Fill .env

```ini
DOMAIN=yourdomain.com
BASE_URL=https://yourdomain.com

POSTGRES_USER=exocortex
POSTGRES_PASSWORD=<generated>

REDIS_PASSWORD=<generated>

KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=<generated>

EXOCORTEX_SECRET_KEY=<fernet key>
NEXTAUTH_SECRET=<generated>

# From Keycloak realm-export.json → clients → exocortex-frontend → secret
# Leave as-is for first deploy; rotate after first login (see Phase 6)
KEYCLOAK_FRONTEND_CLIENT_SECRET=exocortex-frontend-secret-change-me

GRAFANA_PASSWORD=<generated>
SENTRY_DSN=   # leave blank to disable

# SMTP — optional bootstrap; prefer Admin UI after first launch
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
SMTP_USE_TLS=true
```

> **Do NOT put AI, Stripe, or Telegram keys here.** Enter them in Admin UI after first launch.

---

## Phase 3 — TLS Certificate (Let's Encrypt)

Run this **before** starting docker-compose (certbot needs port 80 free):

```bash
apt install -y certbot

certbot certonly --standalone \
  -d yourdomain.com \
  -d auth.yourdomain.com \
  -d grafana.yourdomain.com \
  --email you@yourdomain.com \
  --agree-tos --non-interactive

# Verify certs are present
ls /etc/letsencrypt/live/yourdomain.com/
# Must show: cert.pem  chain.pem  fullchain.pem  privkey.pem
```

---

## Phase 4 — First Launch

```bash
cd /opt/exocortex

# Build images and start all services
docker compose -f docker-compose.prod.yml up -d --build

# Watch startup (Keycloak takes ~90 seconds on first run)
docker compose -f docker-compose.prod.yml logs -f --tail=50
```

### 4.1 Health checks

```bash
# All services must be healthy
docker compose -f docker-compose.prod.yml ps

# API
curl -sf https://yourdomain.com/api/v1/health | python3 -m json.tool
# Expected: {"status": "ok", "db": "ok", "redis": "ok"}

# Keycloak
curl -sf https://auth.yourdomain.com/health/ready
# Expected: {"status": "UP"}

# Frontend
curl -sf https://yourdomain.com/ -o /dev/null -w "%{http_code}"
# Expected: 200
```

### 4.2 Database migrations

Migrations run automatically on API startup (`alembic upgrade head`). Verify:

```bash
docker compose -f docker-compose.prod.yml logs api | grep "Running upgrade"
# Expected output should show 0001 → 0002 → ... → 0018
```

---

## Phase 5 — Keycloak Configuration

### 5.1 Create first admin user

1. Open `https://auth.yourdomain.com/admin`
2. Login: `admin` / `KEYCLOAK_ADMIN_PASSWORD` from .env
3. Select realm: **exocortex** (top-left dropdown)
4. **Users** → **Add user**:
   - Username: `admin@yourdomain.com`
   - Email: your real email
   - Email Verified: ON
5. **Credentials** tab → **Set Password** (make it strong, disable "Temporary")
6. **Role Mappings** → **Client Roles** → `exocortex-api` → assign `admin` role

### 5.2 Rotate Keycloak frontend client secret

1. **Clients** → `exocortex-frontend` → **Credentials** tab
2. Click **Regenerate Secret** → copy the new value
3. Update `.env`: `KEYCLOAK_FRONTEND_CLIENT_SECRET=<new_value>`
4. Restart frontend:
   ```bash
   docker compose -f docker-compose.prod.yml restart frontend
   ```

### 5.3 Set SMTP in Keycloak (for password-reset emails)

1. **Realm Settings** → **Email** tab
2. Fill host, port, credentials (same as your SMTP provider)
3. **Test connection**

---

## Phase 6 — Admin UI: Enter All Keys

Open `https://yourdomain.com/admin/settings` (login as the admin user created in Phase 5).

Enter keys in this order. Each value is stored encrypted in DB — never touches `.env`.

### 6.1 AI Keys (at least one required)

| Key | Where to get |
|-----|-------------|
| `anthropic_api_key` | console.anthropic.com → API Keys |
| `openai_api_key` | platform.openai.com → API Keys (optional fallback) |
| `ollama_base_url` | Leave default `http://localhost:11434` or set remote Ollama URL |

### 6.2 Stripe (skip if not using billing)

1. Go to `dashboard.stripe.com`
2. Get **Secret Key** (Developers → API Keys → Secret key)
3. Create two Products with monthly Prices → copy both `price_XXX` IDs
4. Register webhook (see Phase 7)

| Key | Value |
|-----|-------|
| `stripe_secret_key` | `sk_live_...` |
| `stripe_webhook_secret` | `whsec_...` (from Phase 7) |
| `stripe_price_id_pro` | `price_XXX` |
| `stripe_price_id_team` | `price_YYY` |
| `stripe_charity_account` | Stripe account ID for forfeited deposits (optional) |

### 6.3 Email / SMTP

| Key | Example |
|-----|---------|
| `smtp_host` | `smtp.gmail.com` |
| `smtp_port` | `587` |
| `smtp_username` | `noreply@yourdomain.com` |
| `smtp_password` | App password (not account password) |
| `smtp_from_email` | `noreply@yourdomain.com` |
| `smtp_use_tls` | `true` |

> **Gmail**: use App Passwords (Google Account → Security → 2FA → App Passwords).
> **Resend/Postmark/Brevo**: check their SMTP credentials page.

### 6.4 Telegram (skip if not using bot)

| Key | Where to get |
|-----|-------------|
| `telegram_bot_token` | @BotFather → /newbot |
| `telegram_webhook_url` | `https://yourdomain.com` |

Register webhook after entering token (see Phase 8).

### 6.5 Calendar Integrations (skip if not using)

**Google Calendar:**
1. console.cloud.google.com → New Project → Enable "Google Calendar API"
2. Credentials → OAuth 2.0 Client ID (Web application)
3. Authorized redirect URI: `https://yourdomain.com/api/v1/calendar/google/callback`
4. Download credentials → enter `client_id` and `client_secret`

**Microsoft Graph:**
1. portal.azure.com → Azure Active Directory → App registrations → New
2. Redirect URI: `https://yourdomain.com/api/v1/calendar/microsoft/callback`
3. Certificates & secrets → New client secret
4. API permissions → Microsoft Graph → Calendars.ReadWrite (delegated)

### 6.6 Web Push VAPID Keys (for browser notifications)

```bash
# Generate once on any machine with Python
pip install py-vapid
python3 -c "
from py_vapid import Vapid
v = Vapid()
v.generate_keys()
print('PRIVATE:', v.private_key)
print('PUBLIC:', v.public_key)
"
```

| Key | Value |
|-----|-------|
| `vapid_private_key` | Generated private key |
| `vapid_public_key` | Generated public key |
| `vapid_contact_email` | `mailto:you@yourdomain.com` |

---

## Phase 7 — Stripe Webhook Registration

```bash
# In Stripe Dashboard → Developers → Webhooks → Add endpoint
# URL: https://yourdomain.com/api/v1/stripe/webhook
# Events to listen for:
#   customer.subscription.created
#   customer.subscription.updated
#   customer.subscription.deleted
#   invoice.payment_succeeded
#   invoice.payment_failed
#   checkout.session.completed
```

Copy the **Signing secret** (`whsec_...`) → enter as `stripe_webhook_secret` in Admin UI.

**Test the webhook:**
```bash
# Install Stripe CLI
stripe listen --forward-to https://yourdomain.com/api/v1/stripe/webhook
stripe trigger checkout.session.completed
# Check: docker compose logs api | grep "stripe"
```

---

## Phase 8 — Telegram Webhook Registration

After entering `telegram_bot_token` in Admin UI, register the webhook:

```bash
TOKEN="<your_bot_token>"
DOMAIN="yourdomain.com"

curl -s "https://api.telegram.org/bot${TOKEN}/setWebhook" \
  -d "url=https://${DOMAIN}/api/v1/telegram/webhook" \
  -d "allowed_updates=[\"message\",\"callback_query\"]"

# Verify
curl -s "https://api.telegram.org/bot${TOKEN}/getWebhookInfo" | python3 -m json.tool
# "url" should be your domain
# "pending_update_count" should be 0 (or low)
```

---

## Phase 9 — Smoke Tests

Run these manually after completing all configuration:

```bash
# 1. API health (DB + Redis)
curl -sf https://yourdomain.com/api/v1/health

# 2. Login flow
# Open browser → https://yourdomain.com → click Login
# Should redirect to auth.yourdomain.com → login → redirect back to /dashboard

# 3. AI chat works
# Dashboard → open chat → send "hello" → should get a response from Claude

# 4. Team invitation
# Settings → Team → enter an email → click Invite
# Check that the invited email received the invitation
# (or check docker logs api for SMTP errors)

# 5. Background worker alive
docker compose -f docker-compose.prod.yml logs arq-worker | tail -20
# Should show "Starting worker..." and cron job registrations

# 6. iCal sync running (wait up to 30 min or check logs)
docker compose -f docker-compose.prod.yml logs arq-worker | grep ical
```

---

## Phase 10 — Grafana Dashboard Setup

Open `https://grafana.yourdomain.com`
Login: `admin` / `GRAFANA_PASSWORD` from .env

1. **Connections** → **Data sources** → verify Loki and Tempo are connected (green checkmark)
2. **Dashboards** → **Import** → paste dashboard IDs:
   - FastAPI: `17175`
   - PostgreSQL: `9628`
   - Redis: `763`
3. Set up alert: **Alerting** → **Alert rules** → create rule for API error rate > 1%

---

## Phase 11 — Backup Setup

```bash
# Create backup script at /opt/exocortex/scripts/backup.sh
cat > /opt/exocortex/scripts/backup.sh << 'EOF'
#!/bin/bash
set -e
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/exocortex"
mkdir -p "$BACKUP_DIR"

cd /opt/exocortex
source .env

# PostgreSQL full dump
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U "$POSTGRES_USER" exocortex | \
  gzip > "$BACKUP_DIR/postgres_${TIMESTAMP}.sql.gz"

# Keep 14 days of backups
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +14 -delete

echo "Backup complete: $BACKUP_DIR/postgres_${TIMESTAMP}.sql.gz"
EOF

chmod +x /opt/exocortex/scripts/backup.sh

# Schedule daily at 3am
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/exocortex/scripts/backup.sh >> /var/log/exocortex-backup.log 2>&1") | crontab -
```

**Test restore:**
```bash
# Verify backup is valid
gzip -t /backups/exocortex/postgres_*.sql.gz && echo "OK"
```

---

## Phase 12 — Update Procedure

```bash
cd /opt/exocortex
git pull origin main

# Rebuild changed services (migrations run automatically on api start)
docker compose -f docker-compose.prod.yml up -d --build api arq-worker frontend

# Verify no errors
docker compose -f docker-compose.prod.yml logs --tail=30 api
docker compose -f docker-compose.prod.yml ps
```

---

## Rollback

```bash
# If update breaks something
git log --oneline -10   # find previous good commit SHA
git checkout <SHA>
docker compose -f docker-compose.prod.yml up -d --build api arq-worker frontend
```

---

## Quick Reference: Common Issues

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `502 Bad Gateway` from nginx | API not healthy yet | Wait 60s; check `docker logs api` |
| Keycloak login loop | Wrong `KEYCLOAK_FRONTEND_CLIENT_SECRET` | Rotate in Keycloak UI + update .env + restart frontend |
| `cryptography.fernet.InvalidToken` in logs | `EXOCORTEX_SECRET_KEY` changed after data written | Never change this key; use same key that encrypted data |
| AI returns "Model unavailable" | API key not set in Admin UI | Admin UI → AI Keys → enter anthropic_api_key |
| Emails not sent | SMTP not configured | Admin UI → Email/SMTP → fill all fields; check `docker logs api` for SMTP errors |
| Stripe webhook 400 | Wrong `stripe_webhook_secret` | Admin UI → Stripe → update stripe_webhook_secret |
| `alembic upgrade head` fails | Migration error | `docker logs api` → fix migration → restart |
| iCal sync not running | arq-worker unhealthy | `docker restart arq-worker`; check Redis connection |

---

## Security Hardening (Post-Launch)

```bash
# Firewall — allow only 80, 443, 22
ufw allow 22
ufw allow 80
ufw allow 443
ufw enable

# Fail2ban for SSH brute force
apt install -y fail2ban
systemctl enable fail2ban

# Auto security updates
apt install -y unattended-upgrades
dpkg-reconfigure --priority=low unattended-upgrades
```

---

## Deployment Checklist Summary

- [ ] DNS A records created (main, auth, grafana subdomains)
- [ ] Docker 24+ installed
- [ ] `.env` filled — all `CHANGE_ME` replaced, no AI/Stripe/Telegram keys
- [ ] TLS certificates obtained (Let's Encrypt)
- [ ] `docker compose up -d --build` — all services healthy
- [ ] Migrations applied (0001→0018)
- [ ] Keycloak admin user created + `admin` role assigned
- [ ] Keycloak frontend client secret rotated
- [ ] Admin UI: `anthropic_api_key` entered (minimum for AI to work)
- [ ] Admin UI: Stripe keys entered + webhook registered
- [ ] Admin UI: SMTP configured + test email sent
- [ ] Admin UI: Telegram bot token entered + webhook registered (if using)
- [ ] Admin UI: Calendar OAuth credentials entered (if using)
- [ ] Admin UI: VAPID keys entered (if using push notifications)
- [ ] Smoke tests passed (AI chat, team invite, login flow)
- [ ] Grafana dashboards imported
- [ ] Daily DB backup scheduled and tested
- [ ] Firewall + fail2ban configured
