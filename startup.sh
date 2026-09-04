#!/bin/bash
cd /workspaces/auto-article-generator/backend
pip install -r requirements.txt 2>&1 | tail -5
export DATA_DIR=/tmp/data
export STORAGE_BACKEND=local
export APP_HOST=0.0.0.0
export APP_PORT=8000
export LOG_LEVEL=INFO
export ADMIN_USERNAME=admin
export LLM_PROVIDER=openai
export LLM_API_KEY=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
export LLM_BASE_URL=https://integrate.api.nvidia.com/v1
export LLM_MODEL=meta/llama-3.1-405b-instruct
export BUILD_VERSION=codespace-v1
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/server.log 2>&1 &
echo "Server started on port 8000"
