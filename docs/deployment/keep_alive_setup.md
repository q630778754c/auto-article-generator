# Render 免费实例保活配置（task 11.7）

> Render 免费 Web Service 在 **15 分钟无任何外部请求** 后会进入休眠，冷启动约 30-60 秒。
> 三种零成本方案任选其一，推荐 **cron-job.org**（最稳定）。

## 方案 A：cron-job.org（推荐，免费、零部署）

1. 注册 <https://cron-job.org/>（免费 50 个任务）
2. 新建 Cronjob：
   - **URL**：`https://<你的render域名>.onrender.com/api/v1/health`
   - **执行间隔**：每 **14 分钟**（`*/14 * * * *`，早于 15 分钟休眠阈值）
   - **HTTP 方法**：GET
   - **超时**：30 秒
   - **失败重试**：开启（重试 1 次）
3. 启用 → 邮件确认即可。

健康检查响应：
```json
{"code": 0, "message": "ok", "data": {"status": "healthy"}}
```

## 方案 B：UptimeRobot（免费 50 个监控）

1. 注册 <https://uptimerobot.com/>（免费 50 个监控项，5 分钟间隔）
2. **Add New Monitor**：
   - Type: `HTTP(s)`
   - Friendly Name: `auto-article-render-health`
   - URL: `https://<your-domain>.onrender.com/api/v1/health`
   - Monitoring Interval: **5 minutes**
3. Alert Contacts：填邮件 / Webhook（可选）

> ⚠️ 注意 UptimeRobot 免费版最短 5 分钟间隔，对 15 分钟休眠绰绰有余。

## 方案 C：GitHub Actions（自带 cron，无需第三方）

1. 在仓库 `.github/workflows/keep-alive.yml`：

   ```yaml
   name: Render Keep Alive
   on:
     schedule:
       - cron: "*/14 * * * *"
     workflow_dispatch:
   jobs:
     ping:
       runs-on: ubuntu-latest
       steps:
         - name: Ping health endpoint
           run: |
             curl -fsS --max-time 30 \
               "https://<your-domain>.onrender.com/api/v1/health" \
               || echo "ping failed at $(date -u)"
   ```

2. 推送到 main → 自动每 14 分钟触发。

> ⚠️ GitHub Actions cron 实际触发可能延迟几分钟，但 14 分钟足够保活。

## 验证保活生效

```bash
# 部署后空闲 20 分钟观察
curl https://<your-domain>.onrender.com/api/v1/health
# 若秒级返回（无 cold start 日志），保活成功
```

## 备用：本地长期脚本

```bash
# 仓库根目录自带 keep_alive_ping.sh，可放任意长期在线机器
chmod +x scripts/keep_alive_ping.sh
nohup ./scripts/keep_alive_ping.sh https://<your-domain>.onrender.com 840 > keep_alive.log 2>&1 &
```

参数：
- 位置 1：Render 公网 URL（默认 `https://auto-article-generator.onrender.com`）
- 位置 2：间隔秒数（默认 840 = 14 分钟）
- 环境变量 `HEALTH_PATH`：自定义健康路径（默认 `/api/v1/health`）

## 何时停用保活

升级到 Render 付费 plan（Starter $7/月起）后，实例不再休眠，可关闭保活避免无用流量。