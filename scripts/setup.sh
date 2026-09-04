#!/bin/bash
# 一键部署脚本（Linux/macOS）
# 用法：./scripts/setup.sh
# 前置：已安装 Python 3.11+ 和 Node.js 18+

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend"
WEB="$ROOT/backend/web"

echo "===== 全自动AI内容生产与发布系统 - 部署脚本 ====="

# 1. 安装后端依赖
echo "[1/3] 安装后端Python依赖..."
pip install -r "$BACKEND/requirements.txt" --quiet
echo "后端依赖安装完成"

# 2. 构建前端
echo "[2/3] 构建前端..."
cd "$WEB"
npm install --silent 2>/dev/null || true
npx vite build
echo "前端构建完成"

# 3. 初始化环境配置
echo "[3/3] 初始化环境配置..."
if [ ! -f "$BACKEND/.env" ]; then
    cp "$ROOT/.env.example" "$BACKEND/.env"
    echo "已从模板创建 .env 文件，请按需修改"
else
    echo ".env 已存在，跳过"
fi

echo ""
echo "===== 部署完成 ====="
echo "启动命令: cd backend && python -m app.main"
echo "访问地址: http://127.0.0.1:8000"
echo ""
echo "如需配置AI服务/平台凭证，请编辑 backend/.env 后启动"