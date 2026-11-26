# AUDIT LEDGER — what has been audited, when, and what came back

One row per **executed audit run**. This is the coverage map the audit docs
don't give individually: briefs are reusable *instruments*, findings docs record
*one run's output*, and the `project-audit` skill deliberately picks ONE target
per session — so nothing else says what has and hasn't been looked at. This does.

Rules: add a row when an audit **executes** (not when a brief is written); every
row carries a **pointer to the findings doc**; verdicts are **point-in-time** — a
row says the target was audited *as of that date*, not that it's still clean
after later changes. Not part of any session's mandatory reading — open it to
scope an audit or to check what has already been covered. Audits are framed
top-down, fundamental decisions first.

## Executed audits

| Date | Target / scope | Instrument | Output | Verdict (one line) | Outstanding |
|------|----------------|------------|--------|--------------------|-------------|
| 2026-11-26 | Gift links (`src/build_gifts.py`, their use in `src/build_site_data.py`, card text) | `project-audit` decision audit, L0–L4 | `docs/FINDINGS_gift_links.md` | L0, L1, L3 SOUND; L4 PASS; L2 CONDITIONAL: some well-formed donee numbers on the map are typos, so a few links name the wrong charity | Owner picks an L2 fix option; A2 in `docs/ASSUMPTIONS.md` |

## Queued — briefed, not yet run

## Never audited (candidates, roughly ranked)

- <the data join / the denominator / the published headline number …>
