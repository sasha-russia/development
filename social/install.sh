#!/usr/bin/env bash
# Install or update the monitoring system on an Ubuntu server. Run as root:
#   curl -fsSL https://raw.githubusercontent.com/sasha-russia/development/main/social/install.sh | bash
# Re-running it updates the code and restarts the app; data and .env are kept.
set -euo pipefail

REPO="${REPO:-https://github.com/sasha-russia/development.git}"
BRANCH="${BRANCH:-main}"
DIR="${DIR:-/opt/social-monitor}"
DOMAIN="${DOMAIN:-social.a-platonov.ru}"

if ! command -v docker >/dev/null 2>&1; then
  echo "== Устанавливаю Docker"
  curl -fsSL https://get.docker.com | sh
fi
command -v git >/dev/null 2>&1 || apt-get install -y git

echo "== Код: $REPO ($BRANCH) → $DIR"
if [ -d "$DIR/.git" ]; then
  git -C "$DIR" fetch --depth 1 origin "$BRANCH"
  git -C "$DIR" checkout -B "$BRANCH" FETCH_HEAD
else
  git clone --depth 1 --branch "$BRANCH" "$REPO" "$DIR"
fi
cd "$DIR/social"
mkdir -p data

if [ ! -f .env ]; then
  password="$(openssl rand -base64 12 | tr -d '/+=')"
  sed -e "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=$password|" \
      -e "s|^SECRET_KEY=.*|SECRET_KEY=$(openssl rand -hex 32)|" \
      -e "s|^DOMAIN=.*|DOMAIN=$DOMAIN|" \
      -e "s|^BASE_URL=.*|BASE_URL=https://$DOMAIN|" .env.example > .env
  chmod 600 .env
  echo
  echo "   Создан $DIR/social/.env. Вход: admin / $password"
  echo "   Впишите в .env ключи Telegram, VK, Claude и MAX и запустите скрипт ещё раз."
  echo
fi

# Caddy needs ports 80 and 443. If something else (nginx, a VPN) holds them, run the app alone.
busy=""
for port in 80 443; do
  if ss -ltnH "sport = :$port" | grep -q . && ! docker ps --format '{{.Names}} {{.Ports}}' | grep -q "caddy.*:$port->"; then
    busy="$busy $port"
  fi
done

ip="$(curl -fsS4 https://api.ipify.org || true)"
resolved="$(getent ahostsv4 "$DOMAIN" | awk 'NR==1{print $1}' || true)"
if [ -n "$ip" ] && [ "$resolved" != "$ip" ]; then
  echo "!! $DOMAIN указывает на '${resolved:-ничего}', а адрес сервера $ip."
  echo "   В Cloudflare добавьте A-запись: social → $ip (Proxy status: DNS only), затем запустите скрипт ещё раз."
fi

if [ -z "$busy" ]; then
  docker compose --profile caddy up -d --build
  echo "== Готово: https://$DOMAIN"
else
  docker compose up -d --build app
  echo "!! Порты$busy заняты другим сервисом, поэтому Caddy не запущен."
  echo "   Приложение слушает 127.0.0.1:8000. Добавьте в свой веб-сервер проксирование $DOMAIN → http://127.0.0.1:8000"
fi
docker image prune -f >/dev/null
