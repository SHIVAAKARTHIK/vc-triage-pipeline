"""Small, dependency-free helpers shared across pipeline stages."""

from __future__ import annotations

import hashlib
import re


def slugify(name: str) -> str:
    """Turn a company name into a filesystem- and URL-safe slug.

    Used as the join key between `data/candidates.json`, `data/analyses/`, and
    `out/memos/` — see docs/decisions/0001-stack-and-scope.md. Deliberately simple
    (no external dependency): lowercase, non-alphanumerics become single hyphens,
    leading/trailing hyphens stripped.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    if not slug:
        raise ValueError(f"cannot derive a slug from name={name!r}")
    return slug


def evidence_id(url: str) -> str:
    """Derive a stable evidence id from the URL it was fetched from.

    Hash-based rather than a running counter so the same URL always gets the same
    id across separate pipeline runs. That pairs with the committed HTTP cache
    (docs/decisions/0001): re-running sourcing against the cache reproduces
    identical evidence ids, which keeps `data/analyses/*.json` byte-stable when
    nothing upstream actually changed, and means fetching the same URL twice for
    one candidate naturally dedupes instead of creating two evidence records.
    """
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:8]
    return f"ev_{digest}"
