# Render 部署教程（task 12.1）

> **零信用卡零成本部署** 后端 FastAPI 到 Render 免费 Web Service。
> 适用：v2 生产环境（推荐 Render Singapore + Bitiful + CF Pages 全套免费）。

## 1. 准备工作

| 资源 | 用途 | 申请 |
|------|------|------|
| GitHub 账号 | 代码托管 | <https://github.com/> |
| Render 账号 | 后端部署 | <https://render.com/>（GitHub 登录） |
| Bitiful 账号 | 图片存储 | <https://www.bitiful.com/>（身份证实名，**无需信用卡**） |

> ⚠️ Render 注册仅需邮箱（推荐 Gmail / 163 / QQ），不要求绑定支付方式。免费层在 `free` plan 下不会自动扣费。

## 2. 上传代码到 GitHub

```bash
cd auto-article-generator
git init
git add .
git commit -m "feat: v2 部署就绪"
gh repo create auto-article-generator --public --source=. --remote=origin --push
# 或手动 push 到已有仓库
```

## 3. 在 Render 创建 Web Service

1. Dashboard → **New +** → **Web Service**
2. 连接 GitHub 仓库 `auto-article-generator`
3. 填写配置：

| 字段 | 值 |
|------|----|
| Name | `auto-article-generator` |
| Region | **Singapore**（国内访问最快） |
| Branch | `main` |
| Root Directory | `backend` |
| Runtime | `Python 3` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `bash ../scripts/render_start.sh` |
| Instance Type | **Free** |
| Health Check Path | `/api/v1/health` |

4. **Advanced** → 添加 **Disk**：
   - Name: `data-disk`
   - Mount Path: `/data`
   - Size: **1 GB**（免费层最大）

## 4. 配置环境变量

在 **Environment** 区域填入（`sync: false` 走 `Secret Files` 等价）：

### 必填
| Key | Value / 说明 |
|-----|--------------|
| `APP_HOST` | `0.0.0.0` |
| `APP_PORT` | `10000`（Render 默认） |
| `DATA_DIR` | `/data`（与磁盘挂载点一致） |
| `LOG_LEVEL` | `INFO` |
| `PYTHON_VERSION` | `3.11.0` |
| `ADMIN_USERNAME` | 自定义 |
| `ADMIN_PASSWORD` | 强密码（**Generate** 自动生成） |
| `SECRET_KEY_FILE` | `/data/.secret_key` |

### 存储后端（推荐 bitiful）
| Key | 说明 |
|-----|------|
| `STORAGE_BACKEND` | `bitiful` |
| `BITIFUL_ENDPOINT` | Bitiful 控制台 → S3 端点（如 `https://bitiful-east.bitiful.net`） |
| `BITIFUL_ACCESS_KEY` | Bitiful AccessKey |
| `BITIFUL_SECRET_KEY` | Bitiful SecretKey |
| `BITIFUL_BUCKET` | 存储桶名 |
| `BITIFUL_PUBLIC_BASE` | 公共读 CDN 域名 |

### AI 渠道
| Key | 说明 |
|-----|------|
| `LLM_PROVIDER` | `deepseek` / `openai` / `tongyi` / `kimi` |
| `LLM_API_KEY` | 厂商 API Key |
| `LLM_BASE_URL` | 厂商网关地址 |
| `LLM_MODEL` | 模型名 |
| `IMAGE_PROVIDER` | `tongyi_volc` |
| `IMAGE_API_KEY` | 通义万相/火山方舟 Key |

### CORS
| Key | 说明 |
|-----|------|
| `CORS_ALLOWED_ORIGINS` | `https://<你的CF Pages域名>.pages.dev`（多个用英文逗号分隔） |

### 构建版本（CI 注入）
| Key | Value |
|-----|-------|
| `BUILD_VERSION` | 手动填 `manual-v1`；CI 自动填 commit SHA |

## 5. 首次部署

1. 点 **Create Web Service** → Render 开始构建（约 3-5 分钟）
2. 观察日志：出现 `启动完成` 即就绪
3. 访问 `https://<your-app>.onrender.com/api/v1/health`：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "status": "healthy",
    "build_version": "manual-v1",
    "storage_backend": "bitiful",
    "uptime_seconds": 12
  }
}
```

> 首启日志会打印生成的 ADMIN_PASSWORD（如留空），**立即保存**。

## 6. 免费层限制与对策

| 限制 | 数值 | 对策 |
|------|------|------|
| 休眠阈值 | 15 分钟无请求 | 配置保活（见 [keep_alive_setup.md](keep_alive_setup.md)） |
| 月小时数 | 750h | 单实例够用（永久在线需付费 plan） |
| 内存 | 512MB | boto3/openai 懒加载已优化 |
| CPU | 共享 | 单实例 5 任务并发够用 |
| 磁盘 | 1GB | 重要数据定时备份到 Bitiful |

## 7. 自动备份到 Bitiful

Render 原生不提供磁盘快照。**推荐方案**：
- 使用 GitHub Actions 每周触发 `scripts/backup_persistent_disk.sh` 备份到 Bitiful
- 或 cron-job.org 注册每周调用备份接口

```yaml
# .github/workflows/backup-data.yml
name: Backup Persistent Disk
on:
  schedule: [{ cron: "0 3 * * 0" }]  # 每周日凌晨3点
jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - run: |
          echo "需在 Render 侧通过 SSH/REST 调用 backup 脚本"
          # 或迁移到 Bitiful 后无需此备份（持久化即对象存储）
```

## 8. 升级到付费 plan（可选）

- **Starter ($7/月)**：无休眠、512MB 内存
- **Standard ($25/月)**：2GB 内存 + 50GB 磁盘
- 升级路径：Dashboard → 选实例 → **Change Plan**

## 9. 常见问题

### Q1: 部署失败 `pip install` 超时
A: 改用 Render 内置 `pip` 镜像，或在 `requirements.txt` 锁定小版本号。

### Q2: 数据库每次重启都丢
A: 确认 `DATA_DIR=/data` 且 Disk 挂载到 `/data`，**切勿挂错路径**。

### Q3: 时区不对
A: Render 实例时区是 UTC，管理后台按 UTC 显示；如需北京时间可在代码中 `datetime.now(timezone(timedelta(hours=8)))`。

### Q4: 端口 8000 vs 10000
A: Render **强制**监听 `0.0.0.0:$PORT`（默认 10000）。本项目 `APP_PORT` 已支持自定义，但建议保持 `10000` 配 `render.yaml`。

## 10. 与 render.yaml 一键部署

仓库根目录自带 `render.yaml`，可在 Render Dashboard 点 **New + → Blueprint**，选仓库即按文件部署。

```bash
# 验证 render.yaml 格式
# Render 官方 CLI: render blueprints launch
```

## 11. 下一步

- 部署前端：[12_cloudflare_pages.md](12_cloudflare_pages.md)
- 配置保活：[keep_alive_setup.md](keep_alive_setup.md)
- 本地开发：[12_local_dev.md](12_local_dev.md)