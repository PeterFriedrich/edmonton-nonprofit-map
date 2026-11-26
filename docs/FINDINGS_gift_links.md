# Findings: gift links between charities (audit run 2026-11-26)

Target: the gift links shipped 2026-11-24 (`src/build_gifts.py`, their use in
`src/build_site_data.py`, the card text in `site/app.js`). This is the first run on
this target. It was a decision audit, top-down, with correctness checks at the code
level. The decision under audit is the 2026-11-24 row in `docs/DECISIONS.md` and
`docs/SPEC_map.md` §4 "Gifts". All counts come from the raw files as of 2026-11-24
(`data/raw_manifest.json`).

## Verdicts by level

| Level | Question | Verdict |
|---|---|---|
| L0 | Should gift links be published at all? | SOUND |
| L1 | Universe: only the giver's org-table period, only map-to-map links | SOUND |
| L2 | Join: an exact well-formed donee BN that is a map charity proves the link | **CONDITIONAL** |
| L3 | Amount: `Total Gifts`, else `Gifts in Kind`, summed per pair, then banded | SOUND |
| L4 | Code: parsing, ordering, symmetry, flags | PASS |

**L0 — SOUND.** The data is CRA's published T3010 schedule, and it names
organizations, never people. `Donee Name` is never written out.
- *Sharpest counter-argument:* gifts mostly show funders' grant lists, not similarity
  of work (only 19% of pairs share a CRA category). The spec presents them as a second
  relation and keeps them out of placement, so they don't distort the main view.
- *Would change it:* a reader taking a gift link as a statement that two charities
  work together.

**L1 — SOUND.** On the real data the period filter never fires: no map giver has gift
lines for another period, and no giver has two `Form ID`s in its period.
- The "Received from" list counts only givers on the map, and the card label says so.
- 12 self-gifts are logged and appear on no card. That is small and intended.
- *Would change it:* CRA adding multi-period or amended returns to the file. The
  filter would then start to matter, and `test_only_the_givers_period_counts` guards
  it.

**L2 — CONDITIONAL: a well-formed BN on the map is not proof either.**
- The 2026-11-24 work measured typos that land *off* the map (84 lines: the name
  matches a map charity but the number doesn't). It did not measure the reverse:
  mistyped numbers that land on *another* map charity. Those are linked, and they show
  on both cards as a gift that never happened between those two.
- *Method:* for each of the 2,768 linked lines, compare the words of `Donee Name` with
  the legal and account names of the charity holding the BN, ignoring common words
  ("society", "foundation", "Edmonton", …).
  - 140 lines (71 distinct name pairs) share no word.
  - Read by hand, most of these are operating names, acronyms or renames ("E4C",
    "Pregnancy Care Centre" for Outreach for Life, "Edmonton Food Bank" for the
    Gleaners Association).
  - **12 lines are clearly a different charity:**

    | Donee name filed | Charity holding the BN |
    |---|---|
    | Dress for Success, Red Deer | Centre for Family Literacy |
    | Edmonton Food Bank | Ronald McDonald House |
    | Edmonton Symphony | Hope Mission |
    | Government of Alberta | University of Alberta |
    | Movember Canada | Norwood Child & Family Resource Centre |
    | Brooks & District Health Foundation | Brain Care Centre |

    The other six are of the same kind.
  - **About 13 more are uncertain.**
- *Size:* roughly 12–25 of 2,768 linked lines (0.4–0.9%). This is a lower bound,
  because lines that share a word were not read.
- *Why CONDITIONAL and not UNSOUND:* the error is small, and the fix the decision
  rejected (matching by name) would add more risk than it removes. The level holds
  only if a reader sees these links as "as reported to CRA". Today the card doesn't
  say that.
- *Would change it:* a full read of the linked lines that finds a rate well above 1%,
  or the error sitting in the busiest cards.

**L3 — SOUND.**
- Every non-blank amount in the whole file parses (0 unparseable, no `NaN`/`inf`
  strings). There are no negatives, and 2 zeros.
- 216 repeated identical (giver, donee, amount) lines exist among map givers. Only one
  group is linked, and collapsing every repeat changes no pair's band. Only 1 of 8
  links with no amount has `band: null`.
- `Associated = Y` (540 lines, gifts to an associated charity) is not shown
  separately. That is a possible future refinement, not a defect.

**L4 — PASS.**
- Givers' BNs are already clean: 0 rows differ from their stripped, upper-case form.
- Both lists sort largest first, with ties by BN.
- The malformed-number flag and the "not linked" count match `Gifts.stats`.
- The card note says "recipients not linked on this map". That is accurate even for
  the lines with a typo, whose recipient *is* on the map.

## Fix options for L2 (the owner decides)

1. **Caption only:** the card says the gifts are as reported to CRA, and that a
   mistyped number can name the wrong charity. No data change.
2. **Withhold on a name mismatch:** don't link a line whose donee name shares no word
   with the BN's charity. Names would be used only to *withhold* a link, never to make
   one. This removes the 12 clear errors, but also about 115 correct alias lines.
3. **Hand-kept exception list** of BN–name pairs read as wrong. Precise, but it needs
   upkeep with each CRA year.

Recommended: option 1 now, plus a test that fails if the count of linked lines with
no shared name word moves more than a set margin. That way a new CRA year can't double
the error without a red test.

## What this run got wrong

- **The 2026-11-24 typo count, which I relied on at first, covers only half the
  class.** I carried "84 mistyped numbers" into the CRA note draft
  (`/home/opc/research/edmonton-nonprofit-map/cra_note_draft_2026-11-25.md`) as if it
  were the whole problem. The on-map typos above were found only because a repeated
  line put two different names under one BN. The draft needs a sentence on them.
- **The hand classification rests on my own knowledge of Edmonton organizations** and
  wasn't checked against any source. Calls like "Kokopelli is now Korora" or "Richard
  Eaton Singers is now Chorus Inspira" were made from memory and could be wrong in
  either direction.
- **The common-word list decides what "shares a word" means.** Dropping "centre",
  "church" and "fund" pushed some cases into the reviewed set and could have hidden
  others: two different "… Church" charities that share a place name would pass
  unread.
