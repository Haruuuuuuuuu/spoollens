#!/usr/bin/env python3
"""Post-blind comparison against the immutable, separately frozen oracle."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import zipfile
from validate_abc import digest, read_json, validate_raw


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--release-root', type=Path, required=True)
    p.add_argument('--cli', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    root, cli, out = (x.resolve() for x in (args.release_root, args.cli, args.out))
    out.mkdir(parents=True, exist_ok=False)
    truth, usability = root / 'unseen_truth', root / 'usability'
    source = root / 'unseen_input/workshop-replenishment-06a.txt'
    freeze = read_json(truth / 'FREEZE.json')
    policy = read_json(truth / 'PRIVATE_ACCEPTANCE_POLICY.json')
    source_bytes = source.read_bytes()
    expected_csv = (truth / 'expected.rows.exception.csv').read_bytes()
    expected_prov = read_json(truth / 'expected.canonical.provenance.json')
    commands, reports = [], []
    assert digest((truth / 'FREEZE.json').read_bytes()) == 'f8cafe2f33c3f9d8d33d3054854ee7b0b847d6325cd89f16434fd6f701d75c99'
    for path, info in freeze['files'].items():
        data = (root / path).read_bytes()
        assert digest(data) == info['sha256'] and len(data) == info['bytes']
    for entry in (usability / 'CANDIDATE-ARTIFACTS.sha256').read_text().splitlines():
        sha, name = entry.split(maxsplit=1)
        assert digest((usability / name).read_bytes()) == sha

    def run(argv, code):
        cmd = [str(cli), *map(str, argv)]
        done = subprocess.run(cmd, cwd=out, text=True, capture_output=True)
        commands.append({'argv':cmd, 'returncode':done.returncode, 'stdout':done.stdout, 'stderr':done.stderr})
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        assert done.returncode == code, commands[-1]
        return json.loads(done.stdout)

    def compare_accounting(actual, expected, rule):
        # Only author-selected ignore labels may differ, as explicitly permitted
        # in the original freeze. Match literals/modes/reset intent first.
        names = {}
        for authored in rule['ignore']:
            match = [q for q in policy['canonical_ignore_intent'] if all(authored[k] == q[k] for k in ('mode', 'text', 'reset'))]
            assert len(match) == 1
            names[authored['name']] = match[0]['name']
        normalized = copy.deepcopy(actual)
        differences = []
        for line in normalized['lines']:
            if line['category'] == 'IGNORED_BY_EXPLICIT_RULE':
                original = line['reason']
                line['reason'] = names[original]
                if original != line['reason']:
                    differences.append({'line':line['line'], 'actual_label':original, 'frozen_label':line['reason']})
        assert normalized == expected
        return differences

    for stage, filename in [('pre_handling', 'authored-rule-initial.json'), ('final', 'authored-rule-final.json')]:
        rule_path = usability / filename
        rule = read_json(rule_path)
        expected_audit = read_json(truth / ('expected.' + stage + '.accounting.json'))
        expected_export = read_json(truth / ('expected.' + stage + '.export.json'))
        dest = out / stage
        dest.mkdir()
        summary = run(['replay', source, '--rule', rule_path, '--output', dest / 'blocked-clean.csv', '--audit', dest / 'audit.json', '--provenance', dest / 'provenance.json'], 2)
        assert not (dest / 'blocked-clean.csv').exists()
        for key, value in expected_export.items():
            if key != 'rule_sha256':
                assert summary[key] == value, (stage, key)
        assert summary['rule_sha256'] == digest(rule_path.read_bytes())
        audit, provenance = read_json(dest / 'audit.json'), read_json(dest / 'provenance.json')
        labels = compare_accounting(audit, expected_audit, rule)
        assert provenance == expected_prov
        values = validate_raw(source_bytes, audit, provenance)
        report = {'stage':stage, 'status':'PASS', 'physical_lines':len(audit['lines']), 'counts':audit['counts'], 'provenance_values':values, 'canonical_provenance_exact':True, 'coordinate_differences':[], 'permitted_ignore_label_differences':labels, 'clean_export_blocked':True, 'clean_csv_absent':True, 'rule_sha256':digest(rule_path.read_bytes())}
        if stage == 'final':
            run(['replay', source, '--rule', rule_path, '--exception-bundle', dest / 'independent.exception.zip'], 0)
            ui_bundle = usability / 'workshop-exception.zip'
            assert ui_bundle.read_bytes() == (dest / 'independent.exception.zip').read_bytes() == (usability / 'replayed-exception.zip').read_bytes()
            with zipfile.ZipFile(ui_bundle) as z:
                manifest = json.loads(z.read('manifest.json'))
                assert manifest['exception_status'] == 'EXPLICIT_EXCEPTION'
                assert manifest['normal_clean_export_blocked'] is True
                assert manifest['accepted_row_count'] == 18
                assert manifest['unresolved_count'] == 0 and manifest['rejected_count'] == 1
                assert manifest['omitted_line_numbers'] == [12]
                assert z.read(manifest['csv_file']) == expected_csv == (usability / 'workshop-replenishment-06a.exception.csv').read_bytes()
                assert z.read('input.bin') == source_bytes
                assert z.read('rule.json') == rule_path.read_bytes()
                assert json.loads(z.read('accounting.json')) == audit
                assert json.loads(z.read('provenance.json')) == expected_prov
                assert manifest['source_sha256'] == digest(source_bytes)
                assert manifest['rule_sha256'] == digest(rule_path.read_bytes())
                assert manifest['csv_sha256'] == digest(expected_csv)
                for name, info in manifest['artifacts'].items():
                    data = z.read(name)
                    assert digest(data) == info['sha256'] and len(data) == info['bytes']
            report.update(exception_csv_exact=True, exception_bundle_hashes_verified=True, ui_reopen_and_independent_replay_byte_identical=True, exception_zip_sha256=digest(ui_bundle.read_bytes()), extra_authored_space_guard=[1,3])
        reports.append(report)
    assert source.read_bytes() == source_bytes
    assert digest(source_bytes) == policy['source']['sha256']
    for path, info in freeze['files'].items():
        assert digest((root / path).read_bytes()) == info['sha256']
    answer = {'status':'PASS', 'frozen_at_utc':freeze['frozen_at_utc'], 'blind_outcomes_frozen_at_utc':(usability / 'outcomes-frozen-at.txt').read_text().strip(), 'source_immutable':True, 'oracle_unchanged':True, 'csv_sha256':digest(expected_csv), 'stages':reports}
    (out / 'report.json').write_text(json.dumps(answer, indent=2) + '\n')
    print(json.dumps(answer, indent=2))


if __name__ == '__main__':
    main()
