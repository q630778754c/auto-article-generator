# 一键部署脚本（Windows PowerShell）
# 用法：.\scripts\setup.ps1
# 前置：已安装 Python 3.11+ 和 Node.js 18+

$ErrorActionPreference = "Stop"
$ROOT = Resolve-Path "$PSScriptRoot\.."
$BACKEND = "$ROOT\backend"
$WEB = "$ROOT\backend\web"

Write-Host "===== 全自动AI内容生产与发布系统 - 部署脚本 =====" -ForegroundColor Cyan

# 1. 安装后端依赖
Write-Host "[1/3] 安装后端Python依赖..." -ForegroundColor Yellow
$python = if ($env:PYTHON_PATH) { $env:PYTHON_PATH } else { "python" }
& $python -m pip install -r "$BACKEND\requirements.txt" --quiet
if (-not $?) { Write-Host "后端依赖安装失败" -ForegroundColor Red; exit 1 }
Write-Host "后端依赖安装完成" -ForegroundColor Green

# 2. 构建前端
Write-Host "[2/3] 构建前端..." -ForegroundColor Yellow
Push-Location $WEB
npm install --silent 2>$null
npx vite build
Pop-Location
if (-not $?) { Write-Host "前端构建失败" -ForegroundColor Red; exit 1 }
Write-Host "前端构建完成" -ForegroundColor Green

# 3. 初始化环境配置
Write-Host "[3/3] 初始化环境配置..." -ForegroundColor Yellow
$envFile = "$BACKEND\.env"
if (-not (Test-Path $envFile)) {
    Copy-Item "$ROOT\.env.example" $envFile
    Write-Host "已从模板创建 .env 文件，请按需修改" -ForegroundColor Yellow
} else {
    Write-Host ".env 已存在，跳过" -ForegroundColor Green
}

Write-Host ""
Write-Host "===== 部署完成 =====" -ForegroundColor Cyan
Write-Host "启动命令: python -m app.main  (在 backend/ 目录下)" -ForegroundColor White
Write-Host "访问地址: http://127.0.0.1:8000" -ForegroundColor White
Write-Host ""
Write-Host "如需配置AI服务/平台凭证，请编辑 backend/.env 后启动" -ForegroundColor Yellow