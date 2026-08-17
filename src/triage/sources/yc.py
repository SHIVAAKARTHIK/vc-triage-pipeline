"""YC company data — the sourcing stage's structured backbone.

Two HTTP surfaces, both cached through triage.cache.Cache:

  * the per-batch OSS API (yc-oss.github.io/api) — structured, free, always
    present. Gives every candidate a name/website/one-liner for nothing.
  * the YC company's own public page — founder names *and bios* are embedded
    in an Inertia.js `data-page` HTML attribute as escaped JSON, but the OSS
    API does not expose them at all. Parsing that attribute is the only way to
    get real "team signal" per the brief — and it's genuinely there: Egress
    Health's page states its founder was "Prev Microsoft, Harvard CS", exactly
    the technical-depth signal the thesis scores on.

Founder-page parsing is best-effort: some older/acquired companies' pages have
drifted from this shape, so a parse failure returns `[]` rather than raising —
"founders/team signal where findable" per the brief, not "founders required."
"""

from __future__ import annotations

import html as html_lib
import json
import re

from triage.cache import Cache
from triage.util import slugify

BATCH_API = "https://yc-oss.github.io/api/batches/{slug}.json"

# Deliberately a loose two-bucket keyword AND, not a classifier: casts a wide
# enough net that the analyse stage's thesis-scored LLM call does the real
# judgment call, including scoring an off-thesis candidate down to Pass.
# See docs/decisions/0003-sourcing-is-a-loose-filter.md — tuned empirically
# against the real Winter 2025 batch (docs/worklog.md, 2026-08-17).
CAPABILITY_KEYWORDS = ("agent", "automat", "copilot", "ai-powered", "ai powered")
WORKFLOW_KEYWORDS = (
    "back office", "back-office", "admin", "operations", "billing", "invoice",
    "claims", "compliance", "schedul", "bookkeep", "collections",
    "revenue cycle", "paperwork", "workflow", "payroll", "procurement",
    "onboarding", "reconcil", "audit",
    # not bare "support": matched generic usage ("we support the SAT, ACT...")
    # on a real Winter 2025 company during tuning — see docs/worklog.md.
    "support team", "support rep", "customer support", "support ticket", "support queue",
)

_DATA_PAGE_RE = re.compile(r'data-page="(.*?)"', re.S)


def batch_slug(batch: str) -> str:
    """'Winter 2025' -> 'winter-2025', which happens to be exactly the OSS API's
    own slug convention — reuses util.slugify rather than a bespoke mapping."""
    return slugify(batch)


def fetch_batch(cache: Cache, batch: str) -> list[dict]:
    url = BATCH_API.format(slug=batch_slug(batch))
    data = cache.get_json(url)
    if not isinstance(data, list):
        raise ValueError(f"unexpected YC batch response shape for {batch!r} at {url}")
    return data


def parse_founders(page_html: str) -> list[str]:
    """"<Name> — <bio>" per founder, or just "<Name>" if no bio; [] if the page
    doesn't have the expected data-page blob at all."""
    match = _DATA_PAGE_RE.search(page_html)
    if not match:
        return []
    try:
        blob = html_lib.unescape(match.group(1))
        payload = json.loads(blob)
        founders = payload["props"]["company"]["founders"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return []

    out: list[str] = []
    for founder in founders:
        name = (founder.get("full_name") or "").strip()
        if not name:
            continue
        bio = (founder.get("founder_bio") or "").strip()
        out.append(f"{name} — {bio}" if bio else name)
    return out


def relevance_score(company: dict) -> int:
    """0 unless the description hits at least one keyword from *both* buckets;
    otherwise the count of total keyword hits, used only to rank, not to gate
    further than the AND itself."""
    text = f"{company.get('one_liner', '')} {company.get('long_description', '')}".lower()
    capability_hits = sum(1 for k in CAPABILITY_KEYWORDS if k in text)
    workflow_hits = sum(1 for k in WORKFLOW_KEYWORDS if k in text)
    if capability_hits == 0 or workflow_hits == 0:
        return 0
    return capability_hits + workflow_hits


def rank_candidates(companies: list[dict], limit: int) -> list[dict]:
    scored = [(relevance_score(c), c) for c in companies]
    relevant = [(score, c) for score, c in scored if score > 0]
    relevant.sort(key=lambda pair: (-pair[0], pair[1].get("name", "")))
    return [c for _, c in relevant[:limit]]
