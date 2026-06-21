"""Hash-stable weighted routing.

The same input prompt always lands on the same version within a routing
config. Switching the route re-partitions the hash space consistently, so
~10% of traffic moves when you change one weight by 10%.
"""

from __future__ import annotations

import hashlib


def pick_version(weights: dict[int, float], hash_key: str) -> int:
    """Pick a version from `weights` keyed by `hash_key`.

    `weights` maps version int -> non-negative float weight. Weights are
    normalized internally; they don't have to sum to 1.

    `hash_key` is typically the prompt body or a request_id — anything
    you want to be sticky-routed.
    """
    if not weights:
        raise ValueError("weights must be non-empty")
    if any(w < 0 for w in weights.values()):
        raise ValueError("weights must be non-negative")
    total = sum(weights.values())
    if total == 0:
        raise ValueError("at least one weight must be > 0")

    # SHA-256 → first 8 bytes → unsigned int → fraction in [0, 1)
    digest = hashlib.sha256(hash_key.encode("utf-8")).digest()[:8]
    fraction = int.from_bytes(digest, "big") / 2**64

    # Walk versions in sorted order so the partition is reproducible.
    cumulative = 0.0
    for version in sorted(weights.keys()):
        cumulative += weights[version] / total
        if fraction < cumulative:
            return version
    return sorted(weights.keys())[-1]  # belt-and-braces for rounding edge cases