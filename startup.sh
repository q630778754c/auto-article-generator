#!/bin/bash
LOG=/tmp/deploy.log
echo "=== Starting deployment ===" > $LOG

cd /workspaces/auto-article-generator/backend
echo "Installing deps..." >> $LOG
pip install -r requirements.txt >> $LOG 2>&1

mkdir -p /tmp/data/images /tmp/data/logs

export DATA_DIR=/tmp/data
export STORAGE_BACKEND=local
export APP_HOST=0.0.0.0
export APP_PORT=8000
export LOG_LEVEL=INFO
export ADMIN_USERNAME=admin
export LLM_PROVIDER=openai
export LLM_BASE_URL=https://integrate.api.nvidia.com/v1
export LLM_MODEL=meta/llama-3.1-405b-instruct
export BUILD_VERSION=codespace-v1

echo "Starting server..." >> $LOG
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/server.log 2>&1 &
sleep 5

echo "Installing localtunnel..." >> $LOG
npm install -g localtunnel >> $LOG 2>&1

echo "Starting tunnel..." >> $LOG
lt --port 8000 --subdomain aag-api > /tmp/tunnel.log 2>&1 &
sleep 10

TUNNEL_URL=$(grep -oP 'https://[a-z0-9-]+\.loca\.lt' /tmp/tunnel.log | head -1)
echo "Tunnel URL: $TUNNEL_URL" >> $LOG

if [ -n "$TUNNEL_URL" ]; then
    curl -s -X PATCH \
        -H "Authorization: token $GH_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"description\":\"AAG Tunnel URL\",\"files\":{\"url.txt\":{\"content\":\"$TUNNEL_URL\"}}}" \
        https://api.github.com/gists/aag-tunnel-url >> $LOG 2>&1
    if [ $? -ne 0 ]; then
        curl -s -X POST \
            -H "Authorization: token $GH_TOKEN" \
            -H "Content-Type: application/json" \
            -d "{\"description\":\"AAG Tunnel URL\",\"public\":true,\"files\":{\"url.txt\":{\"content\":\"$TUNNEL_URL\"}}}" \
            https://api.github.com/gists >> $LOG 2>&1
    fi
    echo "URL posted to Gist" >> $LOG
fi

echo "=== Done ===" >> $LOG
