"""Golden truth and fail-closed regressions; frozen fixtures are read-only inputs."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

from spoollens.engine import (
    CATEGORIES, ExportBlocked, InputError, RuleError, canonical_rule_bytes,
    empty_rule, execute, export_result, load_rule, rule_issues, validate_rule,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
EXPECTED = ROOT / "tests" / "expected"
RULE = ROOT / "examples" / "inventory.rule.json"


def sha(data):
    return hashlib.sha256(data).hexdigest()


class GoldenContractTests(unittest.TestCase):
    def setUp(self):
        self.rule = load_rule(RULE)

    def run_fixture(self, name):
        path = FIXTURES / f"{name}.txt"
        return execute(path.read_bytes(), self.rule, source_name=path.name, source_path=path)

    def test_exact_frozen_csv_provenance_accounting_and_errors(self):
        for name, rows in (("A_clean", 3), ("B_boundaries", 4), ("C_dangerous", 2)):
            with self.subTest(fixture=name):
                result = self.run_fixture(name)
                self.assertEqual(result.csv_bytes(), (EXPECTED / f"{name}.rows.csv").read_bytes())
                self.assertEqual(result.audit_dict(), json.loads((EXPECTED / f"{name}.accounting.json").read_bytes()))
                self.assertEqual(result.provenance_dict(), json.loads((EXPECTED / f"{name}.provenance.json").read_bytes()))
                expected = json.loads((EXPECTED / f"{name}.export.json").read_bytes())
                self.assertEqual(result.errors, expected["errors"])
                self.assertEqual(result.clean_export_allowed, expected["clean_export_allowed"])
                self.assertEqual(len(result.rows), rows)
                self.assertEqual(result.rule_sha256, sha(RULE.read_bytes()))
                self.assertEqual(result.physical_line_count, sum(result.counts.values()) + result.whitespace_only_line_count)

    def test_every_value_traces_back_to_exact_unmodified_characters(self):
        for name in ("A_clean", "B_boundaries", "C_dangerous"):
            result = self.run_fixture(name)
            for row in result.rows:
                for evidence in row["fields"].values():
                    start, end = evidence["range"]
                    self.assertEqual(result.source_lines[evidence["line"] - 1][start:end], evidence["raw"])
                    self.assertEqual(evidence["raw"].strip(" "), evidence["value"])
                    self.assertEqual(evidence["source_sha256"], result.source_sha256)
                    if evidence["inherited"]:
                        self.assertEqual(evidence["line"], evidence["header_line"])
                        self.assertEqual(evidence["range"], evidence["header_range"])

    def test_c_shifted_quantity_is_never_accepted_or_repaired(self):
        result = self.run_fixture("C_dangerous")
        self.assertEqual(result.counts["UNRESOLVED"], 1)
        self.assertEqual(result.counts["REJECTED"], 5)
        self.assertEqual([e["line"] for e in result.errors], [3, 7, 8, 9, 10, 15])
        self.assertEqual(result.errors[1]["raw"], "7 ")
        self.assertNotIn("C111", result.csv_bytes().decode())

    def test_clean_export_and_exception_zip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a = self.run_fixture("A_clean")
            output = root / "a.csv"
            receipt = export_result(a, output)
            self.assertEqual(output.read_bytes(), a.csv_bytes())
            self.assertEqual(receipt["csv_sha256"], sha(output.read_bytes()))
            c = self.run_fixture("C_dangerous")
            blocked = root / "c.csv"
            with self.assertRaises(ExportBlocked):
                export_result(c, blocked)
            self.assertFalse(blocked.exists())
            exception = root / "c.exception.zip"
            receipt = export_result(c, exception, exception=True)
            self.assertEqual(receipt["status"], "EXPLICIT_EXCEPTION")
            with zipfile.ZipFile(exception) as archive:
                manifest = json.loads(archive.read("manifest.json"))
                self.assertEqual(manifest, receipt["manifest"])
                self.assertEqual(archive.read(manifest["csv_file"]), c.csv_bytes())
                self.assertEqual(archive.read("input.bin"), (FIXTURES / "C_dangerous.txt").read_bytes())
                self.assertEqual(archive.read("rule.json"), RULE.read_bytes())
                self.assertEqual(manifest["rule_sha256"], sha(archive.read("rule.json")))
                self.assertEqual(manifest["source_sha256"], sha(archive.read("input.bin")))
                self.assertEqual(manifest["csv_sha256"], sha(archive.read(manifest["csv_file"])))
                self.assertEqual(manifest["exception_status"], "EXPLICIT_EXCEPTION")
                self.assertTrue(manifest["normal_clean_export_blocked"])
                self.assertEqual(manifest["unresolved_count"], 1)
                self.assertEqual(manifest["rejected_count"], 5)
                self.assertEqual(manifest["accepted_row_count"], 2)
                self.assertEqual(manifest["omitted_line_numbers"], [3, 7, 8, 9, 10, 15])
                for member, descriptor in manifest["artifacts"].items():
                    content = archive.read(member)
                    self.assertEqual(sha(content), descriptor["sha256"])
                    self.assertEqual(len(content), descriptor["bytes"])

    def test_exception_directory_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "bundle"
            receipt = export_result(self.run_fixture("C_dangerous"), output, exception=True)
            self.assertEqual(json.loads((output / "manifest.json").read_bytes()), receipt["manifest"])
            for name, descriptor in receipt["manifest"]["artifacts"].items():
                self.assertEqual(sha((output / name).read_bytes()), descriptor["sha256"])

    def test_source_and_rule_frozen_integrity_unchanged(self):
        # Independently verify every frozen file, including original expected truth.
        for entry in (FIXTURES / "SHA256SUMS").read_text().splitlines():
            checksum, filename = entry.split(maxsplit=1)
            self.assertEqual(sha((FIXTURES / filename.lstrip("*")).read_bytes()), checksum, filename)


class InputPolicyTests(unittest.TestCase):
    def setUp(self):
        self.rule = load_rule(RULE)

    def test_ff_is_one_physical_line_not_a_separator(self):
        result = execute(b"\n\f\n  \n", self.rule)
        self.assertEqual(result.source_lines, ["", "\f", "  "])
        self.assertEqual(result.physical_line_count, 3)
        self.assertEqual(result.whitespace_only_line_count, 2)
        self.assertEqual(result.counts["IGNORED_BY_EXPLICIT_RULE"], 1)

    def test_final_lf_does_not_create_spurious_empty_line(self):
        cases = [(b"", []), (b"\n", [""]), (b"\n\n", ["", ""]),
                 (b" ", [" "]), (b" \n", [" "]), (b" \n\n", [" ", ""])]
        for data, expected in cases:
            self.assertEqual(execute(data, self.rule).source_lines, expected)

    def test_illegal_controls_fail_without_silent_line_drop(self):
        for number in list(range(32)) + [127]:
            if number in (10, 12):
                continue
            with self.subTest(control=number), self.assertRaises(InputError):
                execute(b"safe\n" + bytes([number]) + b"\nend\n", self.rule)
        for data in (b"A\fB\n", b"\f \n", b" \f\n", b"line\r\n", b"\xef\xbb\xbfHEADER\n"):
            with self.subTest(data=data), self.assertRaises(InputError):
                execute(data, self.rule)

    def test_encoding_is_explicit_and_non_ascii_fails_everywhere(self):
        for encoding in ("utf-8", "ascii"):
            rule = copy.deepcopy(dict(self.rule))
            rule["encoding"] = encoding
            for data in (b"\xff\n", "café\n".encode(), "\u2028\n".encode(), "\u00a0\n".encode()):
                with self.subTest(encoding=encoding, data=data), self.assertRaises(InputError):
                    execute(data, rule)
        with self.assertRaises(InputError):
            execute("not bytes", self.rule)
        with self.assertRaises(InputError):
            execute(bytearray(b"mutable"), self.rule)

    def test_unknown_notice_never_silently_disappears(self):
        result = execute(b"NOTICE: CHECK THIS\n", self.rule)
        self.assertEqual(result.counts["UNRESOLVED"], 1)
        self.assertFalse(result.clean_export_allowed)
        self.assertEqual(result.lines[0]["raw"], "NOTICE: CHECK THIS")

    def test_invalid_header_clears_context(self):
        good = "A100      WIDGET BLUE              12      9.95"
        for invalid in ("WAREHOUSE: bad     ", "WAREHOUSE: WEST", "WAREHOUSE:  WEST   "):
            source = f"WAREHOUSE: NORTH   \n{good}\n{invalid}\n{good}\n".encode()
            result = execute(source, self.rule)
            self.assertEqual(len(result.rows), 1)
            self.assertEqual(result.lines[2]["category"], "REJECTED")
            self.assertIsNone(result.lines[2]["context_after"])
            self.assertEqual(result.lines[3]["reason"], "missing_warehouse_context")

    def test_field_alignment_and_ascii_numeric_types(self):
        original = list("A100      WIDGET BLUE              12      9.95")
        cases = [(32, 37, "12   ", "invalid_qty_alignment"),
                 (32, 37, "   -1", "invalid_qty_integer"),
                 (39, 47, "     9.9", "invalid_price_decimal_2"),
                 (39, 47, "9.95    ", "invalid_price_alignment"),
                 (0, 8, "A100X   ", "invalid_item_code")]
        for start, end, replacement, reason in cases:
            chars = original[:]
            chars[start:end] = replacement
            result = execute(("WAREHOUSE: NORTH   \n" + "".join(chars) + "\n").encode(), self.rule)
            self.assertEqual(result.errors[0]["reason"], reason)


class RuleSafetyTests(unittest.TestCase):
    def setUp(self):
        self.rule = dict(load_rule(RULE))

    def bad(self, change):
        rule = copy.deepcopy(self.rule)
        change(rule)
        with self.assertRaises(RuleError):
            validate_rule(rule)

    def test_unknown_keys_and_executable_strings_rejected(self):
        self.bad(lambda r: r.update(expression="__import__('os').system('false')"))
        self.bad(lambda r: r["detail"].update(regex=".*"))
        self.bad(lambda r: r["detail"]["fields"][0].update(transform="eval(value)"))
        self.bad(lambda r: r["ignore"][0].update(command="anything"))
        self.bad(lambda r: r["header"].update(invalid_clears_context=False))
        self.bad(lambda r: r.update(character_policy="unicode"))
        self.bad(lambda r: r.update(encoding="utf-16"))
        self.bad(lambda r: r.update(version=True))
        self.bad(lambda r: r["detail"].update(width=True))

    def test_bad_ranges_and_overlaps_rejected(self):
        self.bad(lambda r: r["detail"]["fields"][0].update(start=-1))
        self.bad(lambda r: r["detail"]["fields"][0].update(end=0))
        self.bad(lambda r: r["detail"]["fields"][0].update(end=48))
        self.bad(lambda r: r["detail"]["fields"][1].update(start=3))
        self.bad(lambda r: r["detail"]["spaces"].append([7, 10]))
        self.bad(lambda r: r["detail"]["spaces"].append([9, 11]))
        self.bad(lambda r: r["detail"]["fields"].append(copy.deepcopy(r["detail"]["fields"][0])))
        self.bad(lambda r: r["detail"]["detector"].update(start=1))
        self.bad(lambda r: r["header"]["field"].update(start=10))

    def test_ignore_rules_cannot_hide_candidates_or_each_other(self):
        def append(r, text, mode="prefix"):
            r["ignore"].append({"name": "unsafe", "text": text, "mode": mode, "reset": True})
        for text in ("A", "A100", "WAREHOUSE", "INVENTORY"):
            with self.subTest(text=text):
                self.bad(lambda r, text=text: append(r, text))
        self.bad(lambda r: append(r, "A100 candidate", "exact"))
        self.bad(lambda r: append(r, " "))
        self.bad(lambda r: append(r, "\t", "exact"))
        self.bad(lambda r: r["ignore"][3].update(reset=False))

    def test_drafts_are_safe_and_export_blocked(self):
        drafts = [empty_rule(), {k: v for k, v in empty_rule().items() if k not in ("header", "detail")}]
        for field in ("item", "qty", "price"):
            partial = copy.deepcopy(self.rule)
            partial["detail"]["fields"] = [x for x in partial["detail"]["fields"] if x["name"] != field]
            drafts.append(partial)
        partial = copy.deepcopy(self.rule)
        partial["detail"]["spaces"].remove([37, 39])
        drafts.append(partial)
        with tempfile.TemporaryDirectory() as directory:
            for i, rule in enumerate(drafts):
                with self.subTest(draft=i):
                    validate_rule(rule)
                    result = execute((FIXTURES / "A_clean.txt").read_bytes(), rule)
                    self.assertFalse(result.rule_complete)
                    self.assertFalse(result.clean_export_allowed)
                    self.assertTrue(rule_issues(rule))
                    for exception in (False, True):
                        destination = Path(directory) / f"{i}-{exception}.zip"
                        with self.assertRaises(ExportBlocked):
                            export_result(result, destination, exception=exception)
                        self.assertFalse(destination.exists())

    def test_exact_loaded_rule_hash_and_mismatch(self):
        raw = json.dumps(self.rule, separators=(",", ":")).encode()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rule.json"
            path.write_bytes(raw)
            loaded = load_rule(path)
            result = execute(b"", loaded)
            self.assertEqual(result.rule_sha256, sha(raw))
            self.assertNotEqual(raw, canonical_rule_bytes(loaded))
            loaded["encoding"] = "ascii"
            changed = execute(b"", loaded)
            self.assertEqual(changed.rule_sha256, sha(canonical_rule_bytes(loaded)))
            with self.assertRaises(RuleError):
                execute(b"", loaded, rule_bytes=raw)

    def test_duplicate_json_keys_and_non_json_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            for raw in (b'{"version":1,"version":1}', b'NaN', b'null', b'[]', b'\xef\xbb\xbf{}', b'{"x":Infinity}', b'\xff'):
                path.write_bytes(raw)
                with self.subTest(raw=raw), self.assertRaises(RuleError):
                    load_rule(path)

    def test_schema_type_mutations_fail_with_safe_errors(self):
        paths = []
        def scan(value, path=()):
            paths.append(path)
            if isinstance(value, dict):
                for key, child in value.items():
                    scan(child, path + (key,))
            elif isinstance(value, list):
                for key, child in enumerate(value):
                    scan(child, path + (key,))
        scan(self.rule)
        for path in paths:
            for replacement in (None, False, True, 0, -1, 1.5, float("nan"), "", "x", [], {}):
                mutated = copy.deepcopy(self.rule)
                if not path:
                    mutated = replacement
                else:
                    target = mutated
                    for key in path[:-1]:
                        target = target[key]
                    target[path[-1]] = replacement
                try:
                    # Some mutations create legitimate safe drafts; all others must
                    # produce a controlled RuleError, not a crash or code execution.
                    execute(b"", mutated)
                except RuleError:
                    pass

    def test_oversized_and_extreme_json_numbers_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            for data in (b" " * (1024 * 1024 + 1), b'{"version":' + b"9" * 10000 + b"}"):
                path.write_bytes(data)
                with self.assertRaises(RuleError):
                    load_rule(path)

    def test_canonical_rule_preserves_semantics_and_order(self):
        reordered = copy.deepcopy(self.rule)
        reordered["detail"]["fields"].reverse()
        reordered["detail"]["spaces"].reverse()
        self.assertEqual(canonical_rule_bytes(reordered), canonical_rule_bytes(self.rule))
        self.assertEqual(execute((FIXTURES / "C_dangerous.txt").read_bytes(), reordered).audit_dict(),
                         execute((FIXTURES / "C_dangerous.txt").read_bytes(), self.rule).audit_dict())


class ExportSafetyTests(unittest.TestCase):
    def setUp(self):
        self.rule = load_rule(RULE)
        self.source = (FIXTURES / "A_clean.txt").read_bytes()

    def test_existing_files_directories_symlinks_never_overwritten(self):
        result = execute(self.source, self.rule)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "existing.csv"
            target.write_bytes(b"keep me")
            with self.assertRaises(ExportBlocked):
                export_result(result, target)
            self.assertEqual(target.read_bytes(), b"keep me")
            bundle = root / "existingdir"
            bundle.mkdir()
            with self.assertRaises(ExportBlocked):
                export_result(result, bundle, exception=True)
            link = root / "link.csv"
            link.symlink_to(target)
            with self.assertRaises(ExportBlocked):
                export_result(result, link)
            self.assertEqual(target.read_bytes(), b"keep me")
            broken = root / "broken.csv"
            broken.symlink_to(root / "nonexistent")
            with self.assertRaises(ExportBlocked):
                export_result(result, broken)

    def test_input_source_and_saved_rule_are_never_mutated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.txt"
            rule_path = root / "rule.json"
            source.write_bytes(self.source)
            rule_path.write_bytes(RULE.read_bytes())
            result = execute(source.read_bytes(), load_rule(rule_path), source_path=source)
            for target in (source, rule_path):
                with self.assertRaises(ExportBlocked):
                    export_result(result, target)
            export_result(result, root / "out.csv")
            export_result(result, root / "out.zip", exception=True)
            self.assertEqual(source.read_bytes(), self.source)
            self.assertEqual(rule_path.read_bytes(), RULE.read_bytes())

    def test_stale_source_and_saved_rule_block_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, rule_path = root / "input.txt", root / "rule.json"
            source.write_bytes(self.source)
            rule_path.write_bytes(RULE.read_bytes())
            result = execute(source.read_bytes(), load_rule(rule_path), source_path=source)
            source.write_bytes(self.source + b"NOTICE\n")
            with self.assertRaises(ExportBlocked):
                export_result(result, root / "stale.csv")
            source.write_bytes(self.source)
            rule_path.write_bytes(RULE.read_bytes() + b"\n")
            with self.assertRaises(ExportBlocked):
                export_result(result, root / "stalerule.csv")
            self.assertFalse((root / "stale.csv").exists())
            self.assertFalse((root / "stalerule.csv").exists())

    def test_mutated_public_preview_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            for mutate in (lambda r: r.counts.update(REJECTED=0),
                           lambda r: r.rows[0]["fields"]["qty"].update(value="999"),
                           lambda r: r.lines.pop(), lambda r: r.source_lines.pop()):
                result = execute((FIXTURES / "C_dangerous.txt").read_bytes(), self.rule)
                mutate(result)
                with self.assertRaises(ExportBlocked):
                    export_result(result, Path(directory) / "out.zip", exception=True)

    def test_clean_sidecars_have_verified_counts_hashes_and_exact_evidence(self):
        result = execute(self.source, self.rule, source_name="A_clean.txt")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = export_result(result, root / "a.csv")
            manifest = json.loads(Path(receipt["manifest_path"]).read_bytes())
            self.assertEqual(manifest, receipt["manifest"])
            self.assertEqual(manifest["export_status"], "CLEAN")
            self.assertEqual(manifest["source_sha256"], sha(self.source))
            self.assertEqual(manifest["rule_sha256"], sha(RULE.read_bytes()))
            self.assertEqual(manifest["csv_sha256"], sha((root / "a.csv").read_bytes()))
            self.assertEqual(manifest["accepted_row_count"], 3)
            self.assertFalse(manifest["normal_clean_export_blocked"])
            self.assertEqual(json.loads(Path(receipt["audit_path"]).read_bytes()), result.audit_dict())
            self.assertEqual(json.loads(Path(receipt["provenance_path"]).read_bytes()), result.provenance_dict())
            for name, descriptor in manifest["artifacts"].items():
                self.assertEqual(sha((root / name).read_bytes()), descriptor["sha256"])
                self.assertEqual(len((root / name).read_bytes()), descriptor["bytes"])

    def test_sidecar_collision_does_not_create_csv_or_overwrite_evidence(self):
        result = execute(self.source, self.rule)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root / "a.provenance.json"
            existing.write_bytes(b"preserve unrelated evidence")
            with self.assertRaises(ExportBlocked):
                export_result(result, root / "a.csv")
            self.assertEqual(list(root.iterdir()), [existing])
            self.assertEqual(existing.read_bytes(), b"preserve unrelated evidence")

    def test_clean_artifacts_rollback_on_write_failure(self):
        from spoollens import engine
        result = execute(self.source, self.rule)
        original = engine._exclusive_atomic_write
        def fail_manifest(path, data):
            if path.name.endswith(".manifest.json"):
                raise OSError("simulated disk failure")
            original(path, data)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.object(engine, "_exclusive_atomic_write", side_effect=fail_manifest):
                with self.assertRaises(OSError):
                    export_result(result, root / "a.csv")
            self.assertEqual(list(root.iterdir()), [])

    def test_exception_requires_boolean_not_truthy_string(self):
        result = execute(self.source, self.rule)
        with self.assertRaises(ExportBlocked):
            export_result(result, "not-created.zip", exception="yes")


class CliTests(unittest.TestCase):
    def cli(self, *args):
        return subprocess.run([sys.executable, "-m", "spoollens.cli", *map(str, args)], cwd=ROOT,
                              capture_output=True, text=True, check=False)

    def test_cli_clean_and_blocked_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            good = self.cli("replay", FIXTURES / "A_clean.txt", "--rule", RULE, "--output", root / "a.csv")
            self.assertEqual(good.returncode, 0, good.stderr)
            self.assertEqual((root / "a.csv").read_bytes(), (EXPECTED / "A_clean.rows.csv").read_bytes())
            blocked = self.cli("replay", FIXTURES / "C_dangerous.txt", "--rule", RULE, "--output", root / "c.csv",
                               "--audit", root / "audit.json", "--provenance", root / "provenance.json")
            self.assertEqual(blocked.returncode, 2)
            self.assertFalse((root / "c.csv").exists())
            self.assertEqual(json.loads(blocked.stdout)["rejected_count"], 5)
            self.assertEqual(json.loads((root / "audit.json").read_bytes()), json.loads((EXPECTED / "C_dangerous.accounting.json").read_bytes()))
            exception = self.cli("replay", FIXTURES / "C_dangerous.txt", "--rule", RULE, "--exception-bundle", root / "c.zip")
            self.assertEqual(exception.returncode, 0, exception.stderr)
            self.assertTrue((root / "c.zip").exists())

    def test_cli_explicit_evidence_paths_can_match_automatic_sidecars(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            good = self.cli("replay", FIXTURES / "A_clean.txt", "--rule", RULE,
                            "--output", root / "a.csv", "--audit", root / "a.audit.json",
                            "--provenance", root / "a.provenance.json")
            self.assertEqual(good.returncode, 0, good.stderr)
            self.assertEqual(len(list(root.iterdir())), 4)

    def test_cli_queries_exact_evidence(self):
        field = self.cli("inspect", FIXTURES / "B_boundaries.txt", "--rule", RULE, "--row", 2, "--field", "price")
        self.assertEqual(field.returncode, 0, field.stderr)
        evidence = json.loads(field.stdout)["evidence"]
        self.assertEqual(evidence["value"], "0.20")
        self.assertEqual(evidence["raw"], "    0.20")
        self.assertEqual(evidence["line"], 12)
        self.assertEqual(evidence["range"], [39, 47])
        line = self.cli("inspect", FIXTURES / "C_dangerous.txt", "--rule", RULE, "--line", 7)
        self.assertEqual(json.loads(line.stdout)["reason"], "non_space_separator")


if __name__ == "__main__":
    unittest.main()
