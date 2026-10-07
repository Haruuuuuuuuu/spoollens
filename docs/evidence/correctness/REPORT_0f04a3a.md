# Independent correctness result: PASS

Candidate: `0f04a3ae959460721b0b2142acb72306d2c7ec15`  
Environment: Linux, Python 3.12.14, fresh isolated virtual environment  
Independent run: 2026-10-07 04:02:37–04:02:40 UTC  
Role: independent correctness verification, not implementation or independent usability

## Result

All scoped correctness checks passed. No implementation, frozen truth or expected variation result was changed. All 52 files in the disposable candidate archive still match the supplied Git commit exactly.

- A: 3 accepted rows; counts HEADER 2, DETAIL 3, IGNORED 3, UNRESOLVED 0, REJECTED 0; 2 blank lines
- B: 4 accepted rows; counts HEADER 3, DETAIL 4, IGNORED 8, UNRESOLVED 0, REJECTED 0; 3 blank lines
- C: 2 accepted rows; counts HEADER 2, DETAIL 2, IGNORED 7, UNRESOLVED 1, REJECTED 5; 2 blank lines
- Frozen CSV, complete accounting, every context transition, error line/range, and every provenance object exactly match the original truth
- All 47 frozen physical lines are accounted for once, including standalone form feeds. All 36 frozen output values match exact padded source substrings, hashes and coordinates. No silent non-empty line loss
- C clean export returns exit 2 and creates no CSV. A separately requested exception ZIP contains only the accepted rows and correctly records `EXPLICIT_EXCEPTION`, source/rule/CSV hashes, unresolved 1, rejected 5, and omitted lines 3, 7, 8, 9, 10, 15
- All five predeclared ordinary variations pass: new values and warehouse labels; each reset boundary independently; rejected/unknown lines preserving context; malformed header clearing context; absent terminal LF
- Invalid UTF-8 fails visibly with exit 1 and no clean CSV
- Across frozen and variation cases, the verifier checked 94 physical lines and 92 output-field provenance objects
- The documented `inspect` command returns the exact inherited warehouse source and direct price source for B row 2
- Repeated fresh-process exception replays produce byte-identical ZIP files. Canonically saved and differently formatted JSON rules reproduce identical rows/accounting/provenance, with each manifest hashing the actual rule bytes used
- Source reports, frozen evidence and original rule bytes are unchanged after execution
- The README's no-install direct-run route works inside a fresh venv. All 41 packaged tests pass there
- CLI and TUI both import the shared engine and use its `execute`/`export_result` entry points. No UI authoring help was supplied to the independent usability tester

## Hashes

Actual saved example rule SHA-256:

`85807556db918f1ba7d923c726e62bca3f501980245d611114367e4529a07686`

Accepted CSV SHA-256:

- A: `1c49a81800d6fdf96bb292e684db86b19b7c00213ea46642eae7ed44198859e7`
- B: `176a947371746d16a3a937178bd380913e18ff5470214645d792643fa2f14ac6`
- C exception data: `4dce295d70f1bd7370b6e0fb7ea890506ef8945696cf08c37ff599f30e8f655c`

The native rule hash differs from the frozen reference-policy hash as explicitly permitted by the pre-implementation fixture contract.

## Evidence and reproduction

- Plan authored before candidate receipt: `PLAN.md`
- Original truth audit: `original_truth_audit.json`
- Independently enumerated variation inputs/truth: `predeclared/`
- Predeclared variation manifest SHA-256: `4605fbc6ad810922b256a35198474258f494c39c9273ba844bda2a364c68b0ff`
- Verifier: `run_blackbox.py`
- Complete result and hashes: `blackbox_0f04a3a/report.json`
- All 35 CLI/serialization invocations, stdout/stderr and exit codes: `blackbox_0f04a3a/commands.json`
- Packaged test transcript: `blackbox_0f04a3a/packaged_tests.stderr.txt`
- Per-case exports, bundles, audit and provenance are under `blackbox_0f04a3a/<case>/`

Reproduce using a disposable archive of the exact candidate and a fresh Python venv. From the workspace root:

```sh
python3 spoollens_probe/verification/run_blackbox.py \
  --candidate <candidate-archive-directory> \
  --python <fresh-venv>/bin/python \
  --sha 0f04a3ae959460721b0b2142acb72306d2c7ec15 \
  --out <new-result-directory>
```

The output directory must not already exist. The verifier needs the untouched sibling `fixtures/` and frozen `predeclared/` directories. It does not import implementation code for extraction; extraction and queries use CLI subprocesses. Only rule serialization uses the documented public Python API.

## Limits

This establishes correctness for the declared narrow ASCII inventory workflow and its enumerated ordinary variations. It is not broad security fuzzing, a guarantee for other report layouts, or evidence of representative human usability. Native Windows and additional encodings are not covered. The optional pip/setuptools install route was not required or tested; the documented primary direct-run route was tested in isolation. Remote CI and repository visibility are the parent's separate checks. Independent usability must be judged separately and may still change the final verdict.
