# 安全性清单（task 12.4）

> v2 部署（Render + Cloudflare Pages + Bitiful）涉及的安全控制点完整清单。
> 对应 spec.md §4.3、design.md §3.4。

## 1. 密钥与凭证管理

### 1.1 必须保护的密钥
| 密钥 | 存储位置 | 风险等级 |
|------|----------|----------|
| Fernet 主密钥 (`.secret_key`) | `data/.secret_key`（仅本地） | **致命** |
| 管理员密码 | 环境变量 `ADMIN_PASSWORD` | 高 |
| LLM API Key | 环境变量 `LLM_API_KEY` | 高 |
| Image API Key | 环境变量 `IMAGE_API_KEY` | 高 |
| Bitiful AK/SK | 环境变量 `BITIFUL_*_KEY` | 高 |
| SMTP 密码 | 环境变量 `SMTP_PASSWORD` | 中 |
| Render API Key | Render Dashboard | **致命** |
| Cloudflare API Token | GitHub Secrets | **致命** |
| 统一管理平台 App Secret | 环境变量 `UNIFIED_PLATFORM_APP_SECRET` | 高 |

### 1.2 强制规则
- [x] **永不提交** `.env` / `.secret_key` / 任何 `*_KEY` 到 git
- [x] `.gitignore` 已含：`.env`、`.env.local`、`data/`、`*.key`
- [x] 仓库定期 grep 巡检：
  ```bash
  git log -p | grep -iE "(api[_-]?key|secret|password|token)\s*[:=]" || echo "clean"
  ```
- [x] 密钥轮换：每季度 / 离职员工 / CVE 出现 → 立即轮换

### 1.3 凭证加密落库
- [x] `encrypt_credential` / `decrypt_credential`（task 10.9）已实现 Fernet 包装
- [x] 幂等：明文/密文自动识别（`gAAAAA` 前缀）
- [x] 解密失败回退空字符串（不影响启动）

## 2. 通信安全

### 2.1 HTTPS
- [x] Render 自动签发 Let's Encrypt 证书
- [x] CF Pages 自动 HTTPS
- [x] HSTS 头已在 `_headers` 配置（`max-age=31536000; includeSubDomains`）
- [x] HTTP → HTTPS 自动重定向（Render / CF 默认行为）

### 2.2 API 安全
- [x] CORS 白名单：`CORS_ALLOWED_ORIGINS`（如 `https://auto-article-web.pages.dev`）
- [x] 路径遍历防护：`LocalStorageAdapter._resolve` 替换 `..`
- [x] CSP 头已在 `_headers` 配置，含 `frame-ancestors 'self'`
- [x] X-Frame-Options: SAMEORIGIN
- [x] X-Content-Type-Options: nosniff

## 3. 认证与授权

### 3.1 登录 Token
- [x] 64 位随机 hex（`secrets.token_hex(32)`）
- [x] 默认 24h 过期
- [x] 401 强制清空 localStorage token + 跳登录页

### 3.2 密码哈希
- [x] PBKDF2-HMAC-SHA256，12 万轮（OWASP 推荐 ≥ 60 万，本项目待升级到 ≥ 60 万）
- [x] 16 字节随机盐
- [x] 常量时间比较（`hmac.compare_digest`）
- [ ] **改进项**：升级 PBKDF2 轮数到 600_000（next sprint）

### 3.3 多用户隔离
- [x] `unified_platform_*` 支持统一管理平台认证（v2 后续接入）
- [x] 本地 admin 兜底（`UNIFIED_PLATFORM_*` 未配置时降级）
- [ ] **TODO**：细粒度 RBAC（设计文档 §3.4.3 占位）

## 4. 输入与输出

### 4.1 输入校验
- [x] Pydantic Schema 强类型校验（`app/schemas/`）
- [x] URL 采集白名单（运营层配置，task 5.x 占位）
- [x] SQL 全部走 ORM / 参数化（无 f-string 拼 SQL）
- [x] 命令执行未对外暴露（如需 shell 调用走 `subprocess.run(..., check=True, shell=False)`）

### 4.2 输出脱敏
- [x] API Key 列表接口使用 `mask_sensitive_value`（`****末4位`）
- [x] 日志中凭证字段已过滤（`setup_logging` 配置脱敏过滤器）
- [x] 错误信息对外不暴露堆栈（生产模式）

## 5. 依赖与供应链

### 5.1 已知漏洞
- [x] `cryptography>=44.0.0`、`fastapi>=0.115.0`、`pydantic>=2.10` 均已锁定下限
- [x] CI（建议）跑 `pip-audit` / `safety check`

### 5.2 依赖最小化
- [x] 仅必需依赖：fastapi/sqlalchemy/aiosqlite/apscheduler/cryptography/pydantic-settings/loguru/feedparser/httpx/openai/boto3
- [x] 不引入 Express / Flask 等非必要 Web 框架
- [x] 避免引入 eval/exec 类工具

## 6. 数据保护

### 6.1 数据库
- [x] SQLite WAL 模式（并发读写）
- [x] 定期备份到 Bitiful（`scripts/backup_persistent_disk.sh`）
- [x] 备份文件 `.tar.gz` 含 `app.db` + `images/` + `.secret_key`

### 6.2 静态资源
- [x] 图片上传走 `StorageAdapter`，无路径穿越
- [x] 文件名 UUID 化（`uuid4().hex`）避免猜测

### 6.3 日志
- [x] `loguru` 按天轮转 + 压缩
- [x] 日志保留 30 天
- [x] 不记录 Authorization 头 / Token / 密码明文

## 7. 平台级安全

### 7.1 Render
- [x] 环境变量走 Secret Files（`sync: false`）
- [x] Health Check 路径为 `/api/v1/health`（不暴露内部路径）
- [x] **禁止**在 Render Logs 打印凭证（脚本层过滤）

### 7.2 Cloudflare Pages
- [x] `_redirects` 不暴露 Render 子域名（用代理隐藏）
- [x] `_headers` 注入 CSP 防止 XSS
- [x] API Token 仅授 Pages Edit 权限

### 7.3 Bitiful
- [x] 桶策略：公共读（CDN 加速）+ 私有写
- [x] AccessKey 限 IP 白名单（如平台支持）
- [x] CDN Referer 防盗链（生产环境建议开启）

## 8. 风险与残余威胁

| 风险 | 等级 | 缓解 |
|------|------|------|
| Render 免费层 15 分钟休眠导致潜在时序 | 中 | 保活 cron |
| 免费层 750h/月超限 | 中 | 监控 + 月度复盘 |
| SQLite 写并发瓶颈 | 中 | WAL + 队列 |
| PBKDF2 轮数偏低 | 中 | 升级到 600_000（v2 后期） |
| Bitiful 单点 | 低 | 可切回 local 兜底 |
| GitHub 仓库泄露源码 | 中 | 私有仓库 + Dependabot |

## 9. 应急响应 Runbook

### 9.1 凭证泄露
1. 立即轮换对应平台的 Key
2. 查日志确认泄露窗口
3. 评估数据影响范围
4. 通知相关方
5. 复盘 + 加固

### 9.2 数据库被删
1. 切换 Render 实例为只读
2. 从 Bitiful 拉取最近备份
3. 恢复 + 验证
4. 排查删除路径（修漏洞）

### 9.3 异常登录
1. 强制全用户 Token 失效
2. 修改管理员密码
3. 查 audit log
4. 启用 IP 白名单（如平台支持）

## 10. 合规

- [x] GDPR 个人数据：采集话题不存个人隐私；如未来接入用户画像需补充隐私政策
- [x] 数据本地化：Render Singapore 节点；中国大陆合规性需用户自评
- [x] 日志保留：30 天后可手动清理（`scripts/cleanup_logs.sh` 待补）
- [ ] **TODO**：ICP 备案（如部署中国大陆节点）
- [ ] **TODO**：等保 2.0 三级（如服务政企客户）

## 11. 自检脚本

```bash
# 仓库根
bash scripts/security_scan.sh
# 检查项：
#  1. .env / .secret_key 未提交
#  2. requirements.txt 无已知 CVE
#  3. _headers CSP 完整
#  4. .gitignore 含 data/ .env
```

## 12. 链接

- [spec.md §4.3 安全性设计](../.codeartsdoer/specs/auto_article_generator_v2/spec.md)
- [design.md §3.4 威胁建模](../.codeartsdoer/specs/auto_article_generator_v2/design.md)
- [keep_alive_setup.md](keep_alive_setup.md)
- [12_operations.md](12_operations.md)