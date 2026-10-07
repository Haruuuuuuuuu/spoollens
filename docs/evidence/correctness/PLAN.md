# Independent SpoolLens correctness verification

Prepared before receiving an implementation candidate, 2026-10-07 03:33 UTC.

## Independence and limits

The verifier reads the original user execution request and frozen contract. It does not implement or change SpoolLens, does not change frozen truth, and does not give truth or UI help to the independent usability tester. Execution is against a supplied stable commit in a disposable checkout. Verification artifacts remain outside the implementation checkout unless the owner chooses to commit a report.

This is a black-box contract check, not a second extraction implementation. Expected classifications and rows for the small additional reports are explicitly enumerated below and in `prepare_evidence.py`. The helper only constructs report strings and attaches selected-source evidence. It does not classify unknown input or derive expected rows from the candidate.

## Frozen evidence checks

1. Verify all 20 hashes listed in the original SHA256SUMS before and after execution.
2. Independently check the 47 physical source lines and all 36 non-empty output-field provenance records against exact source bytes: source hash, 1-based LF physical line, 0-based end-exclusive selected range, raw padded substring, trimmed lexical value, inherited header line/range.
3. Check CSV bytes exactly for A, B and C's explicit exception data. Preserve `0.20`, LF and column order.
4. Check every physical line has exactly one record and every non-blank line is exactly HEADER, DETAIL, IGNORED_BY_EXPLICIT_RULE, UNRESOLVED or REJECTED. Standalone FF must remain a non-blank physical line.
5. Check exact frozen classifications, context-before/context-after transitions, and explicit C error positions. A counts 2/3/3/0/0; B 3/4/8/0/0; C 2/2/7/1/5 in category order above.
6. A and B normal CSV exports succeed. C default export fails and creates no clean CSV artifact; a separately explicit exception export contains only the two accepted rows and associated status, counts, input hash, actual saved-rule hash, and CSV hash.
7. Query one direct field and one inherited field through a documented public interface, checking returned location and raw source.
8. Save/reopen/replay one rule against A/B/C in new processes, using exact rule bytes. Compare result and output hashes; verify source and rule bytes unchanged. A differently formatted but semantically identical JSON copy may have a different rule hash, which must reflect its actual bytes.
9. Install in a fresh virtual environment using README instructions and run packaged tests. Record exact candidate SHA and commands; separate package tests from independent assertions.

## Predeclared ordinary variations

These remain within one single-line detail type and one inherited warehouse type. They are not a new product scope or an unbounded security-fuzz campaign.

- V1: Ordinary unseen data, same columns: WEST/Z999/0/0.00, WEST/M321/99999/12345.67, CENTRAL/Q007/7/0.20. All valid, exact values and provenance. This guards against fixture-name/value special casing.
- V2: Isolate each context-reset rule, rather than only the frozen chained footer/FF/page-heading sequence. After each individual footer, FF or page heading, a detail before a fresh warehouse header is rejected. Blank and repeated column header preserve context. Exactly four accepted details and three rejected orphans.
- V3: An unknown notice and malformed quantity occur between two valid details under one warehouse. They remain UNRESOLVED and REJECTED respectively; the later valid detail keeps the same inherited header origin. Exactly two accepted rows, one unresolved and one rejected.
- V4: A valid warehouse is followed by a malformed warehouse candidate. The bad header is rejected and clears prior context; the next otherwise-valid detail is an orphan. A new valid warehouse permits extraction again. Exactly two accepted rows and two rejections.
- V5: V1 bytes with the terminal LF removed. Same physical lines, rows and ranges, different source hash; no synthetic trailing blank line.
- E1: V1 with an invalid UTF-8 byte. Under an explicit UTF-8 rule it must fail closed with a visible decoding failure and no clean CSV artifact. This tests the requested explicit encoding and safe export, not additional encodings.

Expected variation evidence is frozen by a separate SHA256SUMS before candidate execution. No expectation may be rewritten to match candidate output. If a check fails, preserve the first failure, report it, and only rerun against an explicitly supplied new candidate.

## Stopping condition

Complete after the frozen reports, predeclared variations, provenance query, serialization/replay, source immutability and fresh install have a recorded result on a stable candidate. If a material bug is repaired within the authorized probe, verify the supplied replacement SHA and rerun affected checks and the full frozen suite. Do not publish, create another repository or expand features. User deadline: 2026-10-07 08:30:10 UTC.
