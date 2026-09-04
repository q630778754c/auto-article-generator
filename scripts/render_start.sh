# Render Web Service 启动脚本
# 适配 Render 平台的环境约束：/data挂载点为Persistent Disk

set -e

echo "=== 启动全自动AI内容生产与发布系统 (Render) ==="
echo "DATA_DIR=${DATA_DIR:-/data}"
echo "APP_PORT=${APP_PORT:-10000}"

cd "$(dirname "$0")/../backend"

exec python -m app.main