# Frozen SpoolLens competitor task

These three synthetic reports and their manually enumerated answers were created during competitor verification, before any SpoolLens implementation. Do not edit or regenerate the frozen files to accommodate a tool. Every competitor gets the identical input bytes and extraction contract.

## Files

- `A_clean.txt`: clean inventory report, two warehouses, three accepted rows
- `B_boundaries.txt`: two pages, a form feed, repeated column headings, blank lines, warehouse changes, four accepted rows
- `C_dangerous.txt`: two accepted rows plus a shifted quantity, malformed quantity, truncated detail, unexpected notice, and two orphan details (including one on the next page)
- `reference-policy.json`: explicit, human-readable extraction and validation contract
- `expected/*.rows.csv`: accepted rows in exact CSV bytes; C is candidate/exception data only, never an allowed normal clean export
- `expected/*.provenance.json`: exact evidence for every accepted non-empty output value
- `expected/*.accounting.json`: category, reason, raw text, and context transition for every physical source line
- `expected/*.export.json`: export permission and expected errors
- `expected/C_dangerous.exception.manifest.json`: required exception metadata, including counts and input/rule/output hashes
- `FREEZE.json` and `SHA256SUMS`: freeze record and integrity manifest
- `build_frozen_fixtures.py`: one-time artifact generator with manually enumerated truth; it is not a parser and must not be used by the extraction implementation

## A task a non-programmer should complete

Open A. Visually select three detail fields: item, quantity, and price. Mark the warehouse name as inherited context, and identify the column heading, page heading, footer, and page boundary as explicit non-detail rules. Save the rule and replay it on B and C without revising it. Inspect output values and their exact source locations. Attempt a normal CSV export on C, then separately request an exception export if the tool supports that action.

Output columns, in order: `warehouse,item,qty,price`. Description remains human-readable source text but is not exported. Preserve quantity and price lexical forms after trimming ASCII spaces; price `0.20` must not become `0.2`. CSV is UTF-8, comma-separated, minimally quoted, LF-terminated, with one header row.

This task permits one inherited warehouse context, one single-line detail record type, fixed slices, and straightforward validation. No PDF, OCR, code expressions, transformation program, AI, nested context, or multiline records. A competitor that requires a template language, regex authoring, or code may demonstrate parser capability, but must not be credited with a natural no-programming workflow. Source/API evidence and directly observed GUI usability must be distinguished.

## Character and line contract

- Inputs are UTF-8 without a BOM. All bytes belong to the ASCII subset, plus LF and standalone FF controls
- Physical lines are separated only by LF (`0A`). The final LF ends the final line; it does not create an additional empty line
- A form feed (`0C`) is a one-character physical line between LFs. It is not a line separator and is not a blank line. It is explicitly ignored and clears inherited context
- A blank line is empty or consists exclusively of ASCII spaces. Blank lines do not change context and are reported separately as `WHITESPACE_ONLY`
- Source coordinates use 1-based physical line numbers and 0-based, end-exclusive character ranges. LF is excluded from line text. These inputs are ASCII, so byte and character positions coincide
- Preserve all padding and the exact source bytes. Do not normalize line endings or strip lines before identifying provenance

## Fixed layout, declared before testing

Each detail is exactly 47 characters:

- Item: range `[0,8)`, left-aligned; one uppercase ASCII letter followed by three digits, then four spaces
- Separator: `[8,10)`, two literal spaces
- Description: `[10,30)`, not exported
- Separator: `[30,32)`, two literal spaces
- Quantity: `[32,37)`, right-aligned unsigned ASCII integer
- Separator: `[37,39)`, two literal spaces
- Price: `[39,47)`, right-aligned unsigned decimal with exactly two fractional digits

Every candidate whose first four characters have the item-code shape must be validated against the entire fixed layout before it can become a detail row. A layout/value failure is `REJECTED`, not silently ignored. Check record width, separators, item, quantity, price, then required context, in that order. Exact built-in type checks or equivalent declarative constraints are allowed; the user must not have to program them.

The quantity shift in C deliberately preserves total record width and leaves a plausible but wrong quantity `1` in the naive slice. Character 38 (zero-based index 37) contains the displaced digit `7`, violating the predeclared space-only separator. The correct outcome is rejection, never a repaired value `17` or a silently accepted value `1`.

Warehouse headers start with `WAREHOUSE: `, are exactly 19 characters, and store the left-aligned uppercase warehouse name in `[11,19)`. A valid header replaces context and its source provenance. An invalid warehouse-header candidate is rejected and clears context.

Explicit ignore rules are the exact generated column heading, lines starting `INVENTORY VALUATION  PAGE `, exact `END OF PAGE`, and exact standalone FF. Page heading, footer, and FF all clear warehouse context. Column headings and ASCII-space-only blank lines preserve it. Context starts empty. Rejected details and the unexpected notice do not alter context. Thus no detail before a valid current-page warehouse header may be accepted.

## Frozen outcomes

A: HEADER 2; DETAIL 3; IGNORED_BY_EXPLICIT_RULE 3; UNRESOLVED 0; REJECTED 0; whitespace-only 2. Normal CSV export allowed.

B: HEADER 3; DETAIL 4; IGNORED_BY_EXPLICIT_RULE 8; UNRESOLVED 0; REJECTED 0; whitespace-only 3. Normal CSV export allowed.

C: HEADER 2; DETAIL 2; IGNORED_BY_EXPLICIT_RULE 7; UNRESOLVED 1; REJECTED 5; whitespace-only 2. Normal CSV export blocked, with no clean CSV artifact created.

C's only accepted rows are NORTH/C100/3/12.50 and SOUTH/C201/6/3.25. Its expected failure lines are 3 (orphan), 7 (shift), 8 (malformed quantity), 9 (unknown notice), 10 (truncation), and 15 (post-boundary orphan).

Each non-empty line must have exactly one of HEADER, DETAIL, IGNORED_BY_EXPLICIT_RULE, UNRESOLVED, REJECTED. The separate whitespace-only records plus those five categories must account for every physical line, including standalone FF.

## Provenance and exception export

Every output field's expected evidence includes source SHA-256, line, full selected character range, and exact raw substring including padding. For inherited warehouse values, the evidence additionally identifies the header line/range. A click or query must expose that same evidence, not merely repeat the extracted value.

C's accepted rows can be emitted only following an explicit exception-export request. An exception must include the accepted-row CSV and a clearly associated manifest that records `EXPLICIT_EXCEPTION`, unresolved count 1, rejected count 5, actual source SHA-256, actual saved rule SHA-256, and the fact that normal clean export was blocked. The frozen reference manifest uses `reference-policy.json` as its rule hash basis. A competitor or implementation using another native saved-rule representation must record that actual rule's hash, verified from its exact bytes; its differing hash is expected and is not a ground-truth mismatch. No other expected row, classification, source evidence, or count may be changed.

## Compare all eight requirements

1. Select fixed-width fields without programming
2. Assign an inherited header value
3. Reset or replace it correctly
4. Trace every accepted value to exact source characters
5. Account for every non-empty source line
6. Block normal export if unresolved or rejected lines remain
7. Save an open extraction rule
8. Replay the unchanged rule on another report

Record the current version, concrete steps, observed output, whether code/template/regex writing was needed, and any exact blocker. Do not call a feature absent solely because GUI execution is blocked; distinguish an untested feature from an evidenced gap. Keep any competitor-created artifacts outside this frozen directory.

Integrity check: from this directory run `sha256sum -c SHA256SUMS`. For independent usability testing later, provide only the prototype README and original reports, without these answers, policy, or author assistance.
