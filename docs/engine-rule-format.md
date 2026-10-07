# Engine and rule contract

This initial version deliberately supports one inventory header and one detail type. The UI and CLI both call `spoollens.engine.execute`; neither implements its own extraction logic. Python 3.10+ and only its standard library are required.

## Input and coordinates

Read reports in binary mode. `encoding` must explicitly be `utf-8` or `ascii`, and `character_policy` must be `ascii`. UTF-8 does not enable Unicode field matching in this version. Only printable ASCII, LF separators, and a standalone form-feed physical line are supported. BOMs, CR/CRLF, tabs, non-ASCII characters, invalid decoding, and inline form feeds fail the entire extraction before an export is possible. Nothing is normalized, repaired, stripped from the input, or silently discarded.

LF alone separates physical lines. A terminal LF ends the last line without adding another. Empty lines and lines containing only ASCII spaces are accounted for separately. A standalone FF is a real physical line, not a line separator or blank line. Without an explicit FF ignore rule, it remains unresolved.

Evidence uses 1-based physical line numbers and 0-based, end-exclusive character ranges, excluding LF. The input's ASCII policy means byte positions and character positions coincide. Selected padding is retained in evidence; values are trimmed with ASCII space only. Decimals stay strings, preserving `0.20`.

## Version 1 JSON schema

`examples/inventory.rule.json` is the complete, open, executable-data-free example. The saved rule contains only these fields:

- Root: `version` (integer 1), `encoding`, `character_policy`, `header`, `detail`, `ignore`
- Header: `name` (`warehouse`), `prefix` (literal printable ASCII), `width`, `field`, `invalid_clears_context` (must be true)
- Field: `name`, `start`, `end`, `type`, `alignment`
- Detail: `width`, `detector`, `fields`, `spaces`
- Detector: `kind` (`letter_digits`), `start`, `letters` (1), `digits` (3)
- Ignore entry: `name` (lowercase identifier), `mode` (`exact` or `prefix`), `text` (literal), `reset` (boolean)

Names and validators are deliberately fixed:

| Name | Validator | Alignment |
| --- | --- | --- |
| warehouse | `uppercase`: 1–8 uppercase ASCII letters | left |
| item | `item_code`: one uppercase ASCII letter, three ASCII digits | left |
| qty | `unsigned_integer`: one or more ASCII digits | right |
| price | `decimal_2`: unsigned ASCII integer, decimal point, two digits | right |

Widths, spans, prefixes, and explicit ignore literals come from authoring. All widths and indices are integers, not booleans. Field ranges cannot overlap or extend past their record. The warehouse field cannot overlap its identifying prefix. Space guards cannot overlap fields or each other. A detector starts at the item field's start.

Unknown keys, duplicate JSON keys, NaN/Infinity, expressions, regex rules, custom validators, and ambiguous overlapping ignore/header/detail detectors are rejected. Literal ignore rules cannot hide detail or header candidates. A standalone FF ignore must reset context. Built-in validators use fixed internal type checks; users never author executable code or regular expressions.

## Drafts and required guards

`header` and `detail` can be null or absent during authoring. A non-null detail can have missing field slots. These are safe drafts, with explicit completeness reasons and no permitted export, including exception export.

A complete rule requires all four fields and three explicit two-space guards: immediately after item, immediately before quantity, and between quantity and price. The quantity-to-price gap must be exactly two characters. The UI proposes these adjacent guards from observed source spaces. Removing a required guard returns the rule to draft status; it cannot silently accept the shifted quantity from C. Each required guard is represented as its full two-character span, not two separate one-character guards. Additional non-overlapping guards are permitted.

Validation of detail candidates proceeds in this order: exact record width, coordinate-sorted space guards, item, qty, price, draft completeness, required warehouse context. Candidate failures are rejected rather than ignored. Valid headers replace context and its provenance; invalid header candidates clear it. Explicit reset rules clear context; blank lines, rejected details, and unresolved lines preserve it.

CSV columns always appear in `warehouse,item,qty,price` order. Canonical serialization sorts detail fields into that order and guards by coordinates without modifying the author's in-memory mapping.

## Python API

- `empty_rule()` returns an editable draft mapping
- `validate_rule(rule)` checks structure and safety, permitting well-formed drafts
- `rule_issues(rule)` reports completeness blockers
- `canonical_rule_bytes(rule)` validates and serializes deterministic UTF-8 JSON with a final LF
- `load_rule(path)` returns a dict-like `LoadedRule`, retaining exact original bytes and path
- `execute(source_bytes, rule, rule_bytes=None, *, source_name='source.txt', source_path=None)` returns a snapshot
- `export_result(result, path, exception=False)` enforces the gate and creates a new artifact
- `write_json_artifact(path, document)` atomically writes a standalone JSON artifact without overwriting an existing path

A `LoadedRule` hashes the exact bytes loaded, including formatting, as long as its mapping remains unchanged. In-memory edits use canonical bytes until saved/reloaded. Supplying `rule_bytes` explicitly requires that those exact bytes describe the executed rule. The bundled rule is always the exact representation used for the recorded hash. Rule files are limited to 1 MiB.

`Result` exposes:

- `source_lines`: exact original physical lines
- `lines`: one accounting dictionary per physical line, including category, reason, and context transition
- `rows`: accepted output rows with per-field evidence
- `counts`: the five nonblank categories; blank counts are separate
- `errors`: unresolved/rejected line numbers, reasons, and diagnostic ranges or widths when applicable
- `columns`, `source_sha256`, `rule_sha256`, `rule_complete`, `rule_issues`, `clean_export_allowed`
- `csv_bytes()`, `audit_dict()`, `provenance_dict()`, `export_dict()`

`csv_bytes()` is a candidate preview, including when export is blocked. User-facing code must use `export_result`; directly writing preview bytes bypasses the gate. `export_dict()` describes a decision, not a claim that any file was created.

`SpoolLensError` derives from `ValueError`; `RuleError`, `InputError`, and `ExportBlocked` derive from it. File-system errors use the standard `OSError` hierarchy.

## Export guarantees

Clean CSV export requires a complete rule, zero unresolved lines, and zero rejected lines. A blocked request creates no CSV and does not touch its destination. Existing files, directories, symlinks, and source/rule paths are never overwritten. Parent directories must already exist.

Before any export, the engine re-executes the original snapshot and detects mutations to public preview data. If source and saved-rule paths were provided, their current bytes must still equal the previewed bytes. Reopen and re-extract after a change.

Explicit exception export is a `.zip` archive, or a new directory bundle when the destination has no `.zip` suffix. It contains:

- The accepted-row CSV named `*.exception.csv`
- The exact input snapshot (`input.bin`)
- The exact executed rule (`rule.json`)
- Full accounting and provenance
- `manifest.json`, marked `EXPLICIT_EXCEPTION`, with input/rule/output SHA-256 hashes, byte counts, category counts, omitted problem line numbers, and the normal-clean-export-blocked flag

The manifest includes a SHA-256 and byte count for every other bundle member. ZIP creation is deterministic, with fixed timestamps. The archive is published atomically without overwriting a destination. Clean export automatically creates sibling `.audit.json`, `.provenance.json`, and `.manifest.json` evidence files. The clean manifest records source/rule/CSV SHA-256 hashes and hashes for the evidence files. All destinations are checked before writing; each file is atomic and exclusive, with the CSV published last. An ordinary write failure rolls back files created by that call. The multi-file set is not crash-atomic: an interrupted process can leave sidecars without a CSV. Existing files are never removed by rollback. The CLI's `--audit` and `--provenance` options can additionally create standalone evidence without a clean export.

## CLI

```sh
python -m spoollens replay tests/fixtures/A_clean.txt --rule examples/inventory.rule.json --output a.csv
python -m spoollens replay tests/fixtures/C_dangerous.txt --rule examples/inventory.rule.json --exception-bundle c.exception.zip
python -m spoollens inspect tests/fixtures/B_boundaries.txt --rule examples/inventory.rule.json --row 2 --field price
python -m spoollens inspect tests/fixtures/C_dangerous.txt --rule examples/inventory.rule.json --line 7
```

`replay` prints the decision as JSON. Optional `--audit`, `--provenance`, and `--summary` write new JSON files. Exit 0 means a clean extraction or completed explicit exception export; exit 2 means a blocked/incomplete replay or export, and exit 1 means an input/rule/file error. `inspect` is read-only and may inspect a report whose clean export is blocked. CLI-only usage never imports curses.
