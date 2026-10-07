# Independent release-candidate validation plan

Frozen before receipt of the release candidate or unseen tester output, 2026-10-07.

- Clone the candidate into an independent checkout; record local commit/tree and prove the candidate remote tree is exactly equivalent, independently through GitHub metadata/tree content.
- Start a new virtual environment and follow only the final README's documented installation/launch/bundled-example/replay/test steps. Record OS, Python, actual commands, failures, workarounds, duration, and imported package location. Also invoke the installed CLI from outside the source directory so source-tree imports cannot disguise an installation failure.
- Rerun the full candidate unittest suite, frozen fixture checksum manifest, and compile checks.
- Compare A, B, and C CLI-produced CSV, accounting, provenance and export state exactly against their unchanged frozen expectations. Independently verify every physical line and source substring, inherited header origin, input byte hashes, blocked normal output absence, explicit exception marking and source/rule/artifact hashes.
- Repeat clean replay and explicit exception exports to new paths; require byte-identical CSV/evidence and deterministic exception ZIP bytes.
- Inspect the audit/provenance long-text fix and candidate regression tests; exercise the installed UI through a real terminal and record full-text inspection behavior.
- After the blind tester has finished, evaluate its saved rule and CSV against the separately frozen unseen-report truth without modifying acceptance criteria. Do not supply coordinates, rules, expected output, or coaching to the tester.
- Never change production files, frozen expected values, prior harness assertions, or expand fuzz scope. Report any failure or unverified stage explicitly.
