from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ClassifiedError:
    error_type: str
    retryable: bool
    summary: str


def classify_error(stderr: str, returncode: int) -> ClassifiedError:
    lowered = (stderr or "").lower()
    if returncode == 0:
        return ClassifiedError("OK", False, "")

    retryable_signals = [
        "timed out",
        "timeout",
        "connection reset",
        "connection aborted",
        "temporarily unavailable",
        "http error 429",
        "too many requests",
        "proxy error",
        "tls",
        "ssl",
        "network",
        "unable to download",
        "server error",
    ]
    non_retryable_signals = [
        "video unavailable",
        "private video",
        "this video is private",
        "sign in to confirm your age",
        "age-restricted",
        "this video is not available",
        "copyright claim",
        "members-only",
        "live event will begin",
        "not a valid url",
    ]

    for signal in non_retryable_signals:
        if signal in lowered:
            return ClassifiedError("NON_RETRYABLE", False, signal)

    for signal in retryable_signals:
        if signal in lowered:
            return ClassifiedError("RETRYABLE", True, signal)

    if returncode != 0:
        return ClassifiedError("UNKNOWN", True, lowered[:200])

    return ClassifiedError("UNKNOWN", False, lowered[:200])
