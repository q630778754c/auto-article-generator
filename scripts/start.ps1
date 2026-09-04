# 启动脚本（Windows PowerShell）
# 用法：.\scripts\start.ps1

$ErrorActionPreference = "Stop"
$ROOT = Resolve-Path "$PSScriptRoot\.."
$BACKEND = "$ROOT\backend"

$python = if ($env:PYTHON_PATH) { $env:PYTHON_PATH } else { "python" }

Write-Host "启动全自动AI内容生产与发布系统..." -ForegroundColor Cyan
Write-Host "访问地址: http://127.0.0.1:8000" -ForegroundColor Yellow
Write-Host "按 Ctrl+C 停止" -ForegroundColor Gray
Write-Host ""

& $python -m app.main