# ExoCortex 2.0 — Полная инструкция по развёртыванию
### Пошаговое руководство для начинающих

---

## Содержание

1. [Что вам понадобится](#1-что-вам-понадобится)
2. [Покупка и настройка сервера](#2-покупка-и-настройка-сервера)
3. [Подключение к серверу](#3-подключение-к-серверу)
4. [Настройка сервера — установка программ](#4-настройка-сервера--установка-программ)
5. [Настройка домена (DNS)](#5-настройка-домена-dns)
6. [Загрузка кода на сервер](#6-загрузка-кода-на-сервер)
7. [Генерация секретных ключей](#7-генерация-секретных-ключей)
8. [Заполнение файла настроек .env](#8-заполнение-файла-настроек-env)
9. [Настройка Nginx (домен в конфиге)](#9-настройка-nginx-домен-в-конфиге)
10. [Получение SSL-сертификата (HTTPS)](#10-получение-ssl-сертификата-https)
11. [Запуск всей системы](#11-запуск-всей-системы)
12. [Проверка что всё запустилось](#12-проверка-что-всё-запустилось)
13. [Создание первого пользователя-администратора](#13-создание-первого-пользователя-администратора)
14. [Ввод AI-ключей через Admin UI](#14-ввод-ai-ключей-через-admin-ui)
15. [Настройка Stripe (платежи и подписки)](#15-настройка-stripe-платежи-и-подписки)
16. [Настройка Microsoft Calendar OAuth](#16-настройка-microsoft-calendar-oauth)
17. [Мобильное приложение — сборка и установка](#17-мобильное-приложение--сборка-и-установка)
16. [Настройка автоматического резервного копирования](#16-настройка-автоматического-резервного-копирования)
17. [Мониторинг системы](#17-мониторинг-системы)
18. [Настройка автоматического резервного копирования](#18-настройка-автоматического-резервного-копирования)
19. [Мониторинг системы](#19-мониторинг-системы)
20. [Обновление до новой версии](#20-обновление-до-новой-версии)
21. [Частые проблемы и решения](#21-частые-проблемы-и-решения)

---

## 1. Что вам понадобится

### Минимальные требования к серверу
| Параметр | Минимум | Рекомендуется |
|----------|---------|---------------|
| CPU | 2 ядра | 4 ядра |
| RAM | 4 GB | 8 GB |
| SSD | 40 GB | 80 GB |
| ОС | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |
| Интернет | Любой | 100 Mbit/s |

### Что нужно купить/зарегистрировать заранее
- **VPS-сервер** (Hetzner, DigitalOcean, Timeweb, Reg.ru, Selectel и т.д.)
- **Доменное имя** (например, `myexocortex.com`) — на NameCheap, reg.ru, nic.ru и т.д.
- **Anthropic API Key** (для Claude AI) — регистрация на [console.anthropic.com](https://console.anthropic.com)
- Опционально: OpenAI API Key, Stripe Secret Key, Telegram Bot Token

### Что должно быть на вашем компьютере
- **Windows**: программа PuTTY или Windows Terminal
- **Mac/Linux**: Terminal (встроен)

---

## 2. Покупка и настройка сервера

### Шаг 2.1 — Выбор хостинга

Рекомендуем **Hetzner** (дёшево и надёжно):
- Перейдите на [hetzner.com](https://hetzner.com)
- Cloud → Add Server
- Location: любой (Нюрнберг, Хельсинки и т.д.)
- Image: **Ubuntu 22.04**
- Type: **CX21** (2 CPU, 4 GB RAM) — минимум; **CX31** (2 CPU, 8 GB RAM) — лучше
- Networking: оставьте как есть (Public IPv4)
- SSH Keys: добавьте свой SSH-ключ (или запомните пароль root)
- Нажмите **Create & Buy**

> **Что такое SSH-ключ?** Это пара файлов: публичный (даёте серверу) и приватный (остаётся у вас). Безопаснее пароля. Генерируется командой `ssh-keygen` в терминале.

### Шаг 2.2 — Запишите IP-адрес сервера

После создания сервера вы увидите его IP-адрес, например: `116.202.123.45`
Запишите его — он понадобится.

### Шаг 2.3 — Открытие портов в файрволе

На Hetzner файрвол настраивается через Firewall → Create Firewall:
- Добавьте правила входящего трафика (Inbound):
  - Порт **22** (SSH) — для управления
  - Порт **80** (HTTP) — для Let's Encrypt
  - Порт **443** (HTTPS) — для сайта

---

## 3. Подключение к серверу

### Windows (через PuTTY или Windows Terminal)

**Вариант A — Windows Terminal (рекомендуется, встроен в Win10/11):**
```
Нажмите Win+R → введите cmd → Enter
```

Затем выполните команду (замените IP на ваш):
```
ssh root@116.202.123.45
```

Введите пароль (или подтвердите SSH-ключ). При первом подключении появится вопрос — введите `yes`.

**Вариант B — PuTTY:**
- Скачайте PuTTY с официального сайта [putty.org](https://putty.org)
- В поле Host Name введите IP сервера
- Нажмите Open
- Логин: `root`, затем пароль

### Mac / Linux

Откройте Terminal и выполните:
```bash
ssh root@116.202.123.45
```

---

## 4. Настройка сервера — установка программ

Все команды выполняются на сервере (в SSH-сессии). Копируйте и вставляйте целыми блоками.

### Шаг 4.1 — Обновление системы

```bash
apt update && apt upgrade -y
```

> Это займёт 1-3 минуты. Подождите.

### Шаг 4.2 — Установка Docker

```bash
# Скачиваем и запускаем официальный установщик Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

Проверяем, что Docker установлен:
```bash
docker --version
```
Должно выдать что-то вроде: `Docker version 26.1.3, build ...`

### Шаг 4.3 — Установка дополнительных утилит

```bash
apt install -y git nano curl wget unzip python3 python3-pip
```

### Шаг 4.4 — Проверка Docker Compose

Docker Compose v2 уже входит в Docker. Проверяем:
```bash
docker compose version
```
Должно выдать: `Docker Compose version v2.x.x`

---

## 5. Настройка домена (DNS)

Это нужно сделать в панели управления вашего **регистратора доменов** (там где купили домен).

### Что нужно добавить

Добавьте три A-записи, все указывают на IP вашего сервера:

| Тип | Имя (Host) | Значение (Value) |
|-----|-----------|-----------------|
| A | `@` или `yourdomain.com` | `116.202.123.45` |
| A | `auth` | `116.202.123.45` |
| A | `grafana` | `116.202.123.45` |

> Вместо `116.202.123.45` подставьте реальный IP вашего сервера.
> Вместо `yourdomain.com` — ваше доменное имя.

**Пример в NameCheap:**
- Войдите в личный кабинет → Domain List → Manage
- Advanced DNS → Add New Record
- Добавьте три записи выше

**Пример в reg.ru:**
- Личный кабинет → Домены → ваш домен → DNS-серверы и управление зоной
- Добавить A-запись три раза

### Ожидание распространения DNS

После добавления записей DNS может обновляться до 24 часов. Обычно — 15-60 минут.

Проверить готовность можно командой (выполнять на своём компьютере, не на сервере):
```bash
ping yourdomain.com
```
Если видите IP вашего сервера — DNS работает, можно продолжать.

---

## 6. Загрузка кода на сервер

Выполните на сервере (в SSH):

```bash
# Переходим в домашнюю директорию
cd /opt

# Клонируем репозиторий (замените URL на реальный)
git clone https://github.com/YOUR_USERNAME/exocortex.git

# Входим в папку проекта
cd exocortex
```

> Если репозиторий приватный, потребуется Personal Access Token от GitHub.
> GitHub → Settings → Developer Settings → Personal Access Tokens → Generate new token
> Используйте его вместо пароля при `git clone`.

**Проверьте что файлы на месте:**
```bash
ls
```
Должны увидеть: `backend/  frontend/  mobile/  infrastructure/  docker-compose.yml  docker-compose.prod.yml  DEPLOY.md`

---

## 7. Генерация секретных ключей

Нам нужно создать несколько случайных секретных паролей. Выполните каждую команду и скопируйте результат в блокнот — они понадобятся на следующем шаге.

### Пароль для PostgreSQL
```bash
openssl rand -base64 32
```
Пример вывода: `kH7mN2pQrT8vXzA4bE6fJ9wY1cU5sL3o...`
Запишите как **POSTGRES_PASSWORD**.

### Пароль для Redis
```bash
openssl rand -base64 32
```
Запишите как **REDIS_PASSWORD**.

### Пароль для Keycloak Admin
```bash
openssl rand -base64 32
```
Запишите как **KEYCLOAK_ADMIN_PASSWORD**.

### Секретный ключ шифрования (Fernet) — САМЫЙ ВАЖНЫЙ
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
> Если Python не находит cryptography:
> ```bash
> pip3 install cryptography
> python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
> ```

Пример вывода: `dGhpcyBpcyBhIHRlc3Qga2V5IGZvciBleGFt...=`
Запишите как **EXOCORTEX_SECRET_KEY**.

**ВАЖНО**: Этот ключ шифрует все ваши API-ключи в базе данных. Если потеряете — не сможете расшифровать сохранённые ключи. Храните его в безопасном месте (менеджер паролей).

### Секрет NextAuth
```bash
openssl rand -base64 32
```
Запишите как **NEXTAUTH_SECRET**.

### Пароль Grafana
```bash
openssl rand -base64 16
```
Запишите как **GRAFANA_PASSWORD**.

### Секрет клиента Keycloak для фронтенда
Это значение уже прописано в конфиге Keycloak. Используйте точно такое:
```
CHANGE_ME_frontend_secret_rotate_after_first_login
```
Запишите как **KEYCLOAK_FRONTEND_CLIENT_SECRET**. (Потом поменяем после первого входа.)

---

## 8. Заполнение файла настроек .env

### Шаг 8.1 — Создаём файл из шаблона
```bash
cp .env.production.example .env
```

### Шаг 8.2 — Открываем редактор
```bash
nano .env
```

> Управление в nano:
> - Стрелки — перемещение
> - Ctrl+K — вырезать строку
> - Ctrl+U — вставить строку
> - Ctrl+O, Enter — сохранить
> - Ctrl+X — выйти

### Шаг 8.3 — Заполняем значения

Замените каждое `CHANGE_ME_...` на реальное значение, которое вы записали на шаге 7.

Итоговый файл должен выглядеть примерно так:

```env
DOMAIN=yourdomain.com

POSTGRES_USER=exocortex
POSTGRES_PASSWORD=kH7mN2pQrT8vXzA4bE6fJ9wY1cU5sL3o

REDIS_PASSWORD=mP3qR6tW9xZ2aB5dF8hK1nS4uV7yC0eG

KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=jL4oQ7sT0vX3zA6cE9fI2mN5pR8uW1y

EXOCORTEX_SECRET_KEY=dGhpcyBpcyBhIHRlc3Qga2V5IGZvciBleGFt...=

NEXTAUTH_SECRET=bN5rU8xA1cD4gH7kM0pS3vY6zE9fI2jL

KEYCLOAK_FRONTEND_CLIENT_SECRET=CHANGE_ME_frontend_secret_rotate_after_first_login

GRAFANA_PASSWORD=qW3eR6tY9uI2oP
```

> **ВНИМАНИЕ**: Значения без кавычек. Между `=` и значением нет пробелов.

### Шаг 8.4 — Сохраняем и выходим
Нажмите `Ctrl+O` → `Enter` → `Ctrl+X`

### Шаг 8.5 — Проверяем что всё заполнено
```bash
grep "CHANGE_ME" .env
```
Если вывод пустой — отлично, все значения заменены.
Если что-то нашлось — вернитесь в nano и исправьте.

---

## 9. Настройка Nginx (домен в конфиге)

Nginx нужно знать ваш домен. Заменяем заглушку `YOUR_DOMAIN` на реальное имя:

```bash
sed -i 's/YOUR_DOMAIN/yourdomain.com/g' infrastructure/nginx/nginx.conf
```

> Замените `yourdomain.com` на ваш реальный домен.

**Проверяем что замена прошла:**
```bash
grep "server_name" infrastructure/nginx/nginx.conf
```
Должны увидеть ваш домен в нескольких местах.

---

## 10. Получение SSL-сертификата (HTTPS)

SSL-сертификат (от Let's Encrypt, бесплатно) нужен для работы HTTPS. Есть одна сложность: Nginx нужны сертификаты чтобы запуститься, а сертификаты нужен Nginx чтобы выдать. Решаем это через режим `standalone`.

### Шаг 10.1 — Убеждаемся что порт 80 свободен
```bash
ss -tlnp | grep :80
```
Если порт занят — найдите и остановите процесс:
```bash
systemctl stop apache2 2>/dev/null; systemctl stop nginx 2>/dev/null
```

### Шаг 10.2 — Получаем сертификат

Замените `yourdomain.com` и `your@email.com` на свои значения:

```bash
docker compose -f docker-compose.prod.yml run --rm --service-ports certbot \
  certbot certonly --standalone \
    -d yourdomain.com \
    -d auth.yourdomain.com \
    -d grafana.yourdomain.com \
    --email your@email.com \
    --agree-tos \
    --no-eff-email
```

Команда запустит временный сервер на порту 80, пройдёт проверку Let's Encrypt и сохранит сертификаты.

**Ожидаемый успешный вывод:**
```
Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/yourdomain.com/fullchain.pem
Key is saved at: /etc/letsencrypt/live/yourdomain.com/privkey.pem
```

### Что делать если не получилось

**Ошибка: "Connection refused" или "Timeout"**
- Проверьте что DNS уже обновился: `ping yourdomain.com` (должен ответить IP сервера)
- Проверьте что порт 80 открыт в файрволе

**Ошибка: "Too many requests"**
- Let's Encrypt ограничивает 5 попыток в час. Подождите час и попробуйте снова.

---

## 11. Запуск всей системы

### Шаг 11.1 — Запуск

```bash
docker compose -f docker-compose.prod.yml up -d
```

Эта команда:
1. Скачает все Docker-образы (первый раз ~5-10 минут в зависимости от скорости интернета)
2. Соберёт образы backend и frontend (~3-5 минут)
3. Запустит все контейнеры

### Шаг 11.2 — Наблюдаем за запуском

```bash
docker compose -f docker-compose.prod.yml logs -f api keycloak
```

Нажмите `Ctrl+C` когда надоест следить. Это не останавливает систему.

**Нормальный порядок запуска:**
1. `postgres` стартует первым (~10 секунд)
2. `redis` стартует (~5 секунд)
3. `keycloak` стартует и импортирует realm (~2-3 минуты!)
4. `api` запускает миграции базы и стартует (~1 минута)
5. `frontend` стартует (~30 секунд)
6. `nginx` стартует последним

> **ВАЖНО**: Keycloak стартует медленно. Не паникуйте — 2-3 минуты это нормально.

### Шаг 11.3 — Проверка статуса

```bash
docker compose -f docker-compose.prod.yml ps
```

Ожидаемый вывод (все сервисы `healthy` или `running`):
```
NAME         STATUS
postgres     Up (healthy)
redis        Up (healthy)
keycloak     Up (healthy)
api          Up (healthy)
frontend     Up (healthy)
nginx        Up
certbot      Up
```

Если какой-то сервис в статусе `unhealthy` или `Exit` — см. раздел [Частые проблемы](#19-частые-проблемы-и-решения).

---

## 12. Проверка что всё запустилось

### Проверка 1 — API работает
```bash
curl https://yourdomain.com/api/v1/health
```
Ожидаемый ответ: `{"status": "ok"}`

### Проверка 2 — Сайт открывается
Откройте браузер и зайдите на `https://yourdomain.com`
Должна появиться страница входа ExoCortex.

### Проверка 3 — Keycloak работает
Откройте `https://auth.yourdomain.com`
Должна появиться страница Keycloak.

### Проверка 4 — Миграции применены
```bash
docker compose -f docker-compose.prod.yml exec api alembic current
```
Ожидаемый вывод: `0008 (head)`

---

## 13. Создание первого пользователя-администратора

### Шаг 13.1 — Входим в Keycloak Admin

1. Откройте `https://auth.yourdomain.com`
2. Нажмите **Administration Console**
3. Логин: `admin`
4. Пароль: ваш `KEYCLOAK_ADMIN_PASSWORD` из файла `.env`

### Шаг 13.2 — Переключаемся на realm exocortex

В левом верхнем углу есть выпадающее меню с надписью `master`.
Нажмите на него и выберите **exocortex**.

### Шаг 13.3 — Создаём пользователя

1. В левом меню: **Users** → **Add user**
2. Заполните:
   - **Username**: `admin` (или любое другое)
   - **Email**: ваш email
   - **First name**: ваше имя
   - **Last name**: ваша фамилия
   - **Email verified**: включите переключатель (иначе не войдёте)
3. Нажмите **Create**

### Шаг 13.4 — Устанавливаем пароль

1. Перейдите на вкладку **Credentials**
2. Нажмите **Set password**
3. Введите пароль (придумайте надёжный)
4. **Temporary**: выключите (иначе заставит менять при входе)
5. Нажмите **Save**

### Шаг 13.5 — Назначаем роли

1. Перейдите на вкладку **Role mappings**
2. Нажмите **Assign role**
3. В поиске найдите и выберите все три роли:
   - `user`
   - `admin`
   - `system_admin`
4. Нажмите **Assign**

### Шаг 13.6 — Смена секрета клиента (безопасность)

Поменяем временный секрет `exocortex-frontend` на постоянный:

1. В левом меню: **Clients** → `exocortex-frontend`
2. Перейдите на вкладку **Credentials**
3. Нажмите **Regenerate** рядом с Client secret
4. Скопируйте новый секрет

Теперь обновим `.env` на сервере:
```bash
nano .env
```
Найдите строку `KEYCLOAK_FRONTEND_CLIENT_SECRET=` и вставьте новый секрет.
Сохраните (`Ctrl+O`, Enter, `Ctrl+X`).

Перезапустите frontend:
```bash
docker compose -f docker-compose.prod.yml restart frontend
```

---

## 14. Ввод AI-ключей через Admin UI

### Шаг 14.1 — Входим на сайт

1. Откройте `https://yourdomain.com`
2. Нажмите **Sign in**
3. Введите логин и пароль пользователя, которого создали на шаге 13

### Шаг 14.2 — Переходим в Admin Settings

В меню сайта найдите **Admin → Settings** (доступно только с ролью `system_admin`).

### Шаг 14.3 — Вводим ключи

Последовательно вводите ключи и нажимайте **Save** после каждого:

| Ключ | Где взять |
|------|-----------|
| `anthropic_api_key` | [console.anthropic.com](https://console.anthropic.com) → API Keys |
| `openai_api_key` | [platform.openai.com](https://platform.openai.com) → API Keys (опционально) |
| `stripe_secret_key` | Stripe Dashboard → Developers → API keys → Secret key (sk_live_...) |
| `stripe_webhook_secret` | Stripe → Developers → Webhooks → ваш webhook → Signing secret (whsec_...) |
| `stripe_price_id_pro` | Stripe → Product catalog → Pro план → скопируйте Price ID (price_...) |
| `stripe_price_id_team` | Stripe → Product catalog → Team план → скопируйте Price ID (price_...) |
| `telegram_bot_token` | Telegram → @BotFather → /newbot → токен (опционально) |
| `google_calendar_client_id` | Google Cloud Console → APIs → Credentials → OAuth 2.0 Client ID |
| `google_calendar_client_secret` | Google Cloud Console → тот же Client → секрет |
| `ms_graph_client_id` | Azure Portal → App registrations → Application (client) ID |
| `ms_graph_client_secret` | Azure Portal → App registrations → Certificates & secrets → Value |
| `vapid_private_key` | Генерируется командой (см. ниже) |
| `vapid_public_key` | Генерируется той же командой |

> **Ключи шифруются** в базе данных с помощью вашего `EXOCORTEX_SECRET_KEY`. Никто не увидит их в открытом виде — даже при доступе к базе данных.

### Генерация VAPID-ключей (Web Push)

```bash
docker compose -f docker-compose.prod.yml exec api \
  python -c "
from py_vapid import Vapid
v = Vapid()
v.generate_keys()
print('Private:', v.private_key.private_bytes_raw().hex())
print('Public:', v.public_key.public_bytes_raw().hex())
"
```

Скопируйте оба значения и введите в Admin UI.

### Шаг 14.4 — Проверка работы AI

После ввода Anthropic ключа:
1. Зайдите в раздел **Energy Check-In**
2. Заполните слайдеры и нажмите **Submit**
3. Система должна вернуть ваше energy state
4. Перейдите в **Plan** → нажмите **Generate Plan**
5. AI должен создать план на день

Если всё работает — система полностью готова к использованию!

---

## 15. Настройка Stripe (платежи и подписки)

Stripe используется для оформления Pro и Team подписок. Все ключи вводятся через Admin UI — ничего не добавляйте в `.env`.

### Шаг 15.1 — Создание продуктов и тарифов в Stripe

1. Войдите в [dashboard.stripe.com](https://dashboard.stripe.com)
2. Перейдите в **Product catalog** → **Add product**
3. Создайте два продукта:

**Pro план:**
- Name: `ExoCortex Pro`
- Pricing model: Recurring
- Price: установите нужную сумму (например, 9.99 USD/month)
- После создания скопируйте **Price ID** (начинается с `price_`)

**Team план:**
- Name: `ExoCortex Team`
- Pricing model: Recurring
- Price: (например, 29.99 USD/month)
- Скопируйте **Price ID**

Оба Price ID вводятся в Admin UI как `stripe_price_id_pro` и `stripe_price_id_team`.

### Шаг 15.2 — Настройка Stripe Webhook

Stripe должен уведомлять сервер о событиях подписки (оплата, отмена и т.д.).

1. В Stripe Dashboard: **Developers → Webhooks → Add endpoint**
2. **Endpoint URL:**
   ```
   https://yourdomain.com/api/v1/stripe/webhook
   ```
3. **Events to send** — добавьте следующие события:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
4. Нажмите **Add endpoint**
5. В карточке webhook нажмите **Reveal** рядом с **Signing secret**
6. Скопируйте значение (начинается с `whsec_`)

Введите его в Admin UI как `stripe_webhook_secret`.

> **Почему этот endpoint не имеет rate limit?** Nginx пропускает `/api/v1/stripe/webhook` без ограничений, так как Stripe может быстро повторять запросы при временных сбоях. Безопасность обеспечивается HMAC-подписью (проверяется в FastAPI).

### Шаг 15.3 — Тест подписки

После ввода всех ключей:
1. Войдите на сайт под обычным пользователем (не admin)
2. Перейдите в **Подписка** (левое меню)
3. Нажмите **Перейти на Pro** — должен открыться Stripe Checkout
4. Используйте тестовую карту: `4242 4242 4242 4242`, любой CVV и дата в будущем
5. После оплаты Stripe отправит webhook — тариф должен измениться на Pro

---

## 16. Настройка Microsoft Calendar OAuth

Позволяет пользователям подключать Microsoft (Outlook/Office 365) календари.

### Шаг 16.1 — Регистрация приложения в Azure

1. Войдите на [portal.azure.com](https://portal.azure.com) (нужен Microsoft-аккаунт)
2. Перейдите в **Azure Active Directory → App registrations → New registration**
3. Заполните:
   - **Name**: `ExoCortex Calendar`
   - **Supported account types**: `Accounts in any organizational directory and personal Microsoft accounts`
   - **Redirect URI**: Platform — **Web**, URI:
     ```
     https://yourdomain.com/api/v1/calendar/integrations/microsoft/callback
     ```
4. Нажмите **Register**

### Шаг 16.2 — Скопируйте Client ID

На странице зарегистрированного приложения скопируйте:
- **Application (client) ID** → введите в Admin UI как `ms_graph_client_id`

### Шаг 16.3 — Создание Client Secret

1. В левом меню: **Certificates & secrets → New client secret**
2. Description: `ExoCortex prod`
3. Expires: выберите срок (рекомендуем 24 месяца)
4. Нажмите **Add**
5. Немедленно скопируйте значение из колонки **Value** (оно показывается только один раз!)
6. Введите в Admin UI как `ms_graph_client_secret`

### Шаг 16.4 — Добавление разрешений API

1. **API permissions → Add a permission → Microsoft Graph → Delegated permissions**
2. Найдите и добавьте:
   - `Calendars.Read`
   - `offline_access`
3. Нажмите **Add permissions**
4. Нажмите **Grant admin consent** (если есть права администратора организации)

> Для личных аккаунтов Microsoft (outlook.com, hotmail.com) admin consent не нужен — пользователи дают согласие сами при первом подключении.

### Шаг 16.5 — Проверка

1. Войдите на сайт → **Календари** (левое меню)
2. Нажмите **+ Подключить Microsoft Calendar**
3. Должно открыться окно авторизации Microsoft
4. После авторизации календарь появится в списке подключённых

---

## 17. Мобильное приложение — сборка и установка

Мобильное приложение строится с помощью Expo (React Native).

### Вариант A — Быстрый тест через Expo Go (без сборки)

1. Установите **Expo Go** на телефон (App Store / Google Play)
2. На вашем компьютере (не сервере) установите Node.js: [nodejs.org](https://nodejs.org)
3. Откройте терминал на компьютере и выполните:

```bash
cd путь/к/проекту/mobile
npm install
```

4. Создайте файл `mobile/app.json` и укажите ваш домен в `apiUrl`:
```json
{
  "expo": {
    "extra": {
      "apiUrl": "https://yourdomain.com/api/v1"
    }
  }
}
```

5. Запустите:
```bash
npx expo start
```

6. Отсканируйте QR-код телефоном с установленным Expo Go

> **Ограничение**: Expo Go подходит для тестирования. Для полноценного приложения нужна сборка (Вариант B).

### Вариант B — Полноценная сборка через EAS Build

Требуется аккаунт на [expo.dev](https://expo.dev) (бесплатный тариф доступен).

```bash
# Устанавливаем EAS CLI
npm install -g eas-cli

# Входим в аккаунт Expo
eas login

# Переходим в папку mobile
cd mobile

# Инициализируем EAS проект
eas init

# Собираем APK для Android (внутренний тестовый дистрибутив)
eas build --platform android --profile preview

# Или для iOS (нужен Apple Developer аккаунт)
eas build --platform ios --profile preview
```

Сборка происходит в облаке Expo и занимает ~10-20 минут. По завершении вы получите ссылку для скачивания APK/IPA файла.

### Настройка Keycloak для мобильного приложения

В Keycloak нужно добавить redirect URI для мобильного приложения:

1. `https://auth.yourdomain.com` → Administration Console → exocortex realm
2. **Clients** → `exocortex-mobile`
3. **Settings** → **Valid redirect URIs**
4. Добавьте: `exp://yourdomain.com/*` и `exocortex://auth`
5. Нажмите **Save**

---

## 18. Настройка автоматического резервного копирования

### Шаг 16.1 — Делаем скрипт исполняемым
```bash
chmod +x /opt/exocortex/scripts/backup.sh
```

### Шаг 16.2 — Тестируем резервное копирование
```bash
/opt/exocortex/scripts/backup.sh
```
Проверяем что файл создался:
```bash
ls -lh /opt/exocortex/backups/
```

### Шаг 16.3 — Настраиваем автоматический запуск

```bash
crontab -e
```

Если спросит редактор — выберите `1` (nano).

Добавьте строку в конец файла (резервная копия каждый день в 3:00 ночи):
```
0 3 * * * /opt/exocortex/scripts/backup.sh >> /var/log/exocortex-backup.log 2>&1
```

Сохраните (`Ctrl+O`, Enter, `Ctrl+X`).

### Восстановление из резервной копии

```bash
# Просматриваем доступные копии
ls /opt/exocortex/backups/

# Восстанавливаем (замените имя файла)
gunzip -c /opt/exocortex/backups/exocortex_20260506_030000.sql.gz \
  | docker compose -f /opt/exocortex/docker-compose.prod.yml exec -T postgres \
      psql -U exocortex -d exocortex
```

---

## 19. Мониторинг системы

### Grafana — графики и логи

URL: `https://grafana.yourdomain.com`
- Логин: `admin`
- Пароль: ваш `GRAFANA_PASSWORD`

В Grafana вы увидите:
- Количество запросов к API
- Время ответа
- Ошибки
- Использование ресурсов

### Проверка статуса контейнеров

```bash
docker compose -f /opt/exocortex/docker-compose.prod.yml ps
```

### Просмотр логов конкретного сервиса

```bash
# Логи API (последние 100 строк)
docker compose -f /opt/exocortex/docker-compose.prod.yml logs --tail=100 api

# Логи в реальном времени
docker compose -f /opt/exocortex/docker-compose.prod.yml logs -f api

# Логи Keycloak
docker compose -f /opt/exocortex/docker-compose.prod.yml logs --tail=50 keycloak
```

### Проверка использования ресурсов

```bash
# Общая нагрузка
docker stats --no-stream

# Использование диска
df -h
du -sh /opt/exocortex/backups/
```

### API Health Check

```bash
curl https://yourdomain.com/api/v1/health
```

---

## 20. Обновление до новой версии

После обновления кода новые миграции применяются автоматически при старте контейнера `api`.
Ожидаемый `alembic current` после обновления до последней версии: `0017 (head)`.

```bash
cd /opt/exocortex

# Сохраняем текущий тег (на случай отката)
git tag v1.0.0-pre-upgrade

# Скачиваем новый код
git pull

# Пересобираем изменённые образы
docker compose -f docker-compose.prod.yml build api frontend

# Перезапускаем с новыми образами (миграции запустятся автоматически)
docker compose -f docker-compose.prod.yml up -d
```

### Откат к предыдущей версии

```bash
# Возвращаемся к сохранённому тегу
git checkout v1.0.0-pre-upgrade

# Пересобираем
docker compose -f docker-compose.prod.yml build api frontend
docker compose -f docker-compose.prod.yml up -d

# Откатываем последнюю миграцию базы (если нужно)
docker compose -f docker-compose.prod.yml exec api alembic downgrade -1
```

---

## 21. Частые проблемы и решения

### Проблема: Сервис в статусе `unhealthy`

```bash
# Смотрим логи проблемного сервиса
docker compose -f docker-compose.prod.yml logs api
```

**API unhealthy:**
- Дождитесь пока Keycloak полностью запустится (может занять 3-5 минут)
- Проверьте правильность `EXOCORTEX_SECRET_KEY` в `.env`
- ```bash
  docker compose -f docker-compose.prod.yml restart api
  ```

**Keycloak unhealthy:**
- Keycloak стартует медленно. Подождите 5 минут.
- Проверьте логи: `docker compose -f docker-compose.prod.yml logs keycloak`

**Frontend unhealthy:**
- Должен стартовать только после API. Подождите.
- ```bash
  docker compose -f docker-compose.prod.yml restart frontend
  ```

---

### Проблема: `502 Bad Gateway` в браузере

Nginx запустился, но сервисы за ним ещё не готовы. Подождите 3-5 минут и обновите страницу.

---

### Проблема: Сертификат не получается (`Too many failures`)

DNS ещё не обновился. Проверьте:
```bash
nslookup yourdomain.com
```
Должен вернуть IP вашего сервера. Если нет — подождите ещё.

---

### Проблема: Страница входа есть, но войти не получается

**Ошибка "Invalid client secret":**
- Значение `KEYCLOAK_FRONTEND_CLIENT_SECRET` в `.env` не совпадает с секретом в Keycloak
- Зайдите в Keycloak → Clients → exocortex-frontend → Credentials → скопируйте актуальный секрет
- Вставьте в `.env` и перезапустите: `docker compose -f docker-compose.prod.yml restart frontend`

**Ошибка "Email not verified":**
- Keycloak → Users → ваш пользователь → включите "Email verified"

---

### Проблема: AI не отвечает / ошибка при генерации плана

1. Проверьте что ключ введён правильно в Admin UI (без пробелов, без кавычек)
2. Проверьте баланс на аккаунте Anthropic
3. Посмотрите логи API:
   ```bash
   docker compose -f docker-compose.prod.yml logs --tail=50 api | grep -i error
   ```

---

### Проблема: Нет места на диске

```bash
# Смотрим что занимает место
df -h
du -sh /opt/exocortex/*

# Чистим старые Docker образы и кэш
docker system prune -a --volumes
```

> **ОСТОРОЖНО**: `docker system prune -a --volumes` удаляет неиспользуемые данные. Не используйте если не уверены.

---

### Проблема: Забыл пароль от Keycloak Admin

```bash
docker compose -f docker-compose.prod.yml exec keycloak \
  /opt/keycloak/bin/kc.sh set-password \
  --username admin \
  --new-password НовыйПароль123!
```

---

### Сброс и полная переустановка

**ВНИМАНИЕ: Удаляет все данные!**

```bash
cd /opt/exocortex
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up -d
```

Флаг `-v` удаляет все Docker volumes (базу данных, Redis, Keycloak). Используйте только если хотите начать с чистого листа.

---

## Краткая шпаргалка команд

```bash
# Запуск системы
docker compose -f docker-compose.prod.yml up -d

# Остановка системы
docker compose -f docker-compose.prod.yml down

# Перезапуск одного сервиса
docker compose -f docker-compose.prod.yml restart api

# Статус всех сервисов
docker compose -f docker-compose.prod.yml ps

# Логи (живые)
docker compose -f docker-compose.prod.yml logs -f api

# Логи (последние 50 строк)
docker compose -f docker-compose.prod.yml logs --tail=50 keycloak

# Войти внутрь контейнера
docker compose -f docker-compose.prod.yml exec api bash

# Применить миграции вручную
docker compose -f docker-compose.prod.yml exec api alembic upgrade head

# Текущая версия миграций
docker compose -f docker-compose.prod.yml exec api alembic current

# Сделать бэкап прямо сейчас
/opt/exocortex/scripts/backup.sh

# Использование ресурсов
docker stats --no-stream
```

---

## Архитектура системы (для понимания)

```
Браузер / Телефон
      │
      ▼
  [Nginx :443]  ← HTTPS, SSL termination, rate limiting
      │
      ├── /           → [Frontend :3000]  Next.js 15
      ├── /api/v1/*   → [API :8000]       FastAPI
      ├── auth.*      → [Keycloak :8080]  Auth server
      └── grafana.*   → [Grafana :3000]   Monitoring
           │
           ├── [PostgreSQL :5432]  База данных
           ├── [Redis :6379]       Кэш и очереди
           ├── [Loki]              Хранение логов
           └── [Tempo]             Трассировки
```

**Порядок запуска** (Docker управляет автоматически):
```
PostgreSQL → Redis → Keycloak → API (migrations) → Frontend → Nginx
```

---

*Если что-то не работает — проверьте логи командой `docker compose -f docker-compose.prod.yml logs имя_сервиса` и поищите текст ошибки. Большинство проблем решаются терпением (Keycloak медленный) или проверкой значений в `.env`.*
