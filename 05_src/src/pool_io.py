from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

REQUIRED_COLUMNS = [
    "url",
    "sub_type",
    "estado",
    "idioma",
    "attempts",
    "last_error",
    "video_id",
    "titulo",
    "output_folder",
    "processed_at",
]


@dataclass
class PoolData:
    header: List[str]
    rows: List[Dict[str, str]]


def ensure_pool_exists(pool_path: Path) -> None:
    if pool_path.exists():
        return
    pool_path.parent.mkdir(parents=True, exist_ok=True)
    with pool_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(REQUIRED_COLUMNS)


def read_pool(pool_path: Path) -> PoolData:
    ensure_pool_exists(pool_path)
    with pool_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        rows = list(reader)
    if not rows:
        header = REQUIRED_COLUMNS.copy()
        return PoolData(header=header, rows=[])
    header = rows[0]
    if not header:
        header = REQUIRED_COLUMNS.copy()
    for col in REQUIRED_COLUMNS:
        if col not in header:
            header.append(col)
    data_rows: List[Dict[str, str]] = []
    for row in rows[1:]:
        row_dict = {col: "" for col in header}
        for idx, value in enumerate(row):
            if idx < len(header):
                row_dict[header[idx]] = value
        data_rows.append(row_dict)
    return PoolData(header=header, rows=data_rows)


def backup_pool(pool_path: Path, backup_dir: Path) -> None:
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir / f"pool_{timestamp}.txt"
    backup_path.write_bytes(pool_path.read_bytes())


def atomic_write_pool(pool_path: Path, tmp_dir: Path, pool_data: PoolData) -> None:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / "pool.tmp"
    with tmp_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(pool_data.header)
        for row in pool_data.rows:
            writer.writerow([row.get(col, "") for col in pool_data.header])
    pool_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.replace(pool_path)


def write_pool(
    pool_path: Path,
    backup_dir: Path,
    tmp_dir: Path,
    pool_data: PoolData,
) -> None:
    backup_pool(pool_path, backup_dir)
    atomic_write_pool(pool_path, tmp_dir, pool_data)


def recover_processing_rows(pool_data: PoolData) -> Tuple[PoolData, int]:
    recovered = 0
    for row in pool_data.rows:
        if row.get("estado") == "PROCESSING":
            row["estado"] = "NEW"
            recovered += 1
    return pool_data, recovered
