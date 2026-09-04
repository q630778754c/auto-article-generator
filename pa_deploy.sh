#!/bin/bash
# PythonAnywhere 一键部署脚本
# 在 PythonAnywhere Dashboard → Consoles → Bash 中粘贴执行
# Webapp ID: 7040, Domain: q630778754.pythonanywhere.com

set -e

USERNAME="q630778754"
HOME_DIR="/home/$USERNAME"
PROJECT_DIR="$HOME_DIR/auto-article-generator"
VENV_DIR="$HOME_DIR/.virtualenvs/aag"
DOMAIN="$USERNAME.pythonanywhere.com"
WEBAPP_ID=7040
API_TOKEN="06a1e8a559d2055c405db2ef06104e683618698f"

echo "=== 1/7 克隆代码 ==="
if [ -d "$PROJECT_DIR" ]; then
    echo "目录已存在，拉取最新代码..."
    cd "$PROJECT_DIR"
    git pull
else
    git clone https://github.com/q630778754c/auto-article-generator.git "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

echo "=== 2/7 创建数据目录 ==="
mkdir -p "$HOME_DIR/data/images"
mkdir -p "$HOME_DIR/data/logs"

echo "=== 3/7 创建虚拟环境 (Python 3.10) ==="
if [ ! -d "$VENV_DIR" ]; then
    python3.10 -m venv "$VENV_DIR"
fi

echo "=== 4/7 安装依赖 ==="
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/backend/requirements.txt"

echo "=== 5/7 配置 WSGI 文件 ==="
cat > "$HOME_DIR/mysite_wsgi.py" << 'WSGI_EOF'
import os, sys, asyncio

project_home = '/home/q630778754/auto-article-generator/backend'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.environ['DATA_DIR'] = '/home/q630778754/data'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ['APP_HOST'] = '0.0.0.0'
os.environ['APP_PORT'] = '8080'
os.environ['LOG_LEVEL'] = 'INFO'
os.environ['ADMIN_USERNAME'] = 'admin'
os.environ['LLM_PROVIDER'] = 'openai'
os.environ['LLM_API_KEY'] = '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'
os.environ['LLM_BASE_URL'] = 'https://integrate.api.nvidia.com/v1'
os.environ['LLM_MODEL'] = 'meta/llama-3.1-405b-instruct'
os.environ['BUILD_VERSION'] = 'pa-deploy-v1'

from app.main import app as asgi_app

def application(environ, start_response):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    method = environ.get('REQUEST_METHOD', 'GET')
    path = environ.get('PATH_INFO', '/')
    query = environ.get('QUERY_STRING', '').encode()
    headers = []
    for key, value in environ.items():
        if key.startswith('HTTP_'):
            hdr = key[5:].replace('_', '-').lower()
            headers.append((hdr.encode(), value.encode()))
    if 'CONTENT_TYPE' in environ:
        headers.append((b'content-type', environ['CONTENT_TYPE'].encode()))
    if 'CONTENT_LENGTH' in environ:
        headers.append((b'content-length', environ['CONTENT_LENGTH'].encode()))
    body = b''
    try:
        length = int(environ.get('CONTENT_LENGTH', 0))
        if length > 0:
            body = environ['wsgi.input'].read(length)
    except Exception:
        pass
    response_started = False
    response_body = b''
    async def receive():
        return {'type': 'http.request', 'body': body, 'more_body': False}
    async def send(message):
        nonlocal response_started, response_body
        if message['type'] == 'http.response.start':
            sc = message['status']
            sm = {200: 'OK', 404: 'Not Found', 500: 'Server Error'}
            rh = [(k.decode() if isinstance(k, bytes) else k,
                   v.decode() if isinstance(v, bytes) else v)
                  for k, v in message.get('headers', [])]
            start_response(f'{sc} {sm.get(sc, "Status")}', rh)
            response_started = True
        elif message['type'] == 'http.response.body':
            response_body += message.get('body', b'')
    scope = {
        'type': 'http', 'asgi': {'version': '3.0', 'spec_version': '2.0'},
        'http_version': '1.1', 'method': method, 'scheme': 'https',
        'path': path, 'raw_path': path.encode(), 'query_string': query,
        'headers': headers,
        'client': (environ.get('REMOTE_ADDR', '0.0.0.0'), 0),
        'server': (environ.get('SERVER_NAME', 'localhost'), int(environ.get('SERVER_PORT', 80))),
    }
    try:
        loop.run_until_complete(asgi_app(scope, receive, send))
    except Exception as e:
        if not response_started:
            start_response('500 Server Error', [('Content-Type', 'text/plain')])
            return [f'Error: {e}'.encode()]
    finally:
        loop.close()
    return [response_body] if response_body else [b'']
WSGI_EOF

echo "WSGI文件已写入: $HOME_DIR/mysite_wsgi.py"

echo "=== 6/7 更新 Web App 配置 ==="
curl -sS -X PATCH \
    -H "Authorization: Token $API_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"source_directory\": \"$PROJECT_DIR/backend\", \"working_directory\": \"$PROJECT_DIR/backend\", \"virtualenv\": \"$VENV_DIR\"}" \
    "https://www.pythonanywhere.com/api/v1/user/$USERNAME/webapps/$WEBAPP_ID/" 2>&1 || true
echo ""

echo "=== 7/7 重载 Web App ==="
curl -sS -X POST \
    -H "Authorization: Token $API_TOKEN" \
    "https://www.pythonanywhere.com/api/v1/user/$USERNAME/webapps/$WEBAPP_ID/reload/" 2>&1 || true
echo ""

echo "=== 部署完成! ==="
echo "URL: https://$DOMAIN"
echo "API健康检查: https://$DOMAIN/api/v1/health"
echo ""
echo "首次加载可能需要10-30秒（冷启动）"
echo "如遇错误，请检查: https://www.pythonanywhere.com/user/$USERNAME/webapps/$DOMAIN/"
