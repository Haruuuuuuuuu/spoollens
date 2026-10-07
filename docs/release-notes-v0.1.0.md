# v0.1.0 preparation notes

Prepared for review; this document is not a GitHub Release or a publication decision. SpoolLens is an early, deliberately limited tool, not a production-readiness claim.

## What works

- Visual fixed-width plain-text detail extraction: item, quantity, and price
- One inherited warehouse header/context, with explicit reset boundaries
- Exact source provenance for every extracted value, including inherited header origins
- Complete physical-line accounting, with separate whitespace classification
- Open JSON rules and deterministic offline replay
- Conservative clean CSV export: incomplete rules or unresolved/rejected lines block it
- Explicit exception bundles with candidate CSV, accounting, provenance, rule bytes, and manifest
- Read-only sources and no-overwrite export destinations
- Scrollable audit/provenance windows, full status/path inspection, and exact failing lines in blocked-export explanations

## Known limitations

- Recurring fixed-width TXT/PRN reports only; one inventory-shaped record type
- Built-in fields and validators are fixed; description is displayed but not exported
- Printable ASCII, LF, and standalone form feeds only; no Unicode layouts, tabs, BOMs, or CRLF normalization
- No PDF, OCR, or binary PRN
- No multiline records or nested/multi-level headers
- No AI inference or ERP/database integration
- No cloud, accounts, or collaboration
- Terminal keyboard interface; Linux tested, macOS intended but not independently certified, native Windows unsupported
- No guarantee of semantic or business-data correctness
- Agent-based usability checks do not establish usability for a representative human population

## Safety positioning

SpoolLens provides deterministic extraction, provenance, explicit line accounting, and conservative export behavior. Review the rule and its selected characters. A wrong but internally consistent rule can still extract the wrong business meaning.

Malformed data is not automatically repaired. An explicit exception bundle retains every unresolved/rejected line and marks its candidate CSV as partial. It must not be relabeled as clean output.

## Verification

See [validation evidence](evidence/README.md) for frozen A/B/C correctness and the separate release-preparation checks. Expected results are frozen before their independent test. No release, package publication, repository rename, visibility change, or announcement is part of preparation.
