"""SQLite-backed prompt store with versioning + routing."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .routing import pick_version


SCHEMA = """
CREATE TABLE IF NOT EXISTS prompts (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL,
    version INTEGER NOT NULL,
    body    TEXT NOT NULL,
    sha256  TEXT NOT NULL,
    created TEXT NOT NULL,
    UNIQUE(name, version)
);
CREATE INDEX IF NOT EXISTS idx_prompts_name ON prompts(name);

CREATE TABLE IF NOT EXISTS routes (
    name      TEXT PRIMARY KEY,
    weights   TEXT NOT NULL,
    updated   TEXT NOT NULL
);
"""


@dataclass
class PromptVersion:
    name: str
    version: int
    body: str
    sha256: str
    created: str


class PromptStore:
    def __init__(self, path: str | Path = "prompts.db"):
        self.path = str(path)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    # ---- write ----

    def set(self, name: str, body: str) -> PromptVersion:
        """Save `body` as the next version of `name`. Returns the new version.

        If body is identical to the latest version, no new row is written —
        we return the existing version. Avoids version-spam from re-runs.
        """
        body = body.strip("\n")
        sha = hashlib.sha256(body.encode("utf-8")).hexdigest()

        # Idempotency: if latest version has the same body, return it.
        latest = self.get_version(name, version=None, _internal=True)
        if latest and latest.sha256 == sha:
            return latest

        next_version = (latest.version + 1) if latest else 1
        created = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT INTO prompts (name, version, body, sha256, created) VALUES (?, ?, ?, ?, ?)",
            (name, next_version, body, sha, created),
        )
        # First version of a prompt auto-routes 100% to itself.
        if not latest:
            self._set_route(name, {next_version: 1.0})
        self._conn.commit()
        return PromptVersion(name=name, version=next_version, body=body, sha256=sha, created=created)

    def _set_route(self, name: str, weights: dict[int, float]) -> None:
        self._conn.execute(
            "INSERT INTO routes (name, weights, updated) VALUES (?, ?, ?) "
            "ON CONFLICT(name) DO UPDATE SET weights = excluded.weights, updated = excluded.updated",
            (name, json.dumps({str(k): v for k, v in weights.items()}), datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()

    def route(self, name: str, weights: dict[int, float]) -> None:
        """Set the routing weights for a prompt. Versions must already exist."""
        existing = {v.version for v in self.history(name)}
        bad = [v for v in weights if v not in existing]
        if bad:
            raise ValueError(f"unknown versions for {name}: {bad}")
        self._set_route(name, weights)

    def promote(self, name: str, version: int) -> None:
        """Shorthand: route 100% to one version."""
        self.route(name, {version: 1.0})

    # ---- read ----

    def get(self, name: str, hash_key: str | None = None) -> PromptVersion:
        """Get the version of `name` for the given hash_key (defaults to the name itself).

        Uses the route to pick deterministically.
        """
        weights = self._get_weights(name)
        if not weights:
            raise KeyError(f"no prompt named {name!r}")
        chosen = pick_version(weights, hash_key or name)
        return self.get_version(name, chosen)

    def get_version(self, name: str, version: int | None, *, _internal: bool = False) -> PromptVersion | None:
        if version is None:
            row = self._conn.execute(
                "SELECT name, version, body, sha256, created FROM prompts WHERE name = ? ORDER BY version DESC LIMIT 1",
                (name,),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT name, version, body, sha256, created FROM prompts WHERE name = ? AND version = ?",
                (name, version),
            ).fetchone()
        if not row:
            if _internal:
                return None
            raise KeyError(f"prompt {name!r} v{version} not found")
        return PromptVersion(*row)

    def history(self, name: str) -> list[PromptVersion]:
        rows = self._conn.execute(
            "SELECT name, version, body, sha256, created FROM prompts WHERE name = ? ORDER BY version",
            (name,),
        ).fetchall()
        return [PromptVersion(*r) for r in rows]

    def list_prompts(self) -> list[tuple[str, dict[int, float]]]:
        names = [r[0] for r in self._conn.execute("SELECT DISTINCT name FROM prompts ORDER BY name").fetchall()]
        return [(n, self._get_weights(n)) for n in names]

    def _get_weights(self, name: str) -> dict[int, float]:
        row = self._conn.execute("SELECT weights FROM routes WHERE name = ?", (name,)).fetchone()
        if not row:
            return {}
        return {int(k): v for k, v in json.loads(row[0]).items()}

    def close(self) -> None:
        self._conn.close()