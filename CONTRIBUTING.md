# Contributing to SpoolLens

Small, focused fixes and clear bug reports are welcome. Keep changes within the documented fixed-width plain-text TXT/PRN scope.

## Report a problem

Include your OS, Python version, SpoolLens version or commit, exact steps, and the expected versus actual result. Use a minimal synthetic report and rule. Do not upload confidential production reports, personal data, credentials, or private paths. For security-sensitive findings, see [SECURITY.md](SECURITY.md).

## Work on a change

Follow the [README](README.md) installation instructions, then run:

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q spoollens
```

Add a regression test for fixes where practical. Preserve source bytes, exact value provenance, complete line accounting, deterministic replay, and blocked clean export when unresolved or rejected lines remain. A passing extraction does not prove business-data correctness.

Run the frozen-fixture integrity check described in the README. The original `tests/fixtures/` reports and expected answers are frozen acceptance evidence. Do not change or regenerate them to make a test pass. Add new synthetic cases separately.

Use the existing standard-library approach where possible. Keep generated exports, caches, virtual environments, and local reports out of commits. Any new sample or asset must be synthetic and original, or include its source and a compatible license. Contributions are made under the repository's [MIT license](LICENSE); do not include material you cannot license.
