// 轻量级前端构建配置单测（task 9.7）
// 不引入 vitest，直接用 Node 跑 assert。
// 验证：
//  1. vite.config.ts 正确读取 VITE_API_BASE_URL 环境变量
//  2. vite.config.ts 正确读取 VITE_BUILD_VERSION
//  3. 输出目录指向 backend/app/static
//  4. client.ts BASE_URL 拼接 "/api/v1"
//  5. 公共文件 _redirects/_headers 存在

import { strict as assert } from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const WEB_ROOT = path.resolve(__dirname, '..');

function read(p) {
  return fs.readFileSync(path.join(WEB_ROOT, p), 'utf-8');
}

function test(name, fn) {
  try {
    fn();
    console.log(`  ✓ ${name}`);
  } catch (e) {
    console.error(`  ✗ ${name}`);
    console.error('   ', e.message);
    process.exitCode = 1;
  }
}

console.log('[task 9.7] frontend build config tests');

const viteConfig = read('vite.config.ts');
const clientTs = read('src/api/client.ts');
const redirects = read('public/_redirects');
const headers = read('public/_headers');
const wrangler = read('wrangler.toml');
const deployYml = read('../../.github/workflows/deploy-frontend.yml');
const keepAliveYmlPath = path.join(WEB_ROOT, '..', '..', '.github', 'workflows', 'keep-render-alive.yml');

test('vite.config.ts reads VITE_API_BASE_URL', () => {
  assert.match(viteConfig, /process\.env\.VITE_API_BASE_URL/);
});

test('vite.config.ts reads VITE_BUILD_VERSION', () => {
  assert.match(viteConfig, /VITE_BUILD_VERSION/);
});

test('vite.config.ts injects __BUILD_VERSION__ define', () => {
  assert.match(viteConfig, /__BUILD_VERSION__:\s*JSON\.stringify\(BUILD_VERSION\)/);
});

test('vite.config.ts outDir is backend/app/static', () => {
  assert.match(viteConfig, /outDir:\s*['"]\.\.\/app\/static['"]/);
});

test('client.ts uses VITE_API_BASE_URL', () => {
  assert.match(clientTs, /import\.meta\.env\.VITE_API_BASE_URL/);
});

test('client.ts baseURL appends /api/v1', () => {
  assert.match(clientTs, /baseURL:\s*BASE_URL/);
  assert.match(clientTs, /\/api\/v1/);
});

test('_redirects proxies /api/* to render backend', () => {
  assert.match(redirects, /\/api\/\*.*onrender\.com/);
});

test('_redirects has SPA fallback to /index.html', () => {
  assert.match(redirects, /\/\*\s+\/index\.html/);
});

test('_headers has CSP connect-src for onrender + bitiful', () => {
  assert.match(headers, /connect-src/);
  assert.match(headers, /onrender\.com/);
  assert.match(headers, /bitiful\.net/);
});

test('_headers sets long cache for /assets/*', () => {
  assert.match(headers, /\/assets\/\*/);
  assert.match(headers, /max-age=31536000/);
});

test('wrangler.toml names the pages project', () => {
  assert.match(wrangler, /name\s*=\s*"auto-article-web"/);
});

test('GitHub Actions deploy workflow exists', () => {
  assert.match(deployYml, /Deploy Frontend to Cloudflare Pages/);
  assert.match(deployYml, /cloudflare\/pages-action/);
});

test('GitHub Actions keep-alive workflow exists', () => {
  assert.ok(fs.existsSync(keepAliveYmlPath), `keep-render-alive.yml not found at ${keepAliveYmlPath}`);
  const keepAlive = fs.readFileSync(keepAliveYmlPath, 'utf-8');
  assert.match(keepAlive, /cron:\s*["']\*\/14 \* \* \* \*["']/);
  assert.match(keepAlive, /\/api\/v1\/health/);
});

if (process.exitCode) {
  console.error('\n失败');
  process.exit(process.exitCode);
} else {
  console.log('\n全部通过');
}