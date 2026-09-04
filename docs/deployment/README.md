# 部署文档（v2 零信用卡零成本方案）

> Render（后端）+ Cloudflare Pages（前端）+ Bitiful（图片存储）+ SQLite（数据库）全套免费部署。

## 快速链接

| 文档 | 内容 |
|------|------|
| [12_render.md](12_render.md) | Render Web Service 部署教程（含免费层限制） |
| [12_cloudflare_pages.md](12_cloudflare_pages.md) | Cloudflare Pages 前端部署（含 GitHub Actions） |
| [12_local_dev.md](12_local_dev.md) | 本地开发环境搭建 |
| [12_operations.md](12_operations.md) | 日常运维 SOP（备份/恢复/扩容/故障排查） |
| [12_security.md](12_security.md) | 安全性清单（密钥/通信/认证/合规） |
| [keep_alive_setup.md](keep_alive_setup.md) | Render 免费实例保活配置 |

## 架构总览

```
                    用户浏览器
                         │
                         ▼
        Cloudflare Pages (前端 SPA + 边缘缓存)
                         │
                         │ /api/* (通过 _redirects 反代)
                         ▼
            Render Web Service (FastAPI + SQLite)
                         │
                         │ boto3 (S3 兼容)
                         ▼
                  Bitiful 对象存储 (图片)
```

## 一键部署路线

1. **推送代码** → GitHub
2. **部署后端** → 按 [12_render.md](12_render.md) 创建 Render Web Service
3. **部署前端** → 按 [12_cloudflare_pages.md](12_cloudflare_pages.md) 配置 GitHub Actions
4. **配置保活** → 按 [keep_alive_setup.md](keep_alive_setup.md) 任选一种方案
5. **配置 Bitiful** → 注册实名后填入 `BITIFUL_*` 环境变量
6. **验证** → `/api/v1/health` 返回 200 + `storage_backend=bitiful`

## 关键设计决策

- **Render 区域选择 Singapore**（国内访问延迟 < 100ms）
- **CF Pages 反代 /api**（避免 CORS 跨域，且隐藏 Render 域名）
- **Bitiful S3 兼容**（boto3 复用 AWS 生态，无需专用 SDK）
- **Fernet 加密凭证**（落 .env 即加密，零侵入兼容明文）
- **GitHub Actions 保活**（避免 cron-job.org 第三方依赖）
- **延迟加载 SDK**（boto3/openai 启动期不 import，冷启动 < 5s）

## 相关规格文档

- `E:\抓取数据\.codeartsdoer\specs\auto_article_generator_v2\spec.md`（v2 需求规格）
- `E:\抓取数据\.codeartsdoer\specs\auto_article_generator_v2\design.md`（v2 设计文档，重点 §9-§12）
- `E:\抓取数据\.codeartsdoer\specs\auto_article_generator_v2\tasks.md`（实施任务清单）
- `E:\抓取数据\.codeartsdoer\specs\auto_article_generator_v2\no_card_deploy.md`（无信用卡部署方案论证）
- `E:\抓取数据\.codeartsdoer\specs\auto_article_generator_v2\bitiful_adapter.md`（Bitiful 适配器设计）
- `E:\抓取数据\.codeartsdoer\specs\auto_article_generator_v2\free_deploy_guide.md`（免费部署全流程）