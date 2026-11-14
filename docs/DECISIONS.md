# Decisions Index

Append-only. **One ROW per locked decision** — when, what, why (including what
was rejected), and a pointer to where the argument lives in full. When a decision
locks, add a row; when one is superseded, strike it (`~~...~~`) or mark it
`SUPERSEDED <date>` in place and add the successor — don't delete history.

**What a row owes you:**

1. ⚠️ **EVERY ROW CARRIES A POINTER TO A DOC** — not only to code. Code moves;
   the argument has to live somewhere prose can hold it.
   `scripts/check_doc_citations.py` checks that every pointer resolves.
2. **The row is a self-contained summary** and may paraphrase the argument.
3. **The pointer is the authority.** When a row and its target disagree, the
   target wins and the row gets fixed.
4. **A row names the test that protects it**, or carries `[unverifiable]`.
   `scripts/check_decisions_log.py` enforces this on the merge gate (and that a
   superseded row is marked where it stands).

| When | Decision | Full reasoning |
|------|----------|----------------|
| 2026-11-14 | **v1 universe is CRA-registered charities only.** The Alberta registry's other non-profits come later as a name-only tier. Rejected: including them from the start, since the registry has no description or category to place them by. `[unverifiable]` | `docs/SPEC_map.md` §2 |
| 2026-11-14 | **Boundary is Edmonton plus the metro ring, and the division is kept.** Every org carries `area` (`edmonton` or `metro_ring`) and its municipality; the site shows and filters on it. The ring's place list is still open. `[unverifiable]` until the org table exists | `docs/SPEC_map.md` §3 |
| 2026-11-14 | **The main view is a similarity map, not a street map.** Orgs are placed by program-description similarity and coloured by category. Rejected as the main view: a street map, because the addresses are mailing addresses or postal codes. `[unverifiable]` | `docs/SPEC_map.md` §4 |
| 2026-11-14 | **No director's or officer's name in any output.** `[unverifiable]` until an output exists; a guard is owed with the first one (`TODO.md`) | `docs/SPEC_map.md` §6 |
| 2026-11-14 | **Static site on GitHub Pages**, built by a Python pipeline and deployed by GitHub Actions; no server and no tiles in v1. `[unverifiable]` | `docs/SPEC_map.md` §7 |
