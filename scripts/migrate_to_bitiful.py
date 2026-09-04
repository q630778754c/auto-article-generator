#!/usr/bin/env python
"""Bitiful 迁移工具（task 10.7）。

用法：
  # 干跑（仅打印计划，不实际上传）
  python migrate_to_bitiful.py --dry-run

  # 实际迁移（将 DATA_DIR/images 下所有文件上传到 Bitiful，并打印映射表）
  python migrate_to_bitiful.py

  # 自定义源目录
  python migrate_to_bitiful.py --source ./data/images

环境：
  BITIFUL_ENDPOINT / BITIFUL_ACCESS_KEY / BITIFUL_SECRET_KEY
  BITIFUL_BUCKET / BITIFUL_PUBLIC_BASE

可选：
  --key-prefix  - 目标对象前缀（默认 images/）
  --concurrency - 并发上传数（默认 5）
"""

from __future__ import annotations

import argparse
import concurrent.futures
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.storage import (  # noqa: E402
    BitifulStorageAdapter,
    StorageBackendError,
)


def _collect(source_dir: Path) -> list[Path]:
    if not source_dir.exists():
        print(f"源目录不存在: {source_dir}", file=sys.stderr)
        return []
    return [p for p in source_dir.rglob("*") if p.is_file()]


def _upload_one(adapter: BitifulStorageAdapter, src: Path, key_prefix: str) -> str:
    rel = src.name
    key = f"{key_prefix.rstrip('/')}/{rel}"
    return adapter.put(src, key)


def main() -> int:
    parser = argparse.ArgumentParser(description="本地图片迁移到 Bitiful 对象存储")
    parser.add_argument("--source", default=os.environ.get("DATA_DIR", "../data") + "/images")
    parser.add_argument("--key-prefix", default="images/")
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source_dir = Path(args.source).resolve()
    files = _collect(source_dir)
    print(f"扫描到 {len(files)} 个文件，源={source_dir}")

    if args.dry_run:
        for f in files[:20]:
            print(f"  DRY: {f.relative_to(source_dir)} -> {args.key_prefix}{f.name}")
        if len(files) > 20:
            print(f"  ... 还有 {len(files) - 20} 个未显示")
        return 0

    try:
        adapter = BitifulStorageAdapter(
            endpoint=os.environ.get("BITIFUL_ENDPOINT", ""),
            access_key=os.environ.get("BITIFUL_ACCESS_KEY", ""),
            secret_key=os.environ.get("BITIFUL_SECRET_KEY", ""),
            bucket=os.environ.get("BITIFUL_BUCKET", ""),
            public_base=os.environ.get("BITIFUL_PUBLIC_BASE", ""),
        )
    except StorageBackendError as exc:
        print(f"初始化 Bitiful 适配器失败: {exc}", file=sys.stderr)
        return 2

    success = 0
    failed: list[tuple[Path, str]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futures = {
            ex.submit(_upload_one, adapter, f, args.key_prefix): f for f in files
        }
        for fut in concurrent.futures.as_completed(futures):
            f = futures[fut]
            try:
                url = fut.result()
                success += 1
                print(f"  OK {f.relative_to(source_dir)} -> {url}")
            except Exception as exc:
                failed.append((f, str(exc)))

    print(f"\n完成：成功 {success}，失败 {len(failed)}")
    if failed:
        print("失败文件：")
        for f, err in failed:
            print(f"  - {f}: {err}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())