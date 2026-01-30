from __future__ import annotations

from typing import Dict, Optional, Tuple


def select_language_key(captions: Dict[str, object]) -> Optional[str]:
    if not captions:
        return None
    keys = list(captions.keys())
    for key in keys:
        if key.startswith("es"):
            return key
    for key in keys:
        if key.startswith("en"):
            return key
    return keys[0] if keys else None


def normalize_language(lang_key: Optional[str]) -> str:
    if not lang_key:
        return "unknown"
    if "-" in lang_key:
        return lang_key.split("-")[0]
    if len(lang_key) >= 2:
        return lang_key[:2]
    return lang_key


def choose_captions(info_json: Dict[str, object]) -> Tuple[str, Optional[str], str]:
    subtitles = info_json.get("subtitles") or {}
    if subtitles:
        lang_key = select_language_key(subtitles)
        idioma = normalize_language(lang_key)
        return "human", lang_key, idioma
    auto_captions = info_json.get("automatic_captions") or {}
    if auto_captions:
        lang_key = select_language_key(auto_captions)
        idioma = normalize_language(lang_key)
        return "auto", lang_key, idioma
    return "none", None, "unknown"
