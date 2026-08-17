"""The source stage: a YC batch in, `data/candidates.json` out.

The only pipeline stage that talks to the network (Fig. 1 in the project
overview) — analyse and memo only ever read the file this writes, so a broken
or half-finished sourcing run can't corrupt a working analysis. Per-candidate
fetch failures (a dead homepage, a reshaped YC page, no HN coverage) are caught
and degrade gracefully rather than aborting the run — every candidate still gets
built from whatever evidence *was* collected. See docs/decisions/0003.
"""

from __future__ import annotations

import html as html_lib
import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path

from triage.cache import Cache, FetchError
from triage.schemas import Candidate, Evidence, TractionSignal
from triage.sources import hn, yc
from triage.util import evidence_id, slugify

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path("data/raw")
DEFAULT_OUT_PATH = Path("data/candidates.json")

# Homepages and YC profile pages are the only HTML fetches here, and both are
# only ever read for something near the top of the document (a <meta
# description>, or the data-page blob — observed up to ~120KB in on real YC
# pages). Capping well above that avoids committing multi-megabyte JS-SPA
# bundles to data/raw for zero benefit; see docs/decisions/0003.
MAX_HTML_BODY_CHARS = 300_000

_META_DESCRIPTION_RE = re.compile(
    r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', re.I | re.S
)
_TAG_RE = re.compile(r"<[^>]+>")


def _extract_homepage_snippet(page_html: str, max_len: int = 400) -> str:
    """Prefer the meta description; fall back to tag-stripped body text."""
    match = _META_DESCRIPTION_RE.search(page_html)
    if match:
        text = html_lib.unescape(match.group(1)).strip()
    else:
        text = html_lib.unescape(_TAG_RE.sub(" ", page_html))
        text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


def _homepage_evidence(cache: Cache, website: str, now: datetime) -> Evidence | None:
    try:
        response = cache.get(website, max_body_chars=MAX_HTML_BODY_CHARS)
    except FetchError as exc:
        logger.warning("homepage fetch failed for %s: %s", website, exc)
        return None
    if response.status_code >= 400:
        return None
    snippet = _extract_homepage_snippet(response.text)
    if not snippet:
        return None
    return Evidence(
        id=evidence_id(website), url=website, source="homepage", retrieved_at=now, snippet=snippet
    )


def build_candidate(cache: Cache, raw: dict, batch: str) -> Candidate:
    """One YC OSS API record -> one fully evidenced Candidate.

    Always has at least one Evidence item (the YC listing itself), which is all
    the schema requires — everything past that (founders, HN traction, homepage
    snippet) is best-effort enrichment that's allowed to come back empty.
    """
    name = raw["name"]
    website = raw["website"]
    yc_url = raw["url"]
    now = datetime.now(UTC)

    yc_snippet = (
        raw.get("long_description") or raw.get("one_liner") or "No public description available."
    )
    evidence = [
        Evidence(
            id=evidence_id(yc_url), url=yc_url, source="yc", retrieved_at=now,
            snippet=yc_snippet[:500],
        )
    ]

    founders: list[str] = []
    try:
        yc_page = cache.get(yc_url, max_body_chars=MAX_HTML_BODY_CHARS)
        founders = yc.parse_founders(yc_page.text)
    except FetchError as exc:
        logger.warning("YC founder page fetch failed for %s: %s", name, exc)

    hn_hit = None
    try:
        hn_hit = hn.find_traction(cache, website)
    except FetchError as exc:
        logger.warning("HN lookup failed for %s: %s", name, exc)

    if hn_hit:
        traction = TractionSignal(
            kind="hn_post",
            detail=f"{hn_hit.points} pts, {hn_hit.num_comments} comments",
            url=hn_hit.story_url,
        )
        evidence.append(
            Evidence(
                id=evidence_id(hn_hit.story_url), url=hn_hit.story_url, source="hn",
                retrieved_at=now, snippet=hn_hit.title,
            )
        )
    else:
        # No HN coverage is the common case for very early startups (docs/worklog.md,
        # 2026-08-17) — batch admission itself is the freshness signal, and it's
        # already backed by the yc evidence item above.
        traction = TractionSignal(kind="yc_batch", detail=f"{batch} admission", url=yc_url)

    homepage_ev = _homepage_evidence(cache, website, now)
    if homepage_ev:
        evidence.append(homepage_ev)

    return Candidate(
        slug=slugify(name),
        name=name,
        website=website,
        one_liner=(raw.get("one_liner") or "(no one-liner published)")[:280],
        founders=founders,
        source_batch=batch,
        traction=traction,
        evidence=evidence,
        sourced_at=now,
    )


def run(
    batch: str,
    limit: int = 15,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    out_path: Path = DEFAULT_OUT_PATH,
) -> list[Candidate]:
    with Cache(cache_dir) as cache:
        raw_companies = yc.fetch_batch(cache, batch)
        ranked = yc.rank_candidates(raw_companies, limit=limit)

        candidates: list[Candidate] = []
        seen_slugs: set[str] = set()
        for raw in ranked:
            candidate = build_candidate(cache, raw, batch)
            if candidate.slug in seen_slugs:
                logger.warning(
                    "skipping %s: slug %r collides with an earlier candidate",
                    candidate.name, candidate.slug,
                )
                continue
            seen_slugs.add(candidate.slug)
            candidates.append(candidate)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [c.model_dump(mode="json") for c in candidates]
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("wrote %d candidates to %s", len(candidates), out_path)
    return candidates
