#!/bin/bash
# Деплой на продакшн сервер
# Использование: ./deploy.sh

SERVER="root@185.246.220.130"
REMOTE_DIR="/root/app"

echo "==> Копируем файлы на сервер..."
tar \
  --exclude='.venv' \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  --exclude='.idea' \
  --exclude='.vscode' \
  --exclude='.claude' \
  --exclude='ООО_*.docx' \
  -czf /tmp/app.tar.gz . && \
scp /tmp/app.tar.gz $SERVER:/root/app.tar.gz && \
rm /tmp/app.tar.gz

echo "==> Копируем .env..."
scp .env $SERVER:$REMOTE_DIR/.env

echo "==> Распаковываем и поднимаем..."
ssh $SERVER "
  tar -xzf /root/app.tar.gz -C $REMOTE_DIR && \
  rm /root/app.tar.gz && \
  cd $REMOTE_DIR && \
  docker compose -f docker-compose.prod.yml up --build -d && \
  echo '==> DONE'
"
