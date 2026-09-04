# Render Persistent Disk 备份到 Bitiful
# 用法：bash scripts/backup_persistent_disk.sh
# 需在Render环境变量中配置BITIFUL_* 或在本地.boto中配置

set -e

DATA_DIR="${DATA_DIR:-/data}"
BACKUP_NAME="auto-article-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
TMP="/tmp/${BACKUP_NAME}"

if [ ! -d "${DATA_DIR}" ]; then
    echo "DATA_DIR ${DATA_DIR} 不存在"; exit 1
fi

echo "=== 打包 ${DATA_DIR} ==="
tar czf "${TMP}" -C "${DATA_DIR}" .

if [ -n "${BITIFUL_BUCKET}" ] && [ -n "${BITIFUL_ACCESS_KEY}" ]; then
    AWS_ACCESS_KEY_ID="${BITIFUL_ACCESS_KEY}" \
    AWS_SECRET_ACCESS_KEY="${BITIFUL_SECRET_KEY}" \
    AWS_ENDPOINT_URL="${BITIFUL_ENDPOINT}" \
    aws s3 cp "${TMP}" "s3://${BITIFUL_BUCKET}/backups/${BACKUP_NAME}" --endpoint-url "${BITIFUL_ENDPOINT}"
    echo "已上传到 Bitiful: backups/${BACKUP_NAME}"
else
    echo "BITIFUL_* 未配置，仅本地归档：${TMP}"
fi