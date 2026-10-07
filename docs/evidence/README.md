# Validation evidence

The original correctness and tutorial checks tested runtime candidate `0f04a3ae959460721b0b2142acb72306d2c7ec15`. They are historical evidence, not a substitute for the latest release-preparation checks.

## Frozen correctness

[Portable package instructions](correctness/README.md) include the independent report, result JSON, historical invocations, predeclared variations, and checksums. Its portable verifier reproduced the original per-case results.

Original result: exact frozen A/B/C CSV, all 47 physical lines and 36 accepted-value origins, context transitions, export blocks, exception manifests, deterministic replay, source/rule immutability, five ordinary variations, and invalid UTF-8 handling passed. All 41 tests then present passed in a fresh isolated virtual environment. This establishes the narrow declared inventory contract, not exhaustive security or general-layout support.

The authoritative original acceptance fixtures and their checksum manifest remain unchanged under `tests/fixtures/`. Current tests extend coverage without changing those expected answers.

## Historical tutorial usability

The [interaction report](usability/evidence/independent-usability.md) records the procedure and limits. Its independently authored rule, actual UI exports, terminal recording, and correctness/UI-CLI parity checks are preserved with hashes.

The README-guided interaction took 3m59s without regex, template, JSON, or product-code editing. It was an independent agent-operated terminal test, not a representative human study. The then-current README supplied sample coordinates; the result must not be used as evidence of unfamiliar-layout discovery. The later release preparation removes those coordinates from the public workflow and separately tests a newly frozen unseen report.

## Evidence presentation

Two historical command/terminal recordings have anonymous execution-path prefixes replaced with `<WORKSPACE>` / `<PYTHON_RUNTIME>` for readability. Their public-package checksums were updated and the redaction is disclosed in their manifests. Frozen source bytes, expected answers, test assertions, and outcome data were not changed. The older source repository (`astra-lab-spoollens`) still contains the original anonymous execution paths in its Git history; current-file redaction did not rewrite that source history. This independent `spoollens` repository imports only the verified snapshot, with fresh history and no source-repository commit ancestors.

Live exact-commit CI and current independent checks must be reviewed separately. Passing tests do not guarantee business-data correctness or authorize publication.

## Release-preparation checks

[Current preparation evidence](release-preparation/README.md) contains the independent coordinate-free unseen-report workflow, pre-frozen oracle, exact comparison, clean installation, and hygiene/name review. The original tutorial limitations above remain part of the record.

## Clean repository migration

The independently verified source snapshot is commit `d80c3d5c87ee0513224b2b511bdceb4e09328ac1` in `Haruuuuuuuuu/astra-lab-spoollens`, with tree `751acc7d6127dcdeb6935fa92648f5d60029302a` (183 files). That complete tree was imported unchanged into the independent private `Haruuuuuuuuu/spoollens` repository before these repository-reference updates. No old Git history was imported; the source repository was left unchanged.

Historical commit IDs and the historical 41-test reproduction instructions inside the frozen evidence package refer to the source repository. They are preserved as historical evidence and are not relabeled as runs against this new repository. To verify the current checkout, run the main README's 45-test suite and the portable `validate_abc.py` and `validate_unseen.py` checks under `release-preparation/validation/`. Frozen fixtures, expected answers, recorded evidence, runtime code, and acceptance criteria are unchanged.

This migration is private preparation only. It does not publish a release or package, create a tag, or establish broad production or business-data correctness.
