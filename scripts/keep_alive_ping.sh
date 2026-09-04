#!/usr/bin/env bash
# Render 免费实例保活脚本（task 11.7）
# 用法：
#   keep_alive_ping.sh [URL] [INTERVAL_SEC]
# 默认每 14 分钟 GET /health（Render 免费实例 15 分钟无请求会休眠）
# 可被 cron-job.org / GitHub Actions / 本地 cron 调用

set -e

BASE_URL="${1:-${APP_PUBLIC_URL:-https://auto-article-generator.onrender.com}}"
INTERVAL="${2:-840}"

HEALTH_PATH="${HEALTH_PATH:-/api/v1/health}"
URL="${BASE_URL%/}${HEALTH_PATH}"

echo "[keep-alive] url=${URL} interval_sec=${INTERVAL}"

while true; do
    TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    HTTP_CODE=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 30 "${URL}" || echo "000")
    if [[ "${HTTP_CODE}" =~ ^2 ]]; then
        echo "[${TS}] OK ${HTTP_CODE}"
    else
        echo "[${TS}] FAIL ${HTTP_CODE}"
    fi
    sleep "${INTERVAL}"
done