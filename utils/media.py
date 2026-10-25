"""Bounded HTTP byte-range parsing for artwork video playback."""

import re


def video_byte_range(value: str, size: int) -> tuple[int, int]:
    match = re.fullmatch(r"bytes=(\d{0,20})-(\d{0,20})", value)
    if not match or size <= 0:
        raise ValueError("Invalid byte range")
    first, last = match.groups()
    if not first:
        if not last or int(last) <= 0:
            raise ValueError("Invalid suffix range")
        return max(0, size - int(last)), size - 1
    start = int(first)
    end = min(int(last), size - 1) if last else size - 1
    if start >= size or end < start:
        raise ValueError("Unsatisfiable range")
    return start, end
