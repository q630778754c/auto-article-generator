# 运维手册（task 12.3）

> Render + Cloudflare Pages + Bitiful 全套免费部署的日常运维 SOP。

## 1. 部署后必查清单

部署完成立即验证：

- [ ] `GET /api/v1/health` 返回 `build_version` / `storage_backend` / `uptime_seconds`
- [ ] 浏览器访问首页能登录（admin / 首次打印的密码）
- [ ] 触发一次"采集-改写-审核-配图-发布"全流程跑通
- [ ] 检查 Bitiful 桶里出现新上传图片
- [ ] CF Pages `_redirects` 生效：浏览器访问 `<pages>/api/v1/health` 看到后端响应

## 2. 监控

### 2.1 业务监控（应用层）

`/api/v1/health` 已含构建版本与运行时长，**自建监控**：
- cron-job.org 配置每 14 分钟 GET 一次（兼保活）
- UptimeRobot 配置 5 分钟监控 + 邮件告警

### 2.2 Render 平台监控

Dashboard → 选 Web Service → **Metrics** 标签查看：
- CPU / Memory / Request count
- Free instance 配额：本月小时数

### 2.3 告警渠道

通过环境变量启用（已支持）：
- 企业微信机器人：`WECHAT_ROBOT_WEBHOOK=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx`
- 邮件：`SMTP_*` 系列

后台管理 → 系统设置 → 告警：可单独配运行层 `alert.*` 配置项。

## 3. 备份与恢复

### 3.1 备份策略

| 数据 | 频率 | 方案 |
|------|------|------|
| `data/app.db` | 每日 03:00 | 备份到 Bitiful `backups/` |
| `data/images/` | 已迁 Bitiful，**无需备份** | - |
| `.secret_key` | **手动**异地多份 | 1Password / Bitiful `secrets/` |
| `backend/.env` | 手动 | 1Password |

### 3.2 自动备份脚本

`scripts/backup_persistent_disk.sh` 已支持：

```bash
DATA_DIR=/data BITIFUL_ENDPOINT=... BITIFUL_ACCESS_KEY=... \
  bash scripts/backup_persistent_disk.sh
```

定时任务示例（Render Cron Job / 外部 cron）：

```cron
0 3 * * * /opt/render/project/src/scripts/backup_persistent_disk.sh
```

### 3.3 恢复流程

1. 停止 Render 实例（或切到只读模式）
2. 从 Bitiful 下载最近备份：
   ```bash
   aws s3 cp s3://<bucket>/backups/auto-article-backup-20260901-030000.tar.gz . \
     --endpoint-url <BITIFUL_ENDPOINT>
   ```
3. 解压覆盖 `data/`：
   ```bash
   tar xzf auto-article-backup-*.tar.gz -C /data
   ```
4. 重启 Render 实例
5. 验证 `/health` 与登录

## 4. 升级与回滚

### 4.1 升级流程

1. 本地测试通过 → push 到 `main`
2. Render 自动触发部署（约 3-5 分钟）
3. 观察日志 → 验证 `/health`
4. CF Pages 自动构建前端（如前端有变更）

### 4.2 紧急回滚

Render Dashboard → Deploys → 选历史版本 → **Rollback to this deploy**（秒级）。

前端：CF Pages Dashboard → Deployments → **Rollback to this deployment**。

### 4.3 数据库迁移

Alembic 占位就绪后（v2 后续任务）：
```bash
# 本地
alembic upgrade head

# Render：通过 render.yaml 的 buildCommand 串接
buildCommand: "pip install -r requirements.txt && alembic upgrade head"
```

## 5. 扩容

### 5.1 Render 升级付费

| 场景 | 推荐 plan |
|------|-----------|
| 长期在线（无保活） | Starter $7/月 |
| 内存不够 512MB | Standard $25/月 |
| 磁盘超过 1GB | Standard $25/月（50GB） |

### 5.2 拆分前后端

如并发上来：
- 后端拆成 2 实例（Render Standard 负载均衡）
- Bitiful 切换到按量付费（仍极便宜）

## 6. 故障排查

| 现象 | 可能原因 | 排查命令 |
|------|----------|----------|
| 502 Bad Gateway | Render 实例休眠/崩溃 | `curl /health`；看 Render Logs |
| 启动报 `ModuleNotFoundError: boto3` | 依赖未装全 | 看 Render Build 日志；本地 `pip install -r requirements.txt` 复现 |
| 图片 404 | `STORAGE_BACKEND=local` 但 Render 用 `/data` 持久盘，旧实例丢图 | 改 `STORAGE_BACKEND=bitiful` 切对象存储 |
| CORS 报错 | `CORS_ALLOWED_ORIGINS` 未配 | 后台管理 → 系统设置 |
| `/api/v1/health` 返回 404 | 路由未注册 | 看 main.py `app.include_router(v1_router)` |
| 前端空白 | `VITE_API_BASE_URL` 配置错 | 看 `wrangler.toml` 与 `_redirects` |
| 频繁冷启动 | 保活失效 | 见 [keep_alive_setup.md](keep_alive_setup.md) |

## 7. 安全运维

- **密钥轮换**：每季度轮换 Render API Key、CF API Token、Bitiful AK/SK
- **依赖更新**：每月 `pip list --outdated` + Dependabot PR review
- **CVE 响应**：关键 CVE 出现 24h 内升级
- **登录审计**：管理后台 → 操作日志定期抽查
- **数据脱敏**：日志中 API Key / 邮箱需打码（已通过 `mask_sensitive_value` 实现）

## 8. 性能调优

### 8.1 SQLite WAL

已在 `app/core/database.py` 启用 WAL 模式（concurrent read/write）。

### 8.2 冷启动优化

已在 `app/main.py` 实现 SDK 懒加载（boto3 / openai 启动期不 import）。

### 8.3 静态资源

CF Pages 边缘缓存 + `_headers` 的 `/assets/*` 一年强缓存。

### 8.4 数据库连接

按需 `init_db()` 懒初始化，避免进程内多余连接。

## 9. 离线/灾备

- Render 区域（Singapore）故障时：迁移到 Oregon，需修改 `render.yaml.region` 并重新部署
- Bitiful 不可用时：临时切回 `STORAGE_BACKEND=local`（图片写入会丢，紧急期可接受）

## 10. 常用命令速查

```bash
# 健康检查
curl https://<app>.onrender.com/api/v1/health

# 备份
bash scripts/backup_persistent_disk.sh

# 迁移图片到 Bitiful
python scripts/migrate_to_bitiful.py

# 本地启动
bash scripts/start.sh

# 跑全部测试
py -m pytest

# 前端构建
cd backend/web && npm run build
```