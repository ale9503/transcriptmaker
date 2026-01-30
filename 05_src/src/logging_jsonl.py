from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


MAX_STDERR = 500


def iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def log_event(
    log_path: Path,
    *,
    event: str,
    url: str,
    video_id: Optional[str],
    attempt_number: Optional[int],
    estado_resultante: Optional[str],
    sub_type: Optional[str],
    idioma: Optional[str],
    msg: str,
    returncode: Optional[int] = None,
    stderr: Optional[str] = None,
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    payload: Dict[str, Any] = {
        "ts": iso_now(),
        "event": event,
        "url": url,
        "video_id": video_id,
        "attempt_number": attempt_number,
        "estado_resultante": estado_resultante,
        "sub_type": sub_type,
        "idioma": idioma,
        "msg": msg,
        "returncode": returncode,
        "stderr_excerpt": (stderr or "")[:MAX_STDERR],
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
