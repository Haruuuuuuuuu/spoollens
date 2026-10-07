# Release-preparation validation

The runtime and coordinate-free README were frozen before the new report's first-use test. The report and expected answers were separately frozen before execution. The tester did not implement the data or product and received no field positions, rule JSON, source code, or developer coaching.

- [Independent blind workflow](usability/BLIND-USABILITY-REPORT.md): 4m42s end-to-end; three visual fields, inherited context, explicit ignores, provenance, save/reopen/replay and safe exception output completed without regex or code/template authoring
- [Independent technical comparison](validation/REPORT.md): 45 automated tests; exact original A/B/C rows, 47 physical lines and 36 origins; unseen report's 18 candidate rows, 39 physical lines and 72 origins matched its pre-frozen oracle
- [A/B/C result](validation/abc-bed54bc/report.json) and [unseen result](validation/unseen-bed54bc/report.json): exact accounting, source immutability, deterministic artifacts, conservative export, and exception evidence all passed
- [Clean-install record](validation/first-run/RESULT.json): new Linux/Python 3.12.14 checkout and virtual environment; README install commands, installed UI, bundled example, CLI and tests passed. The unauthenticated private GitHub clone was unavailable, so a content-verified local Git clone was used. Public clone availability was not claimed
- [Hygiene and naming review](hygiene-and-name.md): current-tree files and synthetic assets reviewed; historical execution metadata still requires an owner publication decision

## Recorded documentation correction

The original tester's `Page heading` label was rejected because ignore names are lowercase identifiers. The tester recovered independently. The final README now states the existing label restriction explicitly. No runtime or acceptance rule changed, and the original mistake and timing remain in the blind report. A direct input recheck confirmed that the invalid label leaves the rule unchanged and `page_header` succeeds.

A separate correction during installation changed the documented exception member filename from `rows.csv` to `*.exception.csv`; the tester recorded it before authoring, without restarting the clock.

## Evidence integrity and disclosure

`unseen_input/` and `unseen_truth/` are unchanged synthetic originals. `unseen_truth/FREEZE.json` has SHA-256 `f8cafe2f33c3f9d8d33d3054854ee7b0b847d6325cd89f16434fd6f701d75c99`. The file named `PRIVATE_ACCEPTANCE_POLICY.json` was withheld during the blind attempt; it is included here only after outcomes were frozen. Do not expose it to a future tester using this report as an unseen task.

The original fresh-use terminal and installation records remain preserved outside this public evidence copy. Here, anonymous execution-path prefixes were replaced with `<WORKSPACE>`, `<PYTHON_RUNTIME>`, or `<USER_HOME>`; raw terminal controls were otherwise preserved. These redacted recordings are not new untouched captures. `ORIGINAL-CAPTURE-HASHES.sha256` retains original artifact hashes; the adjacent `CANDIDATE-ARTIFACTS.sha256` verifies the distributed copies. Source reports, saved rules, exception ZIPs, expected answers, and outcome values were not modified.

The original validation report describes its tested candidate, and is not relabeled as a final-commit run. Final exact-tree identity, installed checks and GitHub Actions are verified separately. Agent-based tests do not establish representative human usability or business correctness.

## Reproduce the comparisons

Install the current checkout using the main README, then use new output directories:

```sh
python docs/evidence/release-preparation/validation/validate_abc.py --help
python docs/evidence/release-preparation/validation/validate_unseen.py --release-root docs/evidence/release-preparation --cli .venv/bin/spoollens --out output/recheck-unseen
```

The unseen checker preserves the pre-frozen truth and checks the tester's original UI-authored rule and exception output. Do not rerun the one-time fixture generator to accommodate a result.
