from __future__ import annotations

import re
from pathlib import Path
from typing import List

TAG_RE = re.compile(r"<[^>]+>")
TIMESTAMP_RE = re.compile(r"-->" )
INDEX_RE = re.compile(r"^\d+$")


def parse_vtt_to_lines(contents: str) -> List[str]:
    lines: List[str] = []
    for raw_line in contents.splitlines():
        line = raw_line.strip()
        if not line:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if line.startswith("WEBVTT"):
            continue
        if TIMESTAMP_RE.search(line):
            continue
        if INDEX_RE.match(line):
            continue
        line = TAG_RE.sub("", line)
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    cleaned: List[str] = []
    for line in lines:
        if line == "" and (not cleaned or cleaned[-1] == ""):
            continue
        cleaned.append(line)
    return cleaned


def write_transcript(vtt_path: Path, transcript_path: Path) -> None:
    contents = vtt_path.read_text(encoding="utf-8")
    lines = parse_vtt_to_lines(contents)
    transcript_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
