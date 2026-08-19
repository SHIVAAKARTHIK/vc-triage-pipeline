# Investment Thesis

> **Drafting note (honesty, not decoration — see `AI_USE.md`):** this draft was written
> by Claude Code, grounded in the 15 real candidates already sourced in
> `data/candidates.json` and the direction agreed at kickoff. It has **not yet been
> reviewed, argued with, or internalized by Karthik.** Every score the pipeline emits is
> a score against this document, and it's the one page an interviewer is most likely to
> push on directly — read it, disagree with parts of it, edit it until it's actually
> yours before relying on it in a live conversation. Delete this note once it is.

## The slice

Seed-stage startups (first institutional check, roughly $500K–$3M) building AI agents
that **fully execute one specific, currently-outsourced back-office workflow** —
insurance verification, revenue-cycle billing, bookkeeping/month-end close, compliance
monitoring, trade documentation — for **SMB and lower-mid-market businesses (roughly
5–500 employees)** who today pay a person, or a BPO vendor, to do that exact task.

The workflow has to be nameable in one sentence, and the buyer has to already have a
line item — payroll, a vendor contract, an FTE — paying for it today. Not general
"AI coworker" tools with no named workflow. Not developer infrastructure sold to other
AI builders. Not consumer.

## Why now

Two things converged in the last ~18 months, not just "LLMs got good": tool-calling and
structured output made it viable for an agent to *execute* a workflow end-to-end —
submit the claim, post the reconciling entry — rather than draft something a human still
has to review and send, which is the difference between replacing a seat and assisting
one. And SMBs in exactly this labor-cost bracket (dental, veterinary, small
accounting/compliance shops) are priced out of custom software and stuck paying
$18–25/hr for people doing repetitive claims and data-entry work, so the agent-vs-FTE
ROI math is now unambiguous in a way it wasn't when every agent step still needed a
human in the loop.

## What I explicitly do not invest in

- **General-purpose "AI coworker" products with no named workflow** — real example
  already in the sourced set: Dex, "The AI Coworker in Chrome." If a company can't
  name the one task the agent owns, the thesis can't score it.
- **Developer tooling or agent infrastructure sold to other AI builders**, not to the
  SMB doing the actual workflow — Mastra, Quantstruct.
- **Vertical systems-of-record that digitize a workflow without an agent executing
  it** — Scout (a student information system is a database, not labor replacement).
- **Seat-priced copilots that assist an existing employee** rather than replacing the
  seat or the vendor contract.
- **Enterprise-only go-to-market** — sales cycles too long for a fund writing seed
  checks to underwrite.

## Scoring dimensions

Five dimensions, not six — "technical depth" and "domain background" are folded into
one `team_domain_fit` dimension rather than double-counting founder quality across two
rows. Weights sum to 100.

| Dimension | Weight | What a 10 looks like | What a 0 looks like |
| --- | --- | --- | --- |
| `workflow_ownership` | 30 | Agent executes the actual transaction end-to-end, no human step (e.g. Egress Health filing/scrubbing insurance claims) | Chat assistant that drafts something a human still reviews and sends |
| `buyer_pain` | 20 | Buyer already has a named, quantifiable cost today — a budget line, an FTE, hours/month (e.g. Toothy AI: "160 hours/month on insurance tasks") | No evidence anyone currently pays for this work at all — a hypothetical future need |
| `team_domain_fit` | 25 | Founder has direct operating experience in the exact vertical *and* the technical depth to ship the agent (e.g. Cardamon's founder ran Revolut's diversified-assets team; Cifrato's founder is technical with a prior consumer-scale exit) | No visible domain background and no visible technical background — a generalist team guessing at the workflow |
| `wedge_defensibility` | 15 | The agent accumulates workflow-specific data or integrations that compound the longer it runs (claims history, payer-specific rules, compliance precedent) | A thin prompt wrapper over a generic LLM call, replicable by a competitor in a weekend |
| `traction` | 10 | Real usage signal beyond batch admission — a paying pilot, strong HN reception, or measurable outcomes | Idea-stage; no signal beyond being accepted into the batch |

## Call thresholds

| Score | Call |
| --- | --- |
| 70–100 | Take a meeting |
| 40–69 | Watch |
| 0–39 | Pass |

70 is set so a candidate can't cross it by being strong on only one or two dimensions —
it requires real workflow ownership *and* real buyer pain *and* a passable team, since
those three alone are 75 of the 100 points. 40 is the floor where the idea is
directionally right (workflow and pain are real) but something structural — usually team
or wedge — is missing. Below 40, the thesis doesn't really apply: wrong category, or no
real pain being solved.

## Known blind spots

- **Team scoring is biased toward founders with an impressive, YC-page-visible bio.**
  A phenomenal but under-the-radar solo founder with no notable prior company or degree
  scores artificially low purely because there's no bio text to cite as evidence — the
  dimension measures *legible* pedigree, not actual founder quality.
- **The thesis bets that SMB buyers will trust an agent with the actual transaction**
  (submitting the claim, posting the entry) rather than keeping a human in the loop
  permanently. If the market instead settles on "AI assists, human stays accountable"
  as the durable equilibrium — for trust or regulatory reasons — then
  `workflow_ownership` being the highest-weighted dimension is actively wrong, not
  just an approximation.
