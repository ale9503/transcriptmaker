from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

from src.captions_select import choose_captions
from src.errors import classify_error
from src.logging_jsonl import log_event
from src.pool_io import (
    PoolData,
    recover_processing_rows,
    read_pool,
    write_pool,
)
from src.vtt_parser import write_transcript
from src.ytdlp_client import (
    download_captions,
    get_info_json,
    get_title,
    get_video_id,
    get_version,
)

DEFAULT_ROOT = Path(
    r"D:\OneDrive - Colegio de Estudios Superiores de Administracion"
    r"\Negocios y Oportunidades\005. Extractor de Transcripciones"
)

REQUIRED_STATE_DEFAULTS = {
    "sub_type": "unknown",
    "estado": "NEW",
    "idioma": "unknown",
    "attempts": "0",
    "last_error": "",
    "video_id": "",
    "titulo": "",
    "output_folder": "",
    "processed_at": "",
}

INVALID_CHARS = "<>:\"/\\|?*"


def sanitize_filename(name: str, max_len: int = 120) -> str:
    sanitized = "".join("_" if ch in INVALID_CHARS else ch for ch in name)
    sanitized = " ".join(sanitized.split())
    sanitized = sanitized.replace("__", "_")
    sanitized = sanitized.strip(" .")
    if len(sanitized) > max_len:
        sanitized = sanitized[:max_len].rstrip(" .")
    return sanitized or "untitled"


def is_youtube_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.netloc.lower()
    return "youtube.com" in host or "youtu.be" in host


def ensure_row_defaults(row: Dict[str, str]) -> None:
    for key, value in REQUIRED_STATE_DEFAULTS.items():
        row.setdefault(key, value)
        if row[key] == "" and value:
            row[key] = value


def mark_row(
    pool: PoolData,
    row: Dict[str, str],
    *,
    backup_dir: Path,
    tmp_dir: Path,
    pool_path: Path,
) -> None:
    write_pool(pool_path, backup_dir, tmp_dir, pool)


def build_output_folder(out_base: Path, title: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_title = sanitize_filename(title)
    return out_base / f"{safe_title}_{timestamp}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="YouTube captions to transcript")
    parser.add_argument("--pool", type=Path, default=DEFAULT_ROOT / "01_pool" / "pool.txt")
    parser.add_argument("--out", type=Path, default=DEFAULT_ROOT / "02_output" / "youtube")
    parser.add_argument("--log", type=Path, default=DEFAULT_ROOT / "03_logs" / "run.log.jsonl")
    parser.add_argument("--tmp", type=Path, default=DEFAULT_ROOT / "04_runtime" / "tmp")
    parser.add_argument("--max-attempts", type=int, default=5)
    return parser.parse_args()


def handle_recovery(pool: PoolData, log_path: Path) -> bool:
    pool, recovered = recover_processing_rows(pool)
    if recovered == 0:
        return False
    for row in pool.rows:
        if row.get("estado") == "NEW":
            log_event(
                log_path,
                event="recovery",
                url=row.get("url", ""),
                video_id=row.get("video_id"),
                attempt_number=None,
                estado_resultante="NEW",
                sub_type=row.get("sub_type"),
                idioma=row.get("idioma"),
                msg="Recovered PROCESSING row to NEW",
            )
    return True


def main() -> None:
    args = parse_args()
    pool_path = args.pool
    backup_dir = pool_path.parent / "pool.backup"
    tmp_dir = args.tmp
    out_base = args.out
    log_path = args.log

    pool = read_pool(pool_path)
    for row in pool.rows:
        ensure_row_defaults(row)

    recovered = handle_recovery(pool, log_path)
    if recovered:
        write_pool(pool_path, backup_dir, tmp_dir, pool)

    ytdlp_version = get_version()

    for idx, row in enumerate(pool.rows):
        ensure_row_defaults(row)
        if row.get("estado") != "NEW":
            continue

        url = row.get("url", "").strip()
        log_event(
            log_path,
            event="start",
            url=url,
            video_id=row.get("video_id"),
            attempt_number=None,
            estado_resultante=None,
            sub_type=row.get("sub_type"),
            idioma=row.get("idioma"),
            msg="Starting processing",
        )

        if not url or not is_youtube_url(url):
            row["estado"] = "ERROR"
            row["last_error"] = "INVALID_URL"
            mark_row(pool, row, backup_dir=backup_dir, tmp_dir=tmp_dir, pool_path=pool_path)
            log_event(
                log_path,
                event="end",
                url=url,
                video_id=row.get("video_id"),
                attempt_number=None,
                estado_resultante=row["estado"],
                sub_type=row.get("sub_type"),
                idioma=row.get("idioma"),
                msg="Invalid URL",
            )
            continue

        attempts = int(row.get("attempts", "0") or 0)
        if attempts >= args.max_attempts:
            row["estado"] = "ERROR"
            row["last_error"] = "MAX_ATTEMPTS"
            mark_row(pool, row, backup_dir=backup_dir, tmp_dir=tmp_dir, pool_path=pool_path)
            log_event(
                log_path,
                event="end",
                url=url,
                video_id=row.get("video_id"),
                attempt_number=attempts,
                estado_resultante=row["estado"],
                sub_type=row.get("sub_type"),
                idioma=row.get("idioma"),
                msg="Max attempts reached",
            )
            continue

        video_id: Optional[str] = None
        final_estado: Optional[str] = None
        while attempts < args.max_attempts:
            attempts += 1
            row["attempts"] = str(attempts)
            log_event(
                log_path,
                event="attempt",
                url=url,
                video_id=video_id,
                attempt_number=attempts,
                estado_resultante=None,
                sub_type=row.get("sub_type"),
                idioma=row.get("idioma"),
                msg="Attempt start",
            )

            video_id, stderr, returncode = get_video_id(url)
            if returncode != 0 or not video_id:
                classified = classify_error(stderr, returncode)
                row["last_error"] = classified.summary
                log_event(
                    log_path,
                    event="attempt",
                    url=url,
                    video_id=video_id,
                    attempt_number=attempts,
                    estado_resultante=None,
                    sub_type=row.get("sub_type"),
                    idioma=row.get("idioma"),
                    msg=f"Failed to get video id: {classified.error_type}",
                    returncode=returncode,
                    stderr=stderr,
                )
                if not classified.retryable or attempts >= args.max_attempts:
                    row["estado"] = "ERROR"
                    final_estado = row["estado"]
                    break
                time.sleep(min(60, 2 ** attempts))
                continue

            row["video_id"] = video_id

            duplicate_url = any(
                i != idx and other.get("url", "").strip() == url
                for i, other in enumerate(pool.rows)
            )
            duplicate_id = any(
                i != idx
                and other.get("video_id") == video_id
                and other.get("estado") in {"DONE", "PROCESSING"}
                for i, other in enumerate(pool.rows)
            )
            if duplicate_url or duplicate_id:
                row["estado"] = "DUPLICATE"
                row["last_error"] = "DUPLICATE"
                final_estado = row["estado"]
                break

            row["estado"] = "PROCESSING"
            mark_row(pool, row, backup_dir=backup_dir, tmp_dir=tmp_dir, pool_path=pool_path)

            title, stderr, returncode = get_title(url)
            if returncode != 0 or not title:
                classified = classify_error(stderr, returncode)
                row["last_error"] = classified.summary
                log_event(
                    log_path,
                    event="attempt",
                    url=url,
                    video_id=video_id,
                    attempt_number=attempts,
                    estado_resultante=None,
                    sub_type=row.get("sub_type"),
                    idioma=row.get("idioma"),
                    msg=f"Failed to get title: {classified.error_type}",
                    returncode=returncode,
                    stderr=stderr,
                )
                if not classified.retryable or attempts >= args.max_attempts:
                    row["estado"] = "ERROR"
                    final_estado = row["estado"]
                    break
                time.sleep(min(60, 2 ** attempts))
                continue

            row["titulo"] = title

            info_json, stderr, returncode = get_info_json(url)
            if returncode != 0 or info_json is None:
                classified = classify_error(stderr, returncode)
                row["last_error"] = classified.summary
                log_event(
                    log_path,
                    event="attempt",
                    url=url,
                    video_id=video_id,
                    attempt_number=attempts,
                    estado_resultante=None,
                    sub_type=row.get("sub_type"),
                    idioma=row.get("idioma"),
                    msg=f"Failed to get info JSON: {classified.error_type}",
                    returncode=returncode,
                    stderr=stderr,
                )
                if not classified.retryable or attempts >= args.max_attempts:
                    row["estado"] = "ERROR"
                    final_estado = row["estado"]
                    break
                time.sleep(min(60, 2 ** attempts))
                continue

            sub_type, lang_key, idioma = choose_captions(info_json)
            row["sub_type"] = sub_type
            row["idioma"] = idioma

            if sub_type == "none" or not lang_key:
                row["estado"] = "NO_CAPTIONS"
                row["last_error"] = ""
                final_estado = row["estado"]
                break

            out_dir = build_output_folder(out_base, title)
            vtt_path, stderr, returncode = download_captions(
                url,
                out_dir,
                lang_key,
                sub_type,
            )
            if returncode != 0 or vtt_path is None:
                classified = classify_error(stderr, returncode)
                row["last_error"] = classified.summary
                log_event(
                    log_path,
                    event="attempt",
                    url=url,
                    video_id=video_id,
                    attempt_number=attempts,
                    estado_resultante=None,
                    sub_type=sub_type,
                    idioma=idioma,
                    msg=f"Failed to download captions: {classified.error_type}",
                    returncode=returncode,
                    stderr=stderr,
                )
                if not classified.retryable or attempts >= args.max_attempts:
                    row["estado"] = "ERROR"
                    final_estado = row["estado"]
                    break
                time.sleep(min(60, 2 ** attempts))
                continue

            captions_path = out_dir / "captions.vtt"
            if vtt_path != captions_path:
                captions_path.write_bytes(vtt_path.read_bytes())
                vtt_path.unlink(missing_ok=True)

            transcript_path = out_dir / "transcript.txt"
            write_transcript(captions_path, transcript_path)

            meta = {
                "url": url,
                "video_id": video_id,
                "titulo": title,
                "idioma": idioma,
                "sub_type": sub_type,
                "downloaded_at": datetime.now().isoformat(timespec="seconds"),
                "ytdlp_version": ytdlp_version,
            }
            (out_dir / "meta.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            row["estado"] = "DONE"
            row["processed_at"] = datetime.now().isoformat(timespec="seconds")
            row["output_folder"] = str(out_dir.relative_to(out_base))
            row["last_error"] = ""
            final_estado = row["estado"]
            break

        if final_estado is None:
            final_estado = row.get("estado")

        mark_row(pool, row, backup_dir=backup_dir, tmp_dir=tmp_dir, pool_path=pool_path)
        log_event(
            log_path,
            event="end",
            url=url,
            video_id=row.get("video_id"),
            attempt_number=attempts,
            estado_resultante=final_estado,
            sub_type=row.get("sub_type"),
            idioma=row.get("idioma"),
            msg="Finished processing",
        )


if __name__ == "__main__":
    main()
