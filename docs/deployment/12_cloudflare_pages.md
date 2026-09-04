# Cloudflare Pages 前端部署教程（task 9.x + 12.1）

> **零成本**部署 React 前端到 Cloudflare Pages。
> 配合 Render 后端，通过 `_redirects` 反代 `/api/*` 到 Render。

## 1. 准备工作

| 资源 | 用途 |
|------|------|
| Cloudflare 账号 | <https://dash.cloudflare.com/>（免费） |
| GitHub 仓库 | 已推送的 `auto-article-generator` |

## 2. 方案 A：GitHub Actions 自动部署（推荐）

### 2.1 在 Cloudflare 创建 API Token

1. Cloudflare Dashboard → **My Profile** → **API Tokens** → **Create Token**
2. 模板选 **Edit Cloudflare Pages** 或自定义权限：
   - Account → Cloudflare Pages → Edit
3. 复制 Token（**仅显示一次**）

### 2.2 在 GitHub 配置 Secrets

仓库 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**：

| Name | Value |
|------|-------|
| `CLOUDFLARE_API_TOKEN` | 上一步的 Token |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare Dashboard 右下角 "Account ID" |
| `VITE_API_BASE_URL` | **可选**；如使用 `_redirects` 代理则留空（推荐） |

### 2.3 触发部署

`main` 分支推送或手动 dispatch → `.github/workflows/deploy-frontend.yml` 自动构建并部署。

## 3. 方案 B：Dashboard 手动部署

1. Cloudflare Dashboard → **Workers & Pages** → **Create** → **Pages** → **Direct Upload**
2. 第一次先占位创建项目 `auto-article-web`
3. 本地构建前端：

```bash
cd backend/web
npm ci
npm run build
# 产物在 backend/app/static
```

4. 把 `backend/app/static` 打成 zip，上传到 Pages

## 4. 配置自定义域名（可选）

Pages 项目 → **Custom domains** → 添加 `auto.example.com` → 按提示加 CNAME。

## 5. 路由与重定向（已自动配置）

`public/_redirects` 内容：

```
/api/*  https://<your-render-app>.onrender.com/api/:splat  200
/*      /index.html                                       200
```

> 修改后重新部署生效。`<your-render-app>` 改为实际 Render 子域名。

## 6. HTTP 头（已自动配置）

`public/_headers` 已包含：
- 全局安全头（XFO / XCTO / Referrer-Policy / HSTS / CSP）
- `/assets/*` 一年强缓存
- `/index.html` 不缓存

CSP `connect-src` 已含 `*.onrender.com` 和 `*.bitiful.net`，如换域名需同步更新。

## 7. 构建版本号

每次构建通过 `VITE_BUILD_VERSION`（默认 commit SHA）+ `VITE_BUILD_TIME` 注入，前端 `src/api/client.ts` 暴露 `BUILD_VERSION` 常量，便于调试面板展示。

## 8. 验证

```bash
# 1. SPA 入口
curl -I https://auto-article-web.pages.dev/
# 200 OK

# 2. API 反代
curl https://auto-article-web.pages.dev/api/v1/health
# {"code":0, ...}

# 3. 资源缓存头
curl -I https://auto-article-web.pages.dev/assets/index-xxx.js
# Cache-Control: public, max-age=31536000, immutable
```

## 9. 免费层限制

| 资源 | 限制 |
|------|------|
| 构建次数 | 500 次/月（个人项目绰绰有余） |
| 带宽 | **无限** |
| 文件数 | 20000 个 |
| 单文件 | 25 MB |
| 自定义域名 | 无限 |

> Pages 不存在休眠问题（边缘节点），是 CF Pages 相对 Render 的核心优势。