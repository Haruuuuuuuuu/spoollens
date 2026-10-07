# Independent final-release technical validation

## Verified candidate and scope

Runtime/README candidate: `bed54bc204b60e171dd69189f2370b119192479a` (local), tree `c9e3f1fed79b0ecab1a760ca9b16cfa0190fb140`.

The final remote commit and complete release-documentation tree have not yet been received. This report does not claim remote CI, publication readiness, or unauthenticated GitHub clone success. It records independent installed-runtime and frozen-artifact verification. No production code, frozen report, expected answer, or historical assertion was modified.

## Clean installation and first run: PASS with clone limitation disclosed

- Debian GNU/Linux 13.6; Python 3.12.14; fresh Git checkout and fresh virtual environment.
- The README's GitHub clone command was attempted. Because the repository intentionally remains private and shell Git has no credentials, it failed with `could not read Username for 'https://github.com': terminal prompts disabled`.
- A separate local Git clone was used, pinned to the candidate. The old remote baseline was independently fetched through the GitHub connector and all 118 paths/modes/blob hashes and its root tree were proved identical to the local baseline. Final-candidate remote equivalence is pending separately.
- The exact README virtual-environment and `python -m pip install .` instructions succeeded with no installation workaround. pip disabled an unwritable cache, which was nonfatal.
- Clone, environment, installation, tests and checksums took 22 seconds. Installed UI, bundled example, CLI and independent A/B/C verification were complete 2 minutes 9 seconds after local clone began. This is not the blind-authoring completion time.
- Installed module paths were verified from `/tmp` to reside under the new venv's `site-packages`; all five installed Python runtime files exactly match the checkout.
- Real 100×30 PTY: empty-rule launch, bundled-rule reopen, three-row preview, row 1 quantity provenance, clean CSV export, and normal quit succeeded. UI and CLI CSV bytes both match frozen A exactly.

Detailed commands, timestamps, paths, logs and UI transcript are in `first-run/`.

## Automated and frozen A/B/C verification: PASS

- Complete candidate test suite: **45 passed**.
- All 20 frozen fixture checksum entries passed; compilation passed.
- Independent installed-CLI comparison covers **47 physical lines, 9 accepted rows, and 36 value-provenance records** across A/B/C.
- CSV, full accounting, provenance and export decisions match the unchanged frozen expectations exactly.
- Every source line and exact source slice was independently checked against original bytes; inherited values refer to their actual headers.
- A and B clean-export; C remains blocked with one unresolved and five rejected lines, and creates no clean CSV.
- Explicit exception bundles have correct status, counts, omitted lines, embedded source/rule bytes, and every member hash.
- Repeating all artifacts at new destinations yields byte-identical CSVs, sidecars and exception ZIPs.
- All source, rule and frozen-truth bytes remain unchanged.

Machine-readable result: `abc-bed54bc/report.json`; invocation record: `abc-bed54bc/commands.json`.

## Unseen blind-workflow artifact comparison: PASS

Truth was frozen at `2026-10-07T06:53:06.991209+00:00`. Its complete manifest was independently verified before tester outcomes were received. Tester outcomes were frozen at `2026-10-07T06:59:13Z`; no truth, coordinates or coaching were supplied by this validator.

After the attempt was complete, the tester's saved initial/final rules were replayed with the separately installed CLI:

- Both stages classify all **39 physical lines** with exact raw text and context transitions. The frozen policy explicitly permits custom ignore labels; only `page_heading`, `column_heading` and `page_complete` differ in spelling from the oracle's labels, with identical literal matching and reset intent.
- Before explicit note handling: 18 details, 4 headers, 11 ignored, 1 unresolved, 1 rejected, plus 4 whitespace-only lines. Clean export is blocked and produces no CSV.
- After explicit note handling: 18 details, 4 headers, 12 ignored, 0 unresolved, 1 rejected, plus 4 whitespace-only lines. The malformed business detail at line 12 remains rejected. Clean export remains blocked and produces no CSV.
- All **72 provenance records** match the pre-frozen canonical output exactly, including ranges, raw substrings, hashes and header lineage. There are zero field-coordinate differences. The tester authored one additional harmless leading-space guard `[1,3)`.
- The explicitly marked exception CSV is byte-identical to the pre-frozen CSV, SHA-256 `4607522c15c714ab86c92c44a6397e11f687a1dcad32f7faef457e4820883d2d`.
- The original UI exception ZIP, fresh-process tester replay, and independent installed-CLI replay are byte-identical. Every embedded source/rule/member hash is correct.
- The original source and all oracle files remain unchanged. No acceptance criterion was revised after seeing results.

Machine-readable result: `unseen-bed54bc/report.json`; invocation record: `unseen-bed54bc/commands.json`.

## Audit/provenance text fix: PASS

The candidate adds horizontal and vertical evidence scrolling, clipping indicators, Home/End, Page Up/Down, full status/paths, and blocked-export dialogs containing the actual problem lines. Four new automated regressions passed. In a real terminal, End exposed the previously clipped source-path suffix and the end of a long successful-export receipt at character offset 1868. Exact quantity provenance displayed the original hash, line, range and raw substring before returning to highlighted source.

## Remaining verification

Await the final frozen full-tree SHA, independently compare it to the remote, and rerun final installation/tests/frozen checks against that exact tree. GitHub Actions, naming, repository hygiene, license checks and demo review are separate release-review inputs; this validator does not substitute local test success for those checks.
