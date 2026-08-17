# Investment Thesis

> **Status: TO BE WRITTEN BY KARTHIK — do not ship the repo with this skeleton unfilled.**
>
> This document is the spine of the whole pipeline. Every score the system emits is
> a score *against this thesis*, so if this is vague the scores are meaningless
> (an explicit anti-pattern in the brief). Write it before the analysis code exists,
> and be prepared to defend every line of it in the interview.
>
> Delete this blockquote when you've written the real thing.

## The slice

*One paragraph. What do you invest in? Be narrow enough that a reader could correctly
guess your Pass/Watch/Meeting call on a company you haven't seen yet.*

Working direction (agreed at kickoff — rewrite in your own words, and change it if you
disagree): seed-stage startups selling **AI agents that take over a specific back-office
workflow** — support, claims, bookkeeping, compliance, collections, ops — for SMB and
mid-market buyers who **already pay humans to do that work**.

Questions this paragraph must answer:

- Which workflows count, and which are out of scope?
- Which buyer? (SMB vs mid-market vs enterprise — pick, don't hedge.)
- What stage and what cheque size are you writing?

## Why now

*Two or three sentences. What changed in the last ~18 months that makes this a
window rather than a permanent condition? "LLMs got good" is not an answer — be
specific about what it unlocked for this slice.*

## What I explicitly do not invest in

*A list. This is where the thesis earns credibility — an anti-portfolio is harder
to fake than a portfolio. Three to five bullets.*

- e.g. seat-priced copilots that sit next to the existing workflow rather than replacing it
- e.g. ...

## Scoring dimensions

*These become the weights in `src/triage/scoring.py`. The model rates each dimension;
Python computes the total. If you change a weight here, change it there — and be ready
to justify the split.*

| Dimension | Weight | What a 10 looks like | What a 0 looks like |
| --- | --- | --- | --- |
| Workflow ownership | ?% | | |
| Buyer pain / budget already exists | ?% | | |
| Team–domain fit | ?% | | |
| Technical depth | ?% | | |
| Wedge defensibility | ?% | | |
| Traction / freshness signal | ?% | | |

Weights must sum to 100.

## Call thresholds

*Where do the cut lines sit, and why there?*

| Score | Call |
| --- | --- |
| ?–100 | Take a meeting |
| ?–? | Watch |
| 0–? | Pass |

## Known blind spots

*What will this thesis systematically get wrong? Naming this yourself is worth more
than pretending it's airtight.*
