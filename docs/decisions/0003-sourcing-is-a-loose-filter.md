# ADR 0003 — Sourcing casts a loose net; the thesis-scored LLM call does the real filtering

- **Date:** 2026-08-17
- **Status:** Accepted
- **Authored by:** Karthik, drafted with Claude Code; tuned empirically against the real YC Winter 2025 batch

## Context

The source stage (`src/triage/source.py`, `src/triage/sources/`) turns a YC batch
into 10–20 evidenced `Candidate`s. Three empirical findings from building this
against the live YC OSS API and HN Algolia API shaped the design more than
anything decided up front:

1. **YC's public company page embeds real founder bios** in an HTML-escaped
   Inertia.js `data-page` attribute — not exposed by the OSS API's bulk JSON at
   all. e.g. Egress Health's founder is described as "Prev Microsoft, Harvard
   CS" — exactly the technical-depth signal the thesis scores on. Worth a second,
   page-specific fetch per candidate beyond the batch listing.
2. **Most very-early startups have zero Hacker News coverage.** A domain-
   restricted Algolia search came back empty for the large majority of Winter
   2025 companies tried during development (e.g. `tryegress.com`: 0 hits). This
   is the normal shape of the data, not a bug — `hn.find_traction` returning
   `None` had to be a first-class, commonly-hit path, not an edge case.
3. **A naive single-bucket keyword filter is too loose to be worth calling a
   filter.** Matching any of `["agent", "automat", "ai", ...]` kept 125 of 167
   companies — including drug discovery and air-traffic-control startups that
   share no vocabulary with the thesis at all beyond the word "AI."

## Decision

**Relevance filter is a loose two-bucket keyword AND** (`yc.rank_candidates`):
a company must hit at least one *capability* keyword (agent, automat, copilot...)
**and** at least one *workflow* keyword (billing, compliance, scheduling...) to
score above zero; matches are then ranked by total hit count, not hard-gated
further. Deliberately not a classifier — the analyse stage's thesis-scored LLM
call is where the real judgment call happens, including scoring an off-thesis
candidate down to a clear Pass. Sourcing only needs to get a reasonably relevant
pool in front of that judgment, not replace it.

Even this loose filter needed one real correction: bare `"support"` matched
Miyagi Labs (an exam-prep tutor) via "we currently **support** the SAT, ACT..." —
generic English usage, not the customer-support sense intended. Replaced with
specific phrases (`"support team"`, `"support rep"`, `"customer support"`,
`"support ticket"`, `"support queue"`) after checking the fix against the full
167-company batch didn't drop any of the six known-relevant companies used in
`tests/test_source_yc.py`.

**Missing HN traction is not an error.** `build_candidate` falls back to a
`yc_batch` traction signal (batch admission is itself a freshness signal,
already backed by the YC-listing evidence) whenever `find_traction` returns
`None` — expected to be the common case, not the exception.

**Cached HTML bodies are capped at 300,000 characters** (`source.MAX_HTML_BODY_CHARS`),
JSON responses never truncated. Homepages are modern JS-SPA bundles that can run
1–1.5MB for a single marketing page, and only the `<meta description>` (near the
top) or the YC page's `data-page` blob (observed up to ~120KB into the page) is
ever actually read from them. Cutting the raw `data/raw/` cache from 8.25MB to
4.8MB on the real Winter 2025 run cost nothing functionally — same 15 candidates,
same founder counts, same two HN hits — since nothing past the cap was ever
being read anyway.

## Consequences

- The keyword lists in `yc.py` are a real surface for future tuning; a change
  there should be re-checked against `tests/test_source_yc.py`'s real-batch
  fixture and, ideally, a fresh look at the full live batch (see
  `tests/test_source_live.py`, run manually via `-m live`).
- Because sourcing is deliberately permissive, a materially larger share of the
  quality bar sits on the analyse stage actually holding the thesis line —
  scoring an irrelevant candidate down convincingly is not a nice-to-have, it's
  load-bearing for the whole design.
