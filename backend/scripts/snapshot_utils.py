"""脚本侧的快照工具：复用 app.tools.snapshot_store 的同一套校验逻辑。"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SNAPSHOT = BASE_DIR / "data" / "company_snapshots.json"

sys.path.insert(0, str(BASE_DIR))

from app.tools.snapshot_store import (  # noqa: E402,F401
    DATE_FIELDS,
    DATE_FORMATS,
    REQUIRED_FIELDS,
    find_snapshot,
    load_snapshot_file,
    parse_date,
    remove_record,
    save_snapshot_file,
    unlocked_rules,
    upsert_record,
    validate_record,
)
