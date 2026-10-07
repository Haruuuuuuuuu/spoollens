# SpoolLens independent unseen-report usability attempt

## Frozen outcome

**Workflow result: PASS, with one recoverable label-wording defect.** This is a result for the assigned usability gate, not a publication authorization or an assertion that all release gates passed.

The independent tester produced a UI-authored, saved/reopened extraction rule and an explicit exception ZIP with 18 candidate CSV rows. The genuinely malformed business row remained rejected. No source data was repaired, discarded through an ignore, or silently rewritten. Normal clean export remained blocked.

Expected-result correctness was deliberately **not** checked by this tester. A separate auditor can now compare the frozen outputs with the independently frozen expected result. This report's workflow assessment precedes that comparison.

- Initial candidate: `898d11525a4b7345bc1a4083f60c414463780e11`
- Public README initially read: SHA-256 `44cf0fae6a305acbab394b11403d5ddde5bcc25a81bf682ffc72254110eaf598`
- Corrected documentation candidate used before report authoring: `bed54bc204b60e171dd69189f2370b119192479a`
- Corrected README SHA-256: `9c0765c9c668d6e211d2ea4ac99ba9c72dc3adbbe8965b64cafed19f48e13329`
- Source SHA-256, before and after: `65248ab62aa3ceb0054c25fd9e524070638bd617b4cdf1821304283116c4900e`
- UI-reported final rule SHA-256: `f91c1784b089f52eb95f77020b2bbee3a65050b101438a523f4bbe0800592388`
- Outcome frozen at: 2026-10-07 06:59:13 UTC

## Independence and permitted starting material

The tester did not implement the product or dataset. Before starting, the tester read only the user's release-preparation mission and the parent's procedural assignment. Product authoring began only after a fixed candidate and public README were supplied.

Starting material was the public README, `unseen_input/TASK.txt`, and the new synthetic `workshop-replenishment-06a.txt`. The raw report was first viewed inside the running SpoolLens terminal UI. No implementation, tests, bundled rules, example JSON, previous coordinates, dataset generator, frozen expected result, or private authoring evidence was inspected. No clarification about report coordinates or meaning was requested from the author or parent.

The parent notified the tester during installation that a README-only correction had been committed: the exception CSV is named `*.exception.csv`, not `rows.csv`. The tester recorded this change and inspected only the README diff. The installed runtime was built from the initial SHA; the checkout then moved to the documentation-only commit. No runtime change or authoring assistance was supplied. The initial clock was not restarted and the initial defect has not been erased from this record.

## Timing

| Milestone | UTC | Elapsed from start |
|---|---|---|
| Fresh clone, fixed SHA, first public README read | 06:54:31 | 0:00 |
| Fresh virtual environment installation completed | By 06:55:08 | 0:37 |
| Raw report opened in actual terminal UI | 06:55:26 | 0:55 |
| Three detail fields and inherited context defined; preview available | 06:56:30 | 1:59 |
| Initial rule saved; UI closed | 06:58:09 | 3:38 |
| UI restarted; saved rule reopened; unsafe clean export blocked | 06:58:20 | 3:49 |
| Informational note precisely ignored; final rule saved; malformed row still blocks clean export | 06:58:37 | 4:06 |
| Explicit exception ZIP saved through UI | 06:58:48 | 4:17 |
| CLI replay and blocked export checked; source immutability verified | 06:59:13 | 4:42 |

**End-to-end completion: 4 minutes 42 seconds.** First permitted UI output: 4 minutes 17 seconds. The period waiting for the fixed candidate before 06:54:31 was excluded. There was no personal/agent idle interval during the timed attempt; install processing and tool latency remain included. Evidence-writing and auditor comparison are excluded. This is an agent-based keyboard usability probe, not a representative human timing study.

## Environment and installation

- OS: Linux x86_64, kernel `6.18.44`, host reported by `uname -a` in `install.log`
- Python: 3.12.14
- Terminal: real PTY, `TERM=xterm`, 120 columns by 40 rows
- Fresh local clone with `--no-hardlinks`, detached at the supplied SHA
- Fresh `.venv`; README commands `python3 -m venv .venv`, `. .venv/bin/activate`, and `python -m pip install .`
- Installation succeeded without a workaround or runtime dependencies
- Only install warning: pip cache was unavailable/unwritable, so pip disabled caching
- README's public GitHub clone command was replaced by cloning the supplied frozen local repository. Thus this attempt verifies fresh-clone/venv installation, not public GitHub availability or remote authentication. The repository was intentionally private

Actual launch command:

```sh
stty cols 120 rows 40
TERM=xterm script -q -f ../terminal.typescript -c '.venv/bin/spoollens ui ../../unseen_input/workshop-replenishment-06a.txt'
```

The UI was operated with physical keyboard commands through the PTY: navigation, selections, menus, labels, and filenames. No extraction rule was created or edited through JSON, source code, a template, or a regex.

## Required workflow observations

1. **Install:** succeeded in a new virtual environment using the documented install commands.
2. **Open report:** opened the new raw report read-only with an empty rule.
3. **Visually define detail fields:** independently located the padded `item`, `qty`, and `price` fields using printed column headings, report rows, and the UI character ruler. `g` was used only with positions identified from that view. In particular, the six-digit quantity and wide price rows made full field widths visible. Accepted the UI's adjacent-space guard suggestions after checking the layout.
4. **Inherited context:** selected the `DISPATCH STORE` value and used `h`. Preview reflected the later store changes. No supplied coordinates were used.
5. **Explicit ignores:** defined a stable page-heading prefix with Clear context, exact column headings with Keep context, and the exact page-complete footer with Clear context.
6. **Unresolved/rejected inspection:** used `n` and Enter. The informational planner note was UNRESOLVED. The malformed M499 row was REJECTED because a digit occupied a required separator. Both audits showed complete exact raw source text, classification, reason, and source hash.
7. **Preview:** candidate values were shown live as rules were created. The menu permitted inspection of every candidate row, beyond the three-row preview area.
8. **Exact provenance:** inspected row 2 quantity `104205`: physical line 6, range `[39,45)`, exact substring `104205`, and full source hash. Also inspected row 10 inherited warehouse `HANGAR`: header line 23, range `[17,24)`, exact padded substring `HANGAR `, and detail line 24. Closing each evidence window highlighted the source characters.
9. **Save rule:** used `w` to save `authored-rule-initial.json`.
10. **Close and reopen:** quit, launched a second real UI session on the same report, and used `l` to reopen the saved file.
11. **Replay:** the UI recomputed the same candidate preview and status; the saved rule hash matched. Final CLI replay was also tested.
12. **Attempt unsafe export:** pressed `e` while the planner note was unresolved and the business row was rejected. The UI stated that no CSV was created.
13. **Understand blocking:** the blocking explanation listed both affected physical lines and their exact source text, instructed the user to investigate, and identified the explicitly incomplete-data `x` route.
14. **Handle explicitly and validly:** after reading the planner note, created an exact whole-line ignore with Keep context. Did not ignore or repair M499. A second `e` attempt remained blocked with 0 unresolved / 1 rejected.
15. **Produce permitted CSV:** used `x`, explicitly confirmed EXPLICIT_EXCEPTION with 0 unresolved and 1 rejected, and saved `workshop-exception.zip`. It contains `workshop-replenishment-06a.exception.csv` plus source bytes, accounting, provenance, rule, and marked manifest. An extracted convenience copy of that candidate CSV is retained beside the ZIP; it must remain associated with its exception evidence.

## Errors, confusion, and documentation use

### Recoverable label defect

The README says to give ignores a “plain descriptive label.” The prompt asks for a “Short label.” The tester entered `Page heading`, which was rejected with: `Ignore names must be lowercase identifiers of at most 64 characters`.

The tester recovered without help by using `page_heading`. The failed rule was not retained. Subsequent labels used lowercase underscores. The error was understandable, but the initial wording does not state the restriction. A lowercase label such as `page` would also avoid code/template syntax; this was a naming constraint, not a requirement to author executable logic.

Some navigation keystrokes were batched after the first failed submission, so they were consumed in the error window and opened the source audit. The tester closed that window and retried. This was an input-sequencing mistake during recovery, not a data-rule alteration.

### Documentation lookup record

- Read the complete public README once before launching
- Read the task's plain field intent once before launching
- Read the documentation-only correction diff once before launching
- Referred to the already-read README's keyboard workflow and CLI syntax
- Did not open deep rule-format documentation, example rules, developer docs, tests, implementation, or private expected results
- No `?` help lookup was necessary; the README and on-screen prompts were sufficient

### Other UI observations

- The narrow preview shows only three rows at this terminal height, but explicitly states the total and offers `v` for every row
- Audit/evidence displays exposed the exact error source and inherited-header origin clearly
- On the long exception-export result, the right `>` marker indicated additional text. End successfully reached the far-right result text, including `normal_csv_artifact_created: false`; Home restored the left side. No hidden export evidence was required to understand the result
- The main bottom status line can still clip at terminal width, but `a`/the dedicated evidence windows and scrolling are documented. The tested error and provenance evidence remained inspectable

**Coordinates supplied by someone else:** no. **Regex:** no. **Code/template programming for extraction:** no. **Manual JSON editing:** no. **Hidden developer knowledge:** no. **Author coaching:** no.

## Determinism and safety observations after authoring

Documented final-rule CLI commands were run from the fresh clone:

```sh
spoollens replay ../../unseen_input/workshop-replenishment-06a.txt --rule ../authored-rule-final.json
spoollens replay ../../unseen_input/workshop-replenishment-06a.txt --rule ../authored-rule-final.json --output ../attempt-clean.csv
spoollens replay ../../unseen_input/workshop-replenishment-06a.txt --rule ../authored-rule-final.json --exception-bundle ../replayed-exception.zip
```

- Two plain replay summaries were byte-identical; each returned 2 because the malformed row remains rejected
- Clean CLI export returned 2; `attempt-clean.csv` did not exist afterward
- Exception replay returned 0
- UI-generated and CLI-generated exception ZIPs were byte-identical
- Source SHA-256 was identical before and after the complete attempt
- Final summary: rule complete; 18 candidate rows; 0 unresolved; 1 rejected; clean export not allowed
- No source or production files were edited by the tester

## Frozen evidence

- `terminal.typescript`: original actual ANSI terminal output of rule authoring, errors, audit, provenance, save, and quit
- `terminal-reopened.typescript`: actual second-session output of reopen/replay, blocked exports, planner-note handling, final save, explicit exception export, and horizontal scroll
- `install.log`: OS, Python, and fresh installation output
- `authored-rule-initial.json`: UI-saved rule before planner-note handling
- `authored-rule-final.json`: UI-saved rule after precise planner-note handling
- `workshop-exception.zip`: original UI export
- `workshop-replenishment-06a.exception.csv`: unchanged CSV extracted from the original exception ZIP
- `replayed-exception.zip`: CLI replay of the final UI-authored rule
- `replay-summary-1.json` and `replay-summary-2.json`: identical independent replay summaries
- `blocked-clean.stderr`: actual CLI refusal reason
- `source-before.sha256` and `source-after.sha256`: source immutability evidence
- `CANDIDATE-ARTIFACTS.sha256`: frozen hashes of the authored rules, output ZIPs, CSV, and raw terminal captures
- `outcomes-frozen-at.txt`: blind outcome freeze time

These are original terminal captures, not mockups. No screenshot has been invented or redrawn to substitute for product behavior. A separate correctness auditor should retain this report unchanged and add its own comparison result rather than rewriting the blind attempt.
