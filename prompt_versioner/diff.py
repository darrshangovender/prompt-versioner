"""Unified-diff between two prompt versions."""

from __future__ import annotations

import difflib


def unified(a_label: str, a_body: str, b_label: str, b_body: str) -> str:
    return "".join(difflib.unified_diff(
        a_body.splitlines(keepends=True),
        b_body.splitlines(keepends=True),
        fromfile=a_label,
        tofile=b_label,
        lineterm="",
    ))