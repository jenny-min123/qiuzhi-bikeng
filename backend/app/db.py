"""SQLite 单库（V3 4.10：不引入 MySQL + Redis）。

两张表：
- evidence_cache：证据 / 工商查询结果缓存，key = "provider:公司名"
- reports：分析报告，供 /export 与报告页刷新后读取
"""

from __future__ import annotations

import json
import sqlite3
import time
from typing import Any

from .config import settings


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS evidence_cache (
                key        TEXT PRIMARY KEY,
                value      TEXT NOT NULL,
                expires_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                report_id  TEXT PRIMARY KEY,
                payload    TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )


def cache_get(key: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT value, expires_at FROM evidence_cache WHERE key = ?", (key,)
        ).fetchone()
    if row is None:
        return None
    if row["expires_at"] < time.time():
        return None
    try:
        return json.loads(row["value"])
    except json.JSONDecodeError:
        return None


def cache_set(key: str, value: dict[str, Any], ttl_seconds: int | None = None) -> None:
    ttl = settings.cache_ttl_seconds if ttl_seconds is None else ttl_seconds
    expires_at = time.time() + ttl
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO evidence_cache (key, value, expires_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value,
                                           expires_at = excluded.expires_at
            """,
            (key, json.dumps(value, ensure_ascii=False), expires_at),
        )


def save_report(report_id: str, payload: dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO reports (report_id, payload, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(report_id) DO UPDATE SET payload = excluded.payload
            """,
            (report_id, json.dumps(payload, ensure_ascii=False), time.time()),
        )


def get_report(report_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT payload FROM reports WHERE report_id = ?", (report_id,)
        ).fetchone()
    if row is None:
        return None
    try:
        return json.loads(row["payload"])
    except json.JSONDecodeError:
        return None
