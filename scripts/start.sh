#!/bin/bash
# 启动脚本（Linux/macOS）
# 用法：./scripts/start.sh

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend"

echo "启动全自动AI内容生产与发布系统..."
echo "访问地址: http://127.0.0.1:8000"
echo "按 Ctrl+C 停止"
echo ""

cd "$BACKEND"
python -m app.main