"""Strict, dependency-free extraction shared by the CLI and terminal editor.

Rules contain data only. Coordinates refer to the original, unmodified physical
line, with a zero-based inclusive start and exclusive end. No expressions, regex
rules, line-ending repair, or best-effort decoding are supported.
"""
from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from dataclasses import dataclass
from typing import Any
import zipfile

VERSION = "0.1.0"
CATEGORIES = ("HEADER", "DETAIL", "IGNORED_BY_EXPLICIT_RULE", "UNRESOLVED", "REJECTED")
COLUMNS = ("warehouse", "item", "qty", "price")
COORDINATES = "1-based line; 0-based, end-exclusive character ranges; LF excluded"
FIELD_TYPES = {"warehouse": ("uppercase", "left"), "item": ("item_code", "left"),
               "qty": ("unsigned_integer", "right"), "price": ("decimal_2", "right")}
MAX_RULE_BYTES = 1024 * 1024
MAX_WIDTH = 1000000


class SpoolLensError(ValueError):
    """A safe, user-facing validation or export error."""


class RuleError(SpoolLensError):
    pass


class InputError(SpoolLensError):
    pass


class ExportBlocked(SpoolLensError):
    pass


class LoadedRule(dict):
    """An editable mapping retaining the exact bytes read from disk.

    Execution uses these bytes only while the mapping still has identical
    semantics. Edits are hashed using canonical_rule_bytes until saved/reloaded.
    """
    def __init__(self, rule: dict, raw_bytes: bytes, source_path: Path):
        super().__init__(rule)
        self.raw_bytes = raw_bytes
        self.source_path = source_path
        self._original = copy.deepcopy(rule)


def empty_rule() -> dict:
    return {"version": 1, "encoding": "utf-8", "character_policy": "ascii",
            "header": None, "detail": None, "ignore": []}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _keys(value: Any, expected: set[str], where: str, optional: set[str] | None = None) -> None:
    if not isinstance(value, dict):
        raise RuleError(f"{where} must be an object")
    if any(not isinstance(k, str) for k in value):
        raise RuleError(f"{where} keys must be strings")
    unknown = set(value) - expected - (optional or set())
    missing = expected - set(value)
    if unknown:
        raise RuleError(f"Unknown {where} keys: {', '.join(sorted(unknown))}")
    if missing:
        raise RuleError(f"Missing {where} keys: {', '.join(sorted(missing))}")


def _integer(value: Any, where: str, minimum: int = 0, maximum: int = MAX_WIDTH) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise RuleError(f"{where} must be an integer from {minimum} to {maximum}")
    return value


def _literal(value: Any, where: str, allow_ff: bool = False) -> str:
    if not isinstance(value, str) or not value:
        raise RuleError(f"{where} must be a non-empty string")
    if allow_ff and value == "\f":
        return value
    if len(value) > MAX_WIDTH or any(not 32 <= ord(c) <= 126 for c in value):
        raise RuleError(f"{where} must contain printable ASCII only")
    if not value.strip(" "):
        raise RuleError(f"{where} cannot match a whitespace-only line")
    return value


def _field(field: Any, width: int, where: str, names: set[str]) -> None:
    _keys(field, {"name", "start", "end", "type", "alignment"}, where)
    name = field["name"]
    if not isinstance(name, str) or name not in names:
        raise RuleError(f"{where}.name must be one of {', '.join(sorted(names))}")
    start = _integer(field["start"], f"{where}.start")
    end = _integer(field["end"], f"{where}.end", 1)
    if not start < end <= width:
        raise RuleError(f"{where} needs 0 <= start < end <= record width")
    expected_type, expected_alignment = FIELD_TYPES[name]
    if field["type"] != expected_type or field["alignment"] != expected_alignment:
        raise RuleError(f"{name} requires {expected_type} validation and {expected_alignment} alignment")
    if name == "warehouse" and end - start > 8:
        raise RuleError("Warehouse field must be at most 8 characters wide")
    if name == "item" and end - start < 4:
        raise RuleError("Item field must be at least 4 characters wide")


def _span_overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def _literal_overlap(a: dict, b: dict) -> bool:
    x, y = a["text"], b["text"]
    if a["mode"] == "exact" and b["mode"] == "exact":
        return x == y
    if a["mode"] == "prefix" and b["mode"] == "prefix":
        return x.startswith(y) or y.startswith(x)
    return y.startswith(x) if a["mode"] == "prefix" else x.startswith(y)


def _detector_overlap(literal: str, prefix: bool, detector: dict) -> bool:
    """Whether this literal language can intersect the detail detector language."""
    start, letters, digits = detector["start"], detector["letters"], detector["digits"]
    if not prefix and len(literal) < start + letters + digits:
        return False
    for offset in range(letters + digits):
        i = start + offset
        if i >= len(literal):
            continue
        c = literal[i]
        if offset < letters and not "A" <= c <= "Z":
            return False
        if offset >= letters and not "0" <= c <= "9":
            return False
    return True


def validate_rule(rule: Any) -> None:
    """Reject malformed or ambiguous rules; incomplete authoring rules are safe drafts."""
    _keys(rule, {"version", "encoding", "character_policy", "ignore"}, "rule", {"header", "detail"})
    if type(rule["version"]) is not int or rule["version"] != 1:
        raise RuleError("Only rule version 1 is supported")
    if rule["encoding"] not in ("utf-8", "ascii"):
        raise RuleError("encoding must be 'utf-8' or 'ascii'")
    if rule["character_policy"] != "ascii":
        raise RuleError("This probe requires character_policy='ascii'")
    header, detail = rule.get("header"), rule.get("detail")
    if header is not None:
        _keys(header, {"name", "prefix", "width", "field", "invalid_clears_context"}, "header")
        if header["name"] != "warehouse":
            raise RuleError("The inherited header name must be warehouse")
        prefix = _literal(header["prefix"], "header.prefix")
        width = _integer(header["width"], "header.width", 1)
        _field(header["field"], width, "header.field", {"warehouse"})
        if len(prefix) > header["field"]["start"]:
            raise RuleError("Header prefix overlaps the warehouse field")
        if header["invalid_clears_context"] is not True:
            raise RuleError("Invalid header candidates must clear inherited context")
    if detail is not None:
        _keys(detail, {"width", "detector", "fields", "spaces"}, "detail")
        width = _integer(detail["width"], "detail.width", 1)
        detector = detail["detector"]
        _keys(detector, {"kind", "start", "letters", "digits"}, "detail.detector")
        if detector["kind"] != "letter_digits":
            raise RuleError("The only detail detector is letter_digits")
        start = _integer(detector["start"], "detail.detector.start")
        if type(detector["letters"]) is not int or detector["letters"] != 1 or type(detector["digits"]) is not int or detector["digits"] != 3:
            raise RuleError("The item detector requires one uppercase ASCII letter and three ASCII digits")
        if start + 4 > width:
            raise RuleError("Detail detector extends beyond record width")
        if not isinstance(detail["fields"], list) or len(detail["fields"]) > 3:
            raise RuleError("detail.fields must be a list of at most three fields")
        spans: list[tuple[int, int]] = []
        names: set[str] = set()
        for i, field in enumerate(detail["fields"]):
            _field(field, width, f"detail.fields[{i}]", {"item", "qty", "price"})
            if field["name"] in names:
                raise RuleError(f"Duplicate detail field: {field['name']}")
            names.add(field["name"])
            span = (field["start"], field["end"])
            if any(_span_overlap(span, previous) for previous in spans):
                raise RuleError("Detail field ranges overlap")
            spans.append(span)
            if field["name"] == "item" and field["start"] != start:
                raise RuleError("Detail detector must begin at the item field's start")
        if not isinstance(detail["spaces"], list) or len(detail["spaces"]) > 100:
            raise RuleError("detail.spaces must be a list of at most 100 ranges")
        guards: list[tuple[int, int]] = []
        for i, guard in enumerate(detail["spaces"]):
            if not isinstance(guard, list) or len(guard) != 2:
                raise RuleError(f"detail.spaces[{i}] must be [start,end]")
            a = _integer(guard[0], "space guard start")
            b = _integer(guard[1], "space guard end", 1)
            if not a < b <= width:
                raise RuleError("Space guards need 0 <= start < end <= record width")
            if any(_span_overlap((a, b), previous) for previous in spans + guards):
                raise RuleError("Space guard overlaps a field or another guard")
            guards.append((a, b))
        if header is not None and _detector_overlap(header["prefix"], True, detector):
            raise RuleError("Header prefix and detail detector overlap")
    ignores = rule["ignore"]
    if not isinstance(ignores, list) or len(ignores) > 100:
        raise RuleError("ignore must be a list of at most 100 explicit rules")
    ignore_names: set[str] = set()
    for i, ignore in enumerate(ignores):
        _keys(ignore, {"name", "mode", "text", "reset"}, f"ignore[{i}]")
        name = ignore["name"]
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", name):
            raise RuleError("Ignore names must be lowercase identifiers of at most 64 characters")
        if name in ignore_names:
            raise RuleError(f"Duplicate ignore name: {name}")
        ignore_names.add(name)
        if ignore["mode"] not in ("exact", "prefix"):
            raise RuleError("Ignore mode must be exact or prefix")
        literal = _literal(ignore["text"], "ignore.text", allow_ff=ignore["mode"] == "exact")
        if type(ignore["reset"]) is not bool:
            raise RuleError("Ignore reset must be true or false")
        if literal == "\f" and ignore["reset"] is not True:
            raise RuleError("Standalone form feed boundaries must reset context")
        if any(_literal_overlap(ignore, previous) for previous in ignores[:i]):
            raise RuleError("Explicit ignore rules overlap")
        if header is not None and _literal_overlap(ignore, {"text": header["prefix"], "mode": "prefix"}):
            raise RuleError("Ignore rule overlaps the header detector")
        if detail is not None and _detector_overlap(literal, ignore["mode"] == "prefix", detail["detector"]):
            raise RuleError("Ignore rule overlaps the detail detector")


def rule_issues(rule: dict) -> list[str]:
    """Human-readable reasons a well-formed draft cannot be exported."""
    validate_rule(rule)
    issues = []
    if rule.get("header") is None:
        issues.append("Select the inherited warehouse header field")
    detail = rule.get("detail")
    if detail is None:
        issues.append("Select the item, qty, and price detail fields")
        return issues
    fields = {field["name"]: field for field in detail["fields"]}
    for name in COLUMNS[1:]:
        if name not in fields:
            issues.append(f"Select the {name} detail field")
    if len(fields) == 3:
        item, qty, price = (fields[name] for name in COLUMNS[1:])
        if not item["end"] + 2 <= qty["start"] - 2:
            issues.append("Leave room for the description and its two surrounding space guards")
        if price["start"] - qty["end"] != 2:
            issues.append("Quantity and price must be separated by exactly two guarded spaces")
        required = [(item["end"], item["end"] + 2), (qty["start"] - 2, qty["start"]), (qty["end"], price["start"])]
        guards = [tuple(span) for span in detail["spaces"]]
        for start, end in required:
            if (start, end) not in guards:
                issues.append(f"Add required space guard [{start},{end})")
    return issues


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def canonical_rule_bytes(rule: dict) -> bytes:
    validate_rule(rule)
    normal = copy.deepcopy(dict(rule))
    normal.setdefault("header", None)
    normal.setdefault("detail", None)
    if normal["detail"] is not None:
        normal["detail"]["fields"].sort(key=lambda field: COLUMNS.index(field["name"]))
        normal["detail"]["spaces"].sort()
    # Sorting object keys makes saved rules deterministic, independently of authoring order.
    return (json.dumps(normal, ensure_ascii=True, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict:
    out = {}
    for key, value in pairs:
        if key in out:
            raise RuleError(f"Duplicate JSON key: {key}")
        out[key] = value
    return out


def _parse_rule(raw: bytes) -> dict:
    if not isinstance(raw, bytes) or len(raw) > MAX_RULE_BYTES:
        raise RuleError("Rule must be bytes no larger than 1 MiB")
    try:
        rule = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                          parse_constant=lambda constant: (_ for _ in ()).throw(RuleError(f"Invalid JSON constant: {constant}")))
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise RuleError(f"Rule is not strict UTF-8 JSON: {exc}") from exc
    validate_rule(rule)
    return rule


def load_rule(path: str | os.PathLike) -> LoadedRule:
    path = Path(path)
    with path.open("rb") as stream:
        raw = stream.read(MAX_RULE_BYTES + 1)
    return LoadedRule(_parse_rule(raw), raw, path.resolve())


def _effective_rule_bytes(rule: dict, raw: bytes | None) -> bytes:
    if raw is not None:
        parsed = _parse_rule(raw)
        # Canonical comparison tolerates field/guard authoring order but no semantic mismatch.
        if canonical_rule_bytes(parsed) != canonical_rule_bytes(rule):
            raise RuleError("Supplied rule bytes do not describe the executed rule")
        return raw
    if isinstance(rule, LoadedRule) and dict(rule) == rule._original:
        return rule.raw_bytes
    return canonical_rule_bytes(rule)


def _source_lines(source: bytes, encoding: str) -> list[str]:
    if not isinstance(source, bytes):
        raise InputError("Source must be immutable bytes; read the file in binary mode")
    try:
        text = source.decode(encoding, errors="strict")
    except UnicodeDecodeError as exc:
        raise InputError(f"Invalid {encoding} input at byte {exc.start}; no lines were discarded") from exc
    lines = text.split("\n")
    if not text:
        return []
    if text.endswith("\n"):
        lines.pop()
    for number, line in enumerate(lines, 1):
        if line == "\f":
            continue
        for position, character in enumerate(line):
            if not 32 <= ord(character) <= 126:
                raise InputError(f"Unsupported character U+{ord(character):04X} at line {number}, column {position}; "
                                 "use printable ASCII, LF separators, and standalone FF only; input was not normalized")
    return lines


def _matches_detail(line: str, detector: dict) -> bool:
    start = detector["start"]
    candidate = line[start:start + 4]
    return len(candidate) == 4 and "A" <= candidate[0] <= "Z" and all("0" <= c <= "9" for c in candidate[1:])


def _field_error(raw: str, field: dict) -> str | None:
    value = raw.strip(" ")
    kind = field["type"]
    valid = {
        "uppercase": lambda: bool(re.fullmatch(r"[A-Z]{1,8}", value)),
        "item_code": lambda: bool(re.fullmatch(r"[A-Z][0-9]{3}", value)),
        "unsigned_integer": lambda: bool(re.fullmatch(r"[0-9]+", value)),
        "decimal_2": lambda: bool(re.fullmatch(r"[0-9]+\.[0-9]{2}", value)),
    }[kind]()
    reason = {"uppercase": "uppercase", "item_code": "code", "unsigned_integer": "integer", "decimal_2": "decimal_2"}[kind]
    if not valid:
        return f"invalid_{field['name']}_{reason}"
    if (field["alignment"] == "left" and raw != value.ljust(len(raw), " ")) or (field["alignment"] == "right" and raw != value.rjust(len(raw), " ")):
        return f"invalid_{field['name']}_alignment"
    return None


def _evidence(source_hash: str, line_number: int, line: str, field: dict, inherited: bool) -> dict:
    start, end = field["start"], field["end"]
    raw = line[start:end]
    out = {"value": raw.strip(" "), "source_sha256": source_hash, "line": line_number,
           "range": [start, end], "raw": raw, "inherited": inherited}
    if inherited:
        out.update(header_line=line_number, header_range=[start, end])
    return out


@dataclass(frozen=True)
class Result:
    """One extraction snapshot. The exported ledger/provenance use original text."""
    source_lines: list[str]
    lines: list[dict]
    rows: list[dict]
    counts: dict[str, int]
    errors: list[dict]
    source_sha256: str
    rule_sha256: str
    rule_issues: list[str]
    source_name: str
    source_path: Path | None
    rule_path: Path | None
    _source_bytes: bytes
    _rule_bytes: bytes

    @property
    def columns(self) -> list[str]:
        return list(COLUMNS)

    @property
    def rule_complete(self) -> bool:
        return not self.rule_issues

    @property
    def clean_export_allowed(self) -> bool:
        return self.rule_complete and not self.counts["UNRESOLVED"] and not self.counts["REJECTED"]

    @property
    def physical_line_count(self) -> int:
        return len(self.lines)

    @property
    def whitespace_only_line_count(self) -> int:
        return sum(line["category"] == "WHITESPACE_ONLY" for line in self.lines)

    @property
    def nonempty_line_count(self) -> int:
        return self.physical_line_count - self.whitespace_only_line_count

    def csv_bytes(self) -> bytes:
        """Preview accepted candidates, even when clean export is blocked.

        Writing these bytes directly bypasses the safety gate. User-facing entry
        points must use export_result, which enforces it.
        """
        out = io.StringIO(newline="")
        writer = csv.writer(out, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(COLUMNS)
        for row in self.rows:
            writer.writerow(row["fields"][name]["value"] for name in COLUMNS)
        return out.getvalue().encode("utf-8")

    def audit_dict(self) -> dict:
        return {"source_sha256": self.source_sha256, "physical_line_count": self.physical_line_count,
                "nonempty_line_count": self.nonempty_line_count,
                "whitespace_only_line_count": self.whitespace_only_line_count,
                "counts": copy.deepcopy(self.counts), "lines": copy.deepcopy(self.lines)}

    def provenance_dict(self) -> dict:
        return {"source_sha256": self.source_sha256, "coordinates": COORDINATES, "rows": copy.deepcopy(self.rows)}

    def export_dict(self) -> dict:
        """Export decision, not a claim that any artifact has been written."""
        return {"source_sha256": self.source_sha256, "rule_sha256": self.rule_sha256,
                "accepted_row_count": len(self.rows), "clean_export_allowed": self.clean_export_allowed,
                "unresolved_count": self.counts["UNRESOLVED"], "rejected_count": self.counts["REJECTED"],
                "rule_complete": self.rule_complete, "rule_issues": list(self.rule_issues),
                "errors": copy.deepcopy(self.errors)}


def execute(source_bytes: bytes, rule: dict, rule_bytes: bytes | None = None, *,
            source_name: str = "source.txt", source_path: str | os.PathLike | None = None) -> Result:
    validate_rule(rule)
    actual_rule_bytes = _effective_rule_bytes(rule, rule_bytes)
    # Execution takes a snapshot, so later authoring edits cannot change its output.
    snapshot = _parse_rule(actual_rule_bytes)
    source_lines = _source_lines(source_bytes, snapshot["encoding"])
    source_hash = _sha(source_bytes)
    issues = rule_issues(snapshot)
    header, detail = snapshot.get("header"), snapshot.get("detail")
    detail_complete = detail is not None and set(issues) <= {"Select the inherited warehouse header field"}
    ledger: list[dict] = []
    rows: list[dict] = []
    errors: list[dict] = []
    counts = dict.fromkeys(CATEGORIES, 0)
    context: dict | None = None
    for number, line in enumerate(source_lines, 1):
        before = context["value"] if context else None
        category, reason = "UNRESOLVED", "no_explicit_rule_matched"
        extra: dict = {}
        matched_ignore = next((item for item in snapshot["ignore"] if
                               (line == item["text"] if item["mode"] == "exact" else line.startswith(item["text"]))), None)
        if matched_ignore:
            category, reason = "IGNORED_BY_EXPLICIT_RULE", matched_ignore["name"]
            if matched_ignore["reset"]:
                context = None
        elif not line.strip(" "):
            category, reason = "WHITESPACE_ONLY", "blank_line"
        elif header is not None and line.startswith(header["prefix"]):
            category, reason = "HEADER", "warehouse_header"
            field = header["field"]
            if len(line) != header["width"]:
                reason = "invalid_header_width"
                extra = {"expected_width": header["width"], "actual_width": len(line)}
            else:
                field_reason = _field_error(line[field["start"]:field["end"]], field)
                if field_reason:
                    reason = field_reason
                    extra = {"range": [field["start"], field["end"]], "raw": line[field["start"]:field["end"]]}
                elif line[len(header["prefix"]):field["start"]].strip(" ") or line[field["end"]:].strip(" "):
                    reason = "invalid_header_padding"
            if reason != "warehouse_header":
                category, context = "REJECTED", None
            else:
                context = _evidence(source_hash, number, line, field, True)
        elif detail is not None and _matches_detail(line, detail["detector"]):
            category, reason = "REJECTED", "invalid_record_width"
            if len(line) != detail["width"]:
                extra = {"expected_width": detail["width"], "actual_width": len(line)}
            else:
                reason = ""
                for start, end in sorted(detail["spaces"]):
                    if line[start:end] != " " * (end - start):
                        reason = "non_space_separator"
                        extra = {"range": [start, end], "raw": line[start:end]}
                        break
                fields = {field["name"]: field for field in detail["fields"]}
                if not reason:
                    for name in COLUMNS[1:]:
                        if name not in fields:
                            continue
                        field = fields[name]
                        field_reason = _field_error(line[field["start"]:field["end"]], field)
                        if field_reason:
                            reason = field_reason
                            extra = {"range": [field["start"], field["end"]], "raw": line[field["start"]:field["end"]]}
                            break
                if not reason and not detail_complete:
                    reason = "incomplete_detail_rule"
                if not reason and context is None:
                    reason = "missing_warehouse_context"
                if not reason:
                    category, reason = "DETAIL", "accepted_detail"
                    evidence = {"warehouse": copy.deepcopy(context)}
                    evidence.update({name: _evidence(source_hash, number, line, fields[name], False) for name in COLUMNS[1:]})
                    rows.append({"row": len(rows) + 1, "detail_line": number, "fields": evidence})
        after = context["value"] if context else None
        ledger.append({"line": number, "raw": line, "category": category, "reason": reason,
                       "context_before": before, "context_after": after})
        if category in counts:
            counts[category] += 1
        if category in ("UNRESOLVED", "REJECTED"):
            errors.append({"line": number, "category": category, "reason": reason, **extra})
    return Result(source_lines, ledger, rows, counts, errors, source_hash, _sha(actual_rule_bytes), issues,
                  str(source_name), Path(source_path).resolve() if source_path is not None else None,
                  rule.source_path if isinstance(rule, LoadedRule) else None, source_bytes, actual_rule_bytes)


def _exclusive_atomic_write(path: Path, data: bytes) -> None:
    """Publish complete bytes without ever overwriting an existing destination."""
    if path.exists() or path.is_symlink():
        raise ExportBlocked(f"Destination already exists; choose a new path: {path}")
    if not path.parent.is_dir():
        raise ExportBlocked(f"Destination parent directory does not exist: {path.parent}")
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".spoollens-", dir=path.parent, delete=False) as stream:
            temporary = stream.name
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        # A hard link is atomic and refuses an existing destination, unlike replace().
        os.link(temporary, path)
    except FileExistsError as exc:
        raise ExportBlocked(f"Destination already exists; choose a new path: {path}") from exc
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass



def write_json_artifact(path: str | os.PathLike, document: Any) -> None:
    """Write one UTF-8 JSON artifact atomically, refusing an existing destination."""
    _exclusive_atomic_write(Path(path), _json_bytes(document))


def _publish_clean_artifacts(result: Result, path: Path, csv_data: bytes) -> dict:
    paths = {
        "audit": path.with_suffix(".audit.json"),
        "provenance": path.with_suffix(".provenance.json"),
        "manifest": path.with_suffix(".manifest.json"),
    }
    all_paths = [path, *paths.values()]
    if len(set(all_paths)) != len(all_paths):
        raise ExportBlocked("CSV path collides with an evidence sidecar; use a .csv filename")
    for target in all_paths:
        if target.exists() or target.is_symlink():
            raise ExportBlocked(f"Destination already exists; choose a new path: {target}")
        if not target.parent.is_dir():
            raise ExportBlocked(f"Destination parent directory does not exist: {target.parent}")
    audit = _json_bytes(result.audit_dict())
    provenance = _json_bytes(result.provenance_dict())
    contents = {paths["audit"]: audit, paths["provenance"]: provenance, path: csv_data}
    manifest = {
        "export_status": "CLEAN", "source_file": Path(result.source_name).name,
        "source_sha256": result.source_sha256, "source_byte_count": len(result._source_bytes),
        "rule_sha256": result.rule_sha256, "rule_byte_count": len(result._rule_bytes),
        "rule_hash_basis": "Exact rule bytes executed for this snapshot",
        "csv_file": path.name, "csv_sha256": _sha(csv_data),
        "accepted_row_count": len(result.rows), "unresolved_count": 0, "rejected_count": 0,
        "normal_clean_export_blocked": False, "physical_line_count": result.physical_line_count,
        "whitespace_only_line_count": result.whitespace_only_line_count, "counts": result.counts,
        "coordinates": COORDINATES,
        "artifacts": {target.name: {"sha256": _sha(data), "bytes": len(data)}
                      for target, data in contents.items()},
    }
    # Each file is atomic; the set is best-effort transactional. CSV is published
    # last, so a crash cannot expose candidate data before its evidence exists.
    ordered = [(paths["audit"], audit), (paths["provenance"], provenance),
               (paths["manifest"], _json_bytes(manifest)), (path, csv_data)]
    created: list[Path] = []
    try:
        for target, data in ordered:
            _exclusive_atomic_write(target, data)
            created.append(target)
    except BaseException:
        for target in reversed(created):
            try:
                target.unlink()
            except FileNotFoundError:
                pass
        raise
    return {"status": "CLEAN", "path": str(path), "csv_sha256": _sha(csv_data),
            "source_sha256": result.source_sha256, "rule_sha256": result.rule_sha256,
            "accepted_row_count": len(result.rows), "normal_csv_artifact_created": True,
            "audit_path": str(paths["audit"]), "provenance_path": str(paths["provenance"]),
            "manifest_path": str(paths["manifest"]), "manifest": manifest}


def _verify_snapshot(result: Result) -> Result:
    if result.source_path is not None:
        try:
            current = result.source_path.read_bytes()
        except OSError as exc:
            raise ExportBlocked(f"Cannot verify unchanged source: {exc}") from exc
        if current != result._source_bytes:
            raise ExportBlocked("Source changed since preview; reopen and re-extract before exporting")
    if result.rule_path is not None:
        try:
            current = result.rule_path.read_bytes()
        except OSError as exc:
            raise ExportBlocked(f"Cannot verify saved rule: {exc}") from exc
        if current != result._rule_bytes:
            raise ExportBlocked("Saved rule differs from the preview snapshot; save/reload and re-extract before exporting")
    fresh = execute(result._source_bytes, _parse_rule(result._rule_bytes), rule_bytes=result._rule_bytes,
                    source_name=result.source_name)
    # Protect the safety gate from accidental mutation of public preview lists.
    if (fresh.audit_dict() != result.audit_dict() or fresh.provenance_dict() != result.provenance_dict()
            or fresh.export_dict() != result.export_dict() or fresh.source_lines != result.source_lines):
        raise ExportBlocked("Preview result changed; re-extract before exporting")
    return fresh


def export_result(result: Result, path: str | os.PathLike, exception: bool = False) -> dict:
    """Export a clean CSV or explicitly requested, inseparable exception ZIP.

    Clean CSV includes sibling audit, provenance, and manifest JSON.
    A non-.zip exception destination is a newly created directory bundle. Existing
    files/directories and source/rule paths are never overwritten. A blocked clean
    export creates no artifact and does not touch the destination.
    """
    if type(exception) is not bool:
        raise ExportBlocked("exception must be an explicit boolean")
    verified = _verify_snapshot(result)
    if not exception and not verified.clean_export_allowed:
        parts = [f"{verified.counts['UNRESOLVED']} unresolved", f"{verified.counts['REJECTED']} rejected"]
        if verified.rule_issues:
            parts.append("incomplete rule: " + "; ".join(verified.rule_issues))
        raise ExportBlocked("Clean CSV export blocked: " + ", ".join(parts))
    if exception and not verified.rule_complete:
        raise ExportBlocked("Exception export requires a complete saved rule: " + "; ".join(verified.rule_issues))
    path = Path(path)
    resolved = path.resolve()
    if resolved in (result.source_path, result.rule_path):
        raise ExportBlocked("Output must not replace the source or saved rule")
    if path.exists() or path.is_symlink():
        raise ExportBlocked(f"Destination already exists; choose a new path: {path}")
    csv_data = verified.csv_bytes()
    if not exception:
        return _publish_clean_artifacts(verified, path, csv_data)
    source_file = Path(verified.source_name).name
    stem = re.sub(r"[^A-Za-z0-9._-]", "_", Path(source_file).stem)[:100] or "source"
    csv_name = stem + ".exception.csv"
    manifest = {"exception_status": "EXPLICIT_EXCEPTION", "source_file": source_file,
                "source_sha256": verified.source_sha256, "input_artifact": "input.bin",
                "source_byte_count": len(verified._source_bytes), "rule_file": "rule.json",
                "rule_sha256": verified.rule_sha256, "rule_hash_basis": "Exact bytes of bundled rule.json",
                "unresolved_count": verified.counts["UNRESOLVED"], "rejected_count": verified.counts["REJECTED"],
                "accepted_row_count": len(verified.rows), "csv_file": csv_name, "csv_sha256": _sha(csv_data),
                "omitted_line_numbers": [line["line"] for line in verified.errors],
                "normal_clean_export_blocked": not verified.clean_export_allowed,
                "physical_line_count": verified.physical_line_count,
                "whitespace_only_line_count": verified.whitespace_only_line_count,
                "counts": verified.counts, "coordinates": COORDINATES}
    members = {csv_name: csv_data, "input.bin": verified._source_bytes, "rule.json": verified._rule_bytes,
               "accounting.json": _json_bytes(verified.audit_dict()),
               "provenance.json": _json_bytes(verified.provenance_dict())}
    manifest["artifacts"] = {name: {"sha256": _sha(data), "bytes": len(data)} for name, data in members.items()}
    members["manifest.json"] = _json_bytes(manifest)
    if path.suffix.lower() == ".zip":
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in members.items():
                entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = 0o600 << 16
                archive.writestr(entry, data)
        _exclusive_atomic_write(path, out.getvalue())
    else:
        if not path.parent.is_dir():
            raise ExportBlocked(f"Destination parent directory does not exist: {path.parent}")
        # Reserve the name exclusively before writing; remove it if bundle creation fails.
        try:
            path.mkdir(mode=0o700)
        except FileExistsError as exc:
            raise ExportBlocked(f"Destination already exists; choose a new path: {path}") from exc
        try:
            for name, data in members.items():
                with (path / name).open("xb") as stream:
                    stream.write(data)
        except BaseException:
            shutil.rmtree(path)
            raise
    return {"status": "EXPLICIT_EXCEPTION", "path": str(path), "manifest": manifest,
            "normal_csv_artifact_created": False}
