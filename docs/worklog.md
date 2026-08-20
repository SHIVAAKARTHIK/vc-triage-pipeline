# Worklog

> **Written by Karthik.** This is the honest running account of how this got built —
> what I tried, what the AI got wrong, what I threw away. It is not a changelog (git
> already does that).
>
> **Rules I'm holding myself to:**
> - Record the rejections, not just the accepted output. The rejections are the signal.
> - My own words. If a paragraph here reads like a model wrote it, it fails its purpose.
>
> **Honest note on timing:** most of these entries were reconstructed on 2026-08-21, in
> conversation with Claude Code, from memory and the session history — not written in
> real time as each decision happened. That's a real deviation from "never backfill,"
> made under deadline pressure. The dates below are when each decision actually
> happened, not when I wrote it down. I'd rather say that plainly than pretend this was
> kept live the whole way through.

---

## 2026-08-17 — Kickoff and scoping

AI agents can think through the context like a person would, make a decision, and
actually take the action — not just talk about it. That's what makes the work
genuinely easier without a human needed, and faster, saving real time. That's why the
"AI agents for back-office labor" thesis slice made sense to me over the other options
(dev infra, vertical AI for regulated industries) — I wanted the thesis built around
agents that actually do the job, not agents that just assist someone doing it.

## 2026-08-19 — Writing the thesis

Given the deadline, I had Claude draft the thesis first rather than writing it from a
blank page — grounded in the real sourced candidates and the direction we'd agreed at
kickoff. I reviewed it, and it reflects how I actually think about this space, so I'm
standing behind it as mine going forward.

## 2026-08-20 — Switching from Anthropic to OpenAI

Cost, and I already had an OpenAI API key set up — for Anthropic I'd have needed to pay
to get one now, and OpenAI was already ready to go. That's the whole reason; not a
quality judgement between the two.

## 2026-08-20 — Why three separate stages

Splitting the pipeline into separate stages like this makes it easy to track — the
Researcher's job is one level, and only once that's done does the Analyst come into the
picture. The budget-friendly part isn't that each section gets its own AI call — it
doesn't; Team, Product, Market, Risks, and all five scores come back from one single AI
call per company. The real saving is that Sourcing and the memo-writing step use no AI
at all, they're plain code — AI only gets called in the two places that actually need
judgement, not everywhere.

## 2026-08-20 — The eval catching a real overreach

It made me trust the system more, not less. If the eval had come back with all 5s
across the board, I'd have wondered whether it was actually checking anything. Instead
it found a real, specific problem — the analyse stage overstating what a source said
about Mastra to make the rejection sound more decisive — which proves the double-check
catches real problems instead of just rubber-stamping everything.

## 2026-08-21 — The Market section gap

The real reason isn't that market info goes stale — everything in this pipeline goes
stale eventually, that's not a special property of competitive data. The actual reason
is that the Researcher never collects anything about a candidate's competitors in the
first place — only the candidate's own YC page and homepage. So even if I told the
Analyst to name competitors, it would have zero evidence to cite for it, and our own
traceability rule would block it from inventing a competitor name with no source behind
it. Fixing this properly means adding a real sourcing step, not a prompt tweak, and
that's more scope than there's time for right now. I'd rather leave a known, documented
gap than have the AI start making uncited claims to fill it.

## 2026-08-21 — What I'd do differently with more time

I'd want to build a proper UI on top of this, so a user could actually see everything
laid out visually — instead of reading raw Markdown and JSON files.
