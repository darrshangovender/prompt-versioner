"""Hash-stable weighted routing.

The same input prompt always lands on the same version within a routing
config.

Note the partition is a sequential walk over versions in sorted order, not
consistent hashing: the boundaries are cumulative, so changing one weight moves
every boundary after it. Going from ``{1: .5, 2: .25, 3: .25}`` to
``{1: .4, 2: .25, 3: .35}`` moves 20% of traffic, not 10%, and replaces v2's
population wholesale even though its weight did not change. Stickiness holds
for a *fixed* routing config; it does not hold across a reweight.
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
    return max(weights.keys())  # belt-and-braces for rounding edge cases