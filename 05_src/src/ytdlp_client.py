from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def run_yt_dlp(args: List[str]) -> Tuple[int, str, str]:
    process = subprocess.run(
        ["yt-dlp", *args],
        capture_output=True,
        text=True,
    )
    return process.returncode, process.stdout.strip(), process.stderr.strip()


def get_video_id(url: str) -> Tuple[Optional[str], str, int]:
    returncode, stdout, stderr = run_yt_dlp(["--print", "%(id)s", url])
    video_id = stdout.strip() if returncode == 0 else None
    return video_id, stderr, returncode


def get_title(url: str) -> Tuple[Optional[str], str, int]:
    returncode, stdout, stderr = run_yt_dlp(["--print", "%(title)s", url])
    title = stdout.strip() if returncode == 0 else None
    return title, stderr, returncode


def get_info_json(url: str) -> Tuple[Optional[Dict[str, Any]], str, int]:
    returncode, stdout, stderr = run_yt_dlp(["--dump-single-json", url])
    if returncode != 0:
        return None, stderr, returncode
    try:
        return json.loads(stdout), stderr, returncode
    except json.JSONDecodeError:
        return None, "Failed to parse JSON", 1


def get_version() -> Optional[str]:
    returncode, stdout, _stderr = run_yt_dlp(["--version"])
    if returncode != 0:
        return None
    return stdout.strip() or None


def download_captions(
    url: str,
    out_dir: Path,
    lang_key: str,
    sub_type: str,
) -> Tuple[Optional[Path], str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(out_dir / "%(id)s.%(ext)s")
    if sub_type == "human":
        args = [
            "--skip-download",
            "--write-subs",
            "--sub-langs",
            lang_key,
            "-o",
            output_template,
            url,
        ]
    else:
        args = [
            "--skip-download",
            "--write-auto-subs",
            "--sub-langs",
            lang_key,
            "-o",
            output_template,
            url,
        ]
    returncode, _stdout, stderr = run_yt_dlp(args)
    if returncode != 0:
        return None, stderr, returncode

    vtt_files = list(out_dir.glob("*.vtt"))
    if not vtt_files:
        return None, "No VTT file produced", 1
    return vtt_files[0], stderr, returncode
