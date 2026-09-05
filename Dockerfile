# ---- Stage 1: 前端构建 ----
FROM node:20-alpine AS frontend
WORKDIR /build
COPY backend/web/package*.json ./
RUN npm install
COPY backend/web/ ./
RUN npm run build

# ---- Stage 2: 后端运行 ----
FROM python:3.11-slim
WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/alembic ./alembic
COPY --from=frontend /app/static ./app/static

# Render 注入 PORT，启动脚本读取
COPY start.sh ./
RUN chmod +x start.sh

EXPOSE 10000
CMD ["bash", "start.sh"]