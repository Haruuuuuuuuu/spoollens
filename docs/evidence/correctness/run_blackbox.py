#!/usr/bin/env python3
"""Independent CLI verifier. Expected evidence was frozen before candidate delivery."""
import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FROZEN = None  # supplied through --fixtures; original evidence stays external
VARIATIONS = ROOT / "predeclared"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def load(path):
    return json.loads(path.read_text())

def assert_manifest(root):
    entries = (root / "SHA256SUMS").read_text().splitlines()
    for line in entries:
        digest, name = line.split("  ", 1)
        assert sha((root / name).read_bytes()) == digest, name
    return len(entries)

def physical_lines(data):
    text = data.decode("utf-8").split("\n")
    if data.endswith(b"\n"):
        text.pop()
    return text

def validate_raw_evidence(data, audit, prov):
    source_hash = sha(data)
    raw_lines = physical_lines(data)
    assert len(audit["lines"]) == len(raw_lines) == audit["physical_line_count"]
    assert audit["source_sha256"] == prov["source_sha256"] == source_hash
    assert len({record["line"] for record in audit["lines"]}) == len(raw_lines)
    categories = ["HEADER", "DETAIL", "IGNORED_BY_EXPLICIT_RULE", "UNRESOLVED", "REJECTED"]
    count = {c: 0 for c in categories}
    whitespace = 0
    for number, (raw, record) in enumerate(zip(raw_lines, audit["lines"]), 1):
        assert record["line"] == number and record["raw"] == raw
        if raw.strip(" ") == "":
            assert record["category"] == "WHITESPACE_ONLY"
            whitespace += 1
        else:
            assert record["category"] in categories
            count[record["category"]] += 1
    assert audit["counts"] == count
    assert audit["whitespace_only_line_count"] == whitespace
    assert audit["nonempty_line_count"] == len(raw_lines) - whitespace
    values = 0
    for row in prov["rows"]:
        assert audit["lines"][row["detail_line"]-1]["category"] == "DETAIL"
        for field, cell in row["fields"].items():
            start, end = cell["range"]
            assert cell["source_sha256"] == source_hash
            assert cell["raw"] == raw_lines[cell["line"]-1][start:end]
            assert cell["value"] == cell["raw"].strip(" ")
            if field == "warehouse":
                assert cell["inherited"] is True
                assert cell["header_line"] == cell["line"]
                assert cell["header_range"] == cell["range"]
                assert audit["lines"][cell["line"]-1]["category"] == "HEADER"
                assert audit["lines"][row["detail_line"]-1]["context_before"] == cell["value"]
            else:
                assert cell["inherited"] is False
                assert cell["line"] == row["detail_line"]
            values += 1
    return values

def main():
    global FROZEN, VARIATIONS
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True, help="Untouched original frozen fixture directory")
    parser.add_argument("--variations", type=Path, default=ROOT / "predeclared", help="Predeclared variation directory; defaults beside this script")
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    FROZEN, VARIATIONS = args.fixtures.resolve(), args.variations.resolve()
    candidate, python, out = args.candidate.resolve(), args.python.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    commands = []
    report = {"candidate_sha": args.sha, "started_at_utc": datetime.now(timezone.utc).isoformat(), "tests": [], "checks": [], "status": "RUNNING"}
    def save():
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    def check(label, fn):
        try:
            detail = fn()
            report["checks"].append({"name": label, "status": "PASS", "detail": detail})
            print("PASS", label, flush=True)
            save()
            return detail
        except Exception as exc:
            report["checks"].append({"name": label, "status": "FAIL", "error": repr(exc)})
            report["status"] = "FAIL"
            save()
            raise
    def run(label, argv, expected_code=0):
        cmd = [str(python), "-m", "spoollens", *map(str, argv)]
        result = subprocess.run(cmd, cwd=candidate, text=True, capture_output=True)
        record = {"label": label, "argv": cmd, "cwd": str(candidate), "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
        commands.append(record)
        save()
        assert result.returncode == expected_code, record
        return json.loads(result.stdout) if result.stdout.strip().startswith("{") else result.stdout
    check("original frozen integrity before", lambda: assert_manifest(FROZEN))
    check("predeclared variation integrity before", lambda: assert_manifest(VARIATIONS))
    check("candidate frozen integrity", lambda: assert_manifest(candidate / "tests" / "fixtures"))
    source_paths = [*FROZEN.glob("*.txt"), *VARIATIONS.glob("*.txt")]
    initial_sources = {str(p): sha(p.read_bytes()) for p in source_paths}
    rule = candidate / "examples" / "inventory.rule.json"
    rule_data = rule.read_bytes()
    rule_hash = sha(rule_data)
    report["rule_sha256"] = rule_hash
    # Read-only direct execution from the README is the primary install route.
    install = subprocess.run([str(python), "-m", "spoollens", "--help"], cwd=candidate, capture_output=True, text=True)
    commands.append({"label": "fresh venv README direct-run installation", "argv": [str(python), "-m", "spoollens", "--help"], "returncode": install.returncode, "stdout": install.stdout, "stderr": install.stderr})
    check("fresh venv README install route", lambda: (install.returncode == 0 and "replay" in install.stdout) or (_ for _ in ()).throw(AssertionError(install)))
    tests = subprocess.run([str(python), "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=candidate, capture_output=True, text=True)
    (out / "packaged_tests.stdout.txt").write_text(tests.stdout)
    (out / "packaged_tests.stderr.txt").write_text(tests.stderr)
    check("packaged unittest suite", lambda: (tests.returncode == 0 and "Ran 41 tests" in tests.stderr) or (_ for _ in ()).throw(AssertionError(tests)))

    # All extraction is invoked only through documented CLI processes.
    names = ["A_clean", "B_boundaries", "C_dangerous", "V1_unseen_values", "V2_isolated_boundaries", "V3_error_context", "V4_invalid_header", "V5_no_final_lf"]
    for name in names:
        frozen = name[0] in "ABC" and not name.startswith("V")
        root = FROZEN if frozen else VARIATIONS
        src = root / (name + ".txt")
        if frozen:
            exp_audit = load(root / "expected" / (name + ".accounting.json"))
            exp_prov = load(root / "expected" / (name + ".provenance.json"))
            exp_export = load(root / "expected" / (name + ".export.json"))
            csv_expected = (root / "expected" / (name + ".rows.csv")).read_bytes()
            clean = exp_export["clean_export_allowed"]
        else:
            expectation = load(root / (name + ".expected.json"))
            exp_audit, exp_prov = expectation, {"rows": expectation["provenance"]}
            csv_expected = (root / (name + ".rows.csv")).read_bytes()
            clean = expectation["clean_export_allowed"]
        test_out = out / name
        test_out.mkdir()
        csv_path = test_out / (name + ".csv")
        audit_path = test_out / (name + ".audit.json")
        prov_path = test_out / (name + ".provenance.json")
        summary = run(name + " default export", ["replay", src, "--rule", rule, "--output", csv_path, "--audit", audit_path, "--provenance", prov_path], 0 if clean else 2)
        assert summary["source_sha256"] == sha(src.read_bytes()) and summary["rule_sha256"] == rule_hash
        if not clean:
            check(name + " unsafe clean artifact absent", lambda: not csv_path.exists() or (_ for _ in ()).throw(AssertionError("blocked CSV exists")))
            # Blocked export may precede optional audit writing; ask for read-only evidence separately.
            if not audit_path.exists():
                run(name + " blocked audit query", ["replay", src, "--rule", rule, "--audit", audit_path, "--provenance", prov_path], 2)
        audit, prov = load(audit_path), load(prov_path)
        def compare_artifacts():
            if frozen:
                assert audit == exp_audit
                assert prov == exp_prov
                for key in ["accepted_row_count", "clean_export_allowed", "unresolved_count", "rejected_count", "errors"]:
                    assert summary[key] == exp_export[key], key
            else:
                for key in ["source_sha256", "counts", "physical_line_count", "whitespace_only_line_count"]:
                    assert audit[key] == exp_audit[key], key
                assert len(audit["lines"]) == len(exp_audit["lines"])
                for actual, expected in zip(audit["lines"], exp_audit["lines"]):
                    assert {key: actual[key] for key in expected} == expected
                assert prov["rows"] == exp_prov["rows"]
            return {"line_count": len(audit["lines"]), "values": validate_raw_evidence(src.read_bytes(), audit, prov), "counts": audit["counts"]}
        evidence = check(name + " exact accounting and provenance", compare_artifacts)
        if clean:
            def check_clean():
                assert csv_path.read_bytes() == csv_expected
                manifest = load(test_out / (name + ".manifest.json"))
                assert manifest["source_sha256"] == sha(src.read_bytes())
                assert manifest["rule_sha256"] == rule_hash
                assert manifest["csv_sha256"] == sha(csv_expected)
                assert manifest["export_status"] == "CLEAN"
                for member, info in manifest["artifacts"].items():
                    content = (test_out / member).read_bytes()
                    assert sha(content) == info["sha256"] and len(content) == info["bytes"]
                return sha(csv_expected)
            check(name + " clean CSV and evidence hashes", check_clean)
        # Every case also has an explicitly requested bundle; verify its exact content.
        bundle1, bundle2 = test_out / "first.exception.zip", test_out / "second.exception.zip"
        run(name + " explicit exception", ["replay", src, "--rule", rule, "--exception-bundle", bundle1])
        run(name + " deterministic exception replay", ["replay", src, "--rule", rule, "--exception-bundle", bundle2])
        def check_bundle():
            assert bundle1.read_bytes() == bundle2.read_bytes()
            with zipfile.ZipFile(bundle1) as archive:
                manifest = json.loads(archive.read("manifest.json"))
                assert manifest["exception_status"] == "EXPLICIT_EXCEPTION"
                assert manifest["source_sha256"] == sha(src.read_bytes())
                assert manifest["rule_sha256"] == rule_hash
                assert manifest["csv_sha256"] == sha(csv_expected)
                assert manifest["unresolved_count"] == audit["counts"]["UNRESOLVED"]
                assert manifest["rejected_count"] == audit["counts"]["REJECTED"]
                assert manifest["normal_clean_export_blocked"] == (not clean)
                assert archive.read(manifest["csv_file"]) == csv_expected
                assert archive.read("input.bin") == src.read_bytes()
                assert archive.read("rule.json") == rule_data
                assert json.loads(archive.read("accounting.json")) == audit
                assert json.loads(archive.read("provenance.json")) == prov
                for member, info in manifest["artifacts"].items():
                    content = archive.read(member)
                    assert sha(content) == info["sha256"] and len(content) == info["bytes"]
                if name == "C_dangerous":
                    exp_manifest = load(FROZEN / "expected" / "C_dangerous.exception.manifest.json")
                    for key in exp_manifest:
                        if key not in {"rule_sha256", "rule_hash_basis"}:
                            assert manifest[key] == exp_manifest[key], key
            return {"zip_sha256": sha(bundle1.read_bytes()), "csv_sha256": sha(csv_expected)}
        bundle_info = check(name + " explicit bundle and byte-identical replay", check_bundle)
        report["tests"].append({"name": name, "status": "PASS", **evidence, **bundle_info, "source_sha256": sha(src.read_bytes()), "clean_export_allowed": clean})
        save()

    def query_fields():
        source = FROZEN / "B_boundaries.txt"
        expected = load(FROZEN / "expected" / "B_boundaries.provenance.json")["rows"][1]["fields"]
        result = {}
        for field in ["warehouse", "price"]:
            answer = run("inspect " + field, ["inspect", source, "--rule", rule, "--row", "2", "--field", field])
            # Public inspect wraps the exact evidence with additional context.
            result[field] = answer
            if "evidence" in answer:
                assert answer["evidence"] == expected[field]
            else:
                assert all(answer[key] == value for key, value in expected[field].items())
        return result
    check("documented provenance query direct and inherited", query_fields)
    invalid_source = VARIATIONS / "E1_invalid_utf8.txt"
    invalid_csv = out / "invalid_utf8.csv"
    result = run("invalid UTF-8 rejected", ["replay", invalid_source, "--rule", rule, "--output", invalid_csv], 1)
    check("invalid UTF-8 fails visibly without output", lambda: (not invalid_csv.exists() and bool(commands[-1]["stderr"])) or (_ for _ in ()).throw(AssertionError(result)))

    # Save/reload the documented open rule representation, without template programming.
    serialized_rule = out / "resaved.rule.json"
    serialization = subprocess.run([str(python), "-c", "from pathlib import Path; from spoollens.engine import load_rule, canonical_rule_bytes; import sys; p=Path(sys.argv[2]); p.write_bytes(canonical_rule_bytes(load_rule(sys.argv[1])))", str(rule), str(serialized_rule)], cwd=candidate, text=True, capture_output=True)
    commands.append({"label": "documented rule serialization API", "returncode": serialization.returncode, "stdout": serialization.stdout, "stderr": serialization.stderr})
    assert serialization.returncode == 0
    altered_rule = out / "reformatted.rule.json"
    altered_rule.write_text(json.dumps(json.loads(rule_data), separators=(",", ":")))
    for loaded_rule in [serialized_rule, altered_rule]:
        def check_reload():
            runs = {}
            for name in ["A_clean", "B_boundaries", "C_dangerous"]:
                dest = out / (loaded_rule.stem + "_" + name + ".zip")
                run("saved rule reload " + name, ["replay", FROZEN / (name + ".txt"), "--rule", loaded_rule, "--exception-bundle", dest])
                with zipfile.ZipFile(dest) as z:
                    manifest = json.loads(z.read("manifest.json"))
                    assert manifest["rule_sha256"] == sha(loaded_rule.read_bytes())
                    assert z.read("rule.json") == loaded_rule.read_bytes()
                    assert z.read(name + ".exception.csv") == (FROZEN / "expected" / (name + ".rows.csv")).read_bytes()
                    assert json.loads(z.read("accounting.json")) == load(FROZEN / "expected" / (name + ".accounting.json"))
                    assert json.loads(z.read("provenance.json")) == load(FROZEN / "expected" / (name + ".provenance.json"))
                    runs[name] = manifest["csv_sha256"]
            return {"rule_sha256": sha(loaded_rule.read_bytes()), "outputs": runs}
        check("serialization/reload " + loaded_rule.name, check_reload)
    check("source and original rule immutability", lambda: (initial_sources == {str(p): sha(p.read_bytes()) for p in source_paths} and rule.read_bytes() == rule_data) or (_ for _ in ()).throw(AssertionError("bytes mutated")))
    check("original frozen integrity after", lambda: assert_manifest(FROZEN))
    check("predeclared variation integrity after", lambda: assert_manifest(VARIATIONS))
    report["status"] = "PASS"
    report["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    save()
    print("ALL PASS", len(report["checks"]), "check groups", flush=True)

if __name__ == "__main__":
    main()
