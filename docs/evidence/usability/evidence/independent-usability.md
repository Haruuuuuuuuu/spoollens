# Independent SpoolLens usability test

## Result

The requested README-guided workflow completed through the real interactive terminal UI, without editing a template, JSON rule, regex, or product code. The tester did not implement the prototype and received no author assistance.

- Candidate: `0f04a3ae959460721b0b2142acb72306d2c7ec15`
- Separate detached checkout: `spoollens_independent`
- Start: 2026-10-07 03:59:07 UTC
- Required workflow complete: 2026-10-07 04:03:06 UTC
- Total required-workflow wall time: **3 minutes 59 seconds**
- Environment: cloud Linux, interactive PTY, `TERM=xterm-256color`, 120 columns by 40 rows
- The parent authorized starting the independent test at 03:58:59 UTC, earlier than the original hour-five schedule. This timing deviation must not be represented as a six-hour-long run.

This is an independent agent-operated interaction test, not a representative human non-programmer usability study. The README provides the exact coordinates and boundary choices for these fixtures; completion does not establish discoverability on an unfamiliar report.

## Isolation

Before the timed test, the tester saw the user's task, performed only terminal capability preflight, and received the candidate commit/path. The test began from that commit's README and the original report files. No implementation, tests, example rules, expected answers, or fixture-policy documents were read before the required workflow completed. Frozen expected artifacts were first inspected after completion, for a separate correctness check. Product implementation and tests were never needed.

## Installation

Created a new virtualenv with access to preinstalled system packages, then followed the optional README installation command: `python -m pip install --no-build-isolation --no-deps .`. The wheel built, installation succeeded, and the installed `spoollens` command displayed help and ran the UI. No package download was needed. The environment already supplied pip and setuptools; this is not a test of provisioning Python on a clean operating system. A non-fatal pip cache-permission warning appeared.

## Actual workflow

1. Opened `A_clean.txt` with the installed UI. It started with no rules and eight unresolved non-empty lines.
2. Used `g`, Space, arrow keys, and highlighted selections to mark item `[0,8)`, quantity `[32,37)`, and price `[39,47)`. Chose the named fields and accepted adjacent-space checks in UI menus.
3. Selected warehouse `[11,19)` on line 2 and confirmed inherited context.
4. Selected the page-heading prefix and explicitly cleared context; marked the exact column heading while preserving context; marked the footer while clearing context; enabled the explicit standalone-FF boundary rule.
5. Exported A through `e`. Three rows plus audit/provenance/manifest files were created.
6. Inspected output row 1's warehouse with `v`. The UI showed the source SHA256, header line 2, range `[11,19)`, and exact raw substring `NORTH   `; closing the evidence view jumped to and highlighted those source characters.
7. Saved `inventory.rule.json` through `w`, then reopened it with `l`. The rule hash stayed unchanged.
8. Opened B through `o` without changing rules. Four rows were accepted and exported. Inspected row 4's warehouse: EAST, header line 14, range `[11,19)`, exact raw substring `EAST    `, detail line 17.
9. Opened C. The UI showed two accepted rows, one unresolved line, five rejected lines, and blocked clean export.
10. Used `n` and Enter to inspect every problem. Orphans at lines 3 and 15 had no warehouse context; line 7 had a quantity character in the required separator; line 8 contained `2O` instead of an integer; line 9 was an unmatched notice; line 10 had the wrong record width.
11. Attempted `e` on C. The UI explicitly refused and said no CSV was created.

## Mistakes and documentation

- One harmless navigation mistake: pressed `v` while the successful-export confirmation was still open. The key was ignored; Enter closed the modal, after which `v` worked. No incorrect extraction rule or output was produced.
- README was needed for installation, source line/character coordinates including padding, selection controls, context reset choices, the FF rule, provenance inspection, and saving/reopening/report-switch commands.
- No documentation beyond README was needed during the required workflow. No author question was asked.
- No regex, template language, JSON editing, or code was needed for authoring, inspection, export, save/reload, or diagnosis. Subsequent evidence comparison used ordinary test-side Python and shell commands, after timing ended.

## Biggest UX weakness

The successful path is strongly tutorial-dependent: the README supplies exact padded column ranges, clear/keep choices, and filenames. It does not show that a non-programmer could infer these choices on an unfamiliar report. Error explanations also expose technical reason codes and long JSON. At 120 columns, the truncated-record audit's `actual_width` portion and export-manifest tail were horizontally clipped; the visible reason still allowed diagnosis, but the full structured detail was not readable in that view. The row preview shows only a few rows and requires `v` to inspect others.

## Additional checks after timing ended

- Requested and confirmed the explicit C exception export through the UI. Its manifest records `EXPLICIT_EXCEPTION`, one unresolved, five rejected, input/rule hashes, and omitted line numbers.
- Quit and started a new UI process, loaded the independently authored rule, exported A again, inspected inherited provenance, opened C, and reconfirmed export blocking. This second interaction is preserved in `fresh-process-reopen.typescript`.
- Fresh-process A CSV, accounting, and provenance exactly matched the original UI export.
- Original report bytes matched the tested git commit after all interactions.
- Only then compared output to frozen ground truth. A and B CSV bytes, all three reports' complete accounting, and all three reports' provenance matched exactly. C's candidate rows came only from the explicit exception bundle and matched its frozen candidate rows.
- Independently recomputed all 36 accepted-value origins directly from the original report bytes: source hash, line, range, raw substring, normalized value, and inherited header coordinates all matched.
- Replayed the UI-authored rule through the installed CLI only after usability completed. A/B CSV bytes matched UI exports. C clean replay returned exit code 2 and left no CSV. Every C exception-bundle member matched its UI counterpart byte for byte.

## Accounting

| Report | HEADER | DETAIL | IGNORED_BY_EXPLICIT_RULE | UNRESOLVED | REJECTED | Blank | Physical lines |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 2 | 3 | 3 | 0 | 0 | 2 | 10 |
| B | 3 | 4 | 8 | 0 | 0 | 3 | 18 |
| C | 2 | 2 | 7 | 1 | 5 | 2 | 19 |

All non-empty lines were accounted for. No unsafe clean C output existed.

## Hashes

- Input A: `f1c4b2aacdc53d76ffde2d809ce1d4634dc5e48a02fa71606df03e36c509e658`
- Input B: `f8c475c6f0764523425512514b3065dd9b5a549f3bda24c9414c28af27cc8868`
- Input C: `318f02610fa08f95b8018f5dd690433ec30ad003a496c15aee4059c457ce4a77`
- UI-authored rule: `85807556db918f1ba7d923c726e62bca3f501980245d611114367e4529a07686`
- A clean/reopened CSV: `1c49a81800d6fdf96bb292e684db86b19b7c00213ea46642eae7ed44198859e7`
- B clean CSV: `176a947371746d16a3a937178bd380913e18ff5470214645d792643fa2f14ac6`
- C exception CSV: `4dce295d70f1bd7370b6e0fb7ea890506ef8945696cf08c37ff599f30e8f655c`

## Evidence files

- `../inventory.rule.json`: independently UI-authored rule
- `../output/`: UI clean exports, evidence sidecars, and C exception bundle
- `fresh-process-reopen.typescript`: raw ANSI terminal recording of independent fresh-process reload, re-export, provenance jump, and C block; the original full authoring session is in the execution tool transcript and was not retrospectively reconstructed
- `post-usability-validation.json`: frozen-output, exception integrity, reload, and absence checks
- `source-and-cli-validation.json`: source recomputation, full accounting, and UI/CLI parity
- `cli/`: post-usability replay outputs and exit evidence

## Scope conclusion

This candidate passed the specified synthetic README-guided, no-programming interaction workflow and the independent output checks. It demonstrates interaction feasibility. It does not by itself establish general report authoring, customer demand, or non-programmer usability beyond this documented layout.
