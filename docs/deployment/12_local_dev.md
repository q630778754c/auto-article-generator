# 本地开发环境搭建（task 12.2）

> 适合：日常开发、调试、跑测试。

## 1. 前置依赖

| 工具 | 版本 | 安装 |
|------|------|------|
| Python | 3.11+ | <https://www.python.org/downloads/> |
| Node.js | 20+ | <https://nodejs.org/> |
| Git | 2.30+ | <https://git-scm.com/> |

## 2. 克隆与初始化

```bash
git clone https://github.com/<your-org>/auto-article-generator.git
cd auto-article-generator
```

### Windows 一键
```powershell
.\scripts\setup.ps1
```

### Linux / macOS
```bash
bash scripts/setup.sh
```

> 脚本会：建 Python 虚拟环境 `.venv` → 装依赖 → 复制 `.env.example` 为 `.env` → 创建 `data/` 目录。

## 3. 启动后端

```bash
# Windows
.\scripts\start.ps1

# Linux / macOS
bash scripts/start.sh

# 等价手动
cd backend
py -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

启动成功后：
- API: <http://127.0.0.1:8000/api/v1/health>
- Swagger: <http://127.0.0.1:8000/docs>
- 前端首页: <http://127.0.0.1:8000/>

## 4. 启动前端开发服务器（可选）

如果想独立开发前端（HMR 热更）：

```bash
cd backend/web
npm install
npm run dev
# Vite 启动在 5173
# /api 与 /static 通过 Vite proxy 转发到 127.0.0.1:8000
```

## 5. 跑测试

```bash
cd backend
py -m pytest                    # 全部
py -m pytest tests/core/        # 仅核心
py -m pytest -k storage         # 仅 storage 相关
py -m pytest --cov=app          # 覆盖率
```

前端构建配置测试：
```bash
node tests/build-config.test.mjs
```

## 6. 调试 .env

`backend/.env` 关键字段：

```ini
DATA_DIR=../data          # 相对 backend/ 的路径
STORAGE_BACKEND=local     # 开发期默认 local
LOG_LEVEL=DEBUG           # 开发期 DEBUG
ADMIN_PASSWORD=           # 留空首启自动生成
```

> 修改 `.env` 后需重启后端进程（pydantic-settings 不热加载）。

## 7. 数据目录结构

```
data/
├── app.db              # SQLite 主库
├── app.db-wal          # WAL 日志
├── .secret_key         # Fernet 主密钥（**勿提交**）
├── logs/
│   └── app.log
└── images/             # local 模式下的图片
```

## 8. 重置开发环境

```bash
# 停止所有进程
# 删除数据
rm -rf data/

# 重新初始化
bash scripts/setup.sh
```

## 9. 常见开发问题

### Q: pip install 报 Microsoft Visual C++ 14.0 required
A: 仅 Windows 编译某些包时需要，本项目依赖均为预编译 wheel，无需 C++。

### Q: 端口 8000 占用
A: `APP_PORT=8001` 改 `.env` 重启。

### Q: 启动报 "no such table: user_account"
A: ORM 模型未就绪时会用 `_run_migrations()` 占位建表；如失败执行：
```bash
cd backend
py -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"
```

### Q: Bitiful 测试不通过
A: 开发期不连真实 Bitiful；测试用 LocalStorageAdapter 即可。如必须联调：
```bash
export STORAGE_BACKEND=bitiful
export BITIFUL_ENDPOINT=...
export BITIFUL_ACCESS_KEY=...
# ...
```

## 10. IDE 配置（VS Code）

`.vscode/settings.json` 推荐：

```json
{
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "ms-python.black-formatter"
  }
}
```

`.vscode/launch.json`：

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload", "--port", "8000"],
      "cwd": "${workspaceFolder}/backend",
      "envFile": "${workspaceFolder}/backend/.env"
    }
  ]
}
```