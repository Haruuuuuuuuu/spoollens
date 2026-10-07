#!/usr/bin/env python3
"""Independent final validation, immutable A/B/C truth; uses installed CLI only."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_bytes())


def validate_raw(source, audit, provenance):
    raw = source.decode('ascii').split('\n')
    if source.endswith(b'\n'):
        raw.pop()
    assert len(raw) == audit['physical_line_count'] == len(audit['lines'])
    assert audit['source_sha256'] == provenance['source_sha256'] == digest(source)
    categories = dict.fromkeys(('HEADER', 'DETAIL', 'IGNORED_BY_EXPLICIT_RULE', 'UNRESOLVED', 'REJECTED'), 0)
    blanks = 0
    for index, (line, account) in enumerate(zip(raw, audit['lines']), 1):
        assert account['line'] == index and account['raw'] == line
        if not line.strip(' '):
            assert account['category'] == 'WHITESPACE_ONLY'
            blanks += 1
        else:
            categories[account['category']] += 1
    assert categories == audit['counts']
    assert blanks == audit['whitespace_only_line_count']
    assert len(raw) - blanks == audit['nonempty_line_count']
    values = 0
    for row in provenance['rows']:
        assert audit['lines'][row['detail_line']-1]['category'] == 'DETAIL'
        for field, cell in row['fields'].items():
            start, end = cell['range']
            assert cell['source_sha256'] == digest(source)
            assert raw[cell['line']-1][start:end] == cell['raw']
            assert cell['raw'].strip(' ') == cell['value']
            if cell['inherited']:
                assert field == 'warehouse'
                assert cell['line'] == cell['header_line']
                assert cell['range'] == cell['header_range']
                assert audit['lines'][cell['line']-1]['category'] == 'HEADER'
                assert audit['lines'][row['detail_line']-1]['context_before'] == cell['value']
            else:
                assert cell['line'] == row['detail_line']
            values += 1
    return values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--cli', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    candidate, cli, out = (x.resolve() for x in (args.candidate, args.cli, args.out))
    out.mkdir(parents=True, exist_ok=False)
    fixtures = candidate / 'tests/fixtures'
    expected = fixtures / 'expected'
    rule = candidate / 'examples/inventory.rule.json'
    commands, result = [], {'status': 'RUNNING', 'cases': []}
    inputs = [rule] + [p for p in fixtures.rglob('*') if p.is_file()]
    initial = {str(p): digest(p.read_bytes()) for p in inputs}

    def save():
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        (out / 'report.json').write_text(json.dumps(result, indent=2) + '\n')

    def run(argv, code=0):
        full = [str(cli), *map(str, argv)]
        p = subprocess.run(full, cwd=out, text=True, capture_output=True)
        commands.append({'argv': full, 'cwd': str(out), 'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr})
        save()
        assert p.returncode == code, commands[-1]
        return json.loads(p.stdout)

    try:
        for entry in (fixtures / 'SHA256SUMS').read_text().splitlines():
            sha, name = entry.split(maxsplit=1)
            assert digest((fixtures / name.lstrip('*')).read_bytes()) == sha
        for name in ('A_clean', 'B_boundaries', 'C_dangerous'):
            source = fixtures / (name + '.txt')
            source_bytes = source.read_bytes()
            want_csv = (expected / (name + '.rows.csv')).read_bytes()
            want_audit = read_json(expected / (name + '.accounting.json'))
            want_prov = read_json(expected / (name + '.provenance.json'))
            want_export = read_json(expected / (name + '.export.json'))
            clean = want_export['clean_export_allowed']
            reps = []
            for repetition in ('first', 'replayed'):
                dest = out / name / repetition
                dest.mkdir(parents=True)
                csv = dest / (name + '.csv')
                audit_path = dest / (name + '.audit.json')
                prov_path = dest / (name + '.provenance.json')
                summary = run(['replay', source, '--rule', rule, '--output', csv, '--audit', audit_path, '--provenance', prov_path], 0 if clean else 2)
                audit, prov = read_json(audit_path), read_json(prov_path)
                assert audit == want_audit and prov == want_prov
                for key in ('accepted_row_count', 'clean_export_allowed', 'unresolved_count', 'rejected_count', 'errors'):
                    assert summary[key] == want_export[key], (name, key)
                assert summary['source_sha256'] == digest(source_bytes)
                assert summary['rule_sha256'] == digest(rule.read_bytes())
                values = validate_raw(source_bytes, audit, prov)
                if clean:
                    assert csv.read_bytes() == want_csv
                    manifest = read_json(dest / (name + '.manifest.json'))
                    assert manifest['export_status'] == 'CLEAN'
                    assert manifest['source_sha256'] == digest(source_bytes)
                    assert manifest['rule_sha256'] == digest(rule.read_bytes())
                    for file, info in manifest['artifacts'].items():
                        data = (dest / file).read_bytes()
                        assert digest(data) == info['sha256'] and len(data) == info['bytes']
                else:
                    assert not csv.exists()
                bundle = dest / (name + '.exception.zip')
                run(['replay', source, '--rule', rule, '--exception-bundle', bundle])
                with zipfile.ZipFile(bundle) as archive:
                    manifest = json.loads(archive.read('manifest.json'))
                    assert manifest['exception_status'] == 'EXPLICIT_EXCEPTION'
                    assert manifest['normal_clean_export_blocked'] == (not clean)
                    assert manifest['unresolved_count'] == want_export['unresolved_count']
                    assert manifest['rejected_count'] == want_export['rejected_count']
                    assert manifest['source_sha256'] == digest(source_bytes)
                    assert manifest['rule_sha256'] == digest(rule.read_bytes())
                    assert archive.read('input.bin') == source_bytes
                    assert archive.read('rule.json') == rule.read_bytes()
                    assert archive.read(manifest['csv_file']) == want_csv
                    assert json.loads(archive.read('accounting.json')) == want_audit
                    assert json.loads(archive.read('provenance.json')) == want_prov
                    for file, info in manifest['artifacts'].items():
                        data = archive.read(file)
                        assert digest(data) == info['sha256'] and len(data) == info['bytes']
                    if name == 'C_dangerous':
                        frozen_manifest = read_json(expected / 'C_dangerous.exception.manifest.json')
                        for key, value in frozen_manifest.items():
                            if key not in ('rule_sha256', 'rule_hash_basis'):
                                assert manifest[key] == value, key
                reps.append(dest)
            first = {p.name: p.read_bytes() for p in reps[0].iterdir()}
            second = {p.name: p.read_bytes() for p in reps[1].iterdir()}
            assert first == second
            for field in ('warehouse', 'qty'):
                inspected = run(['inspect', source, '--rule', rule, '--row', '1', '--field', field])
                assert inspected['evidence'] == want_prov['rows'][0]['fields'][field]
            result['cases'].append({'name': name, 'status': 'PASS', 'physical_lines': len(want_audit['lines']), 'provenance_values': values, 'counts': want_audit['counts'], 'clean_export_allowed': clean, 'deterministic_all_artifacts': True, 'source_sha256': digest(source_bytes)})
            save()
        assert initial == {str(p): digest(p.read_bytes()) for p in inputs}
        result.update(status='PASS', source_and_rule_immutable=True, frozen_manifest_intact=True, input_hashes=initial)
        save()
        print(json.dumps({k: v for k, v in result.items() if k != 'input_hashes'}, indent=2))
    except BaseException as exc:
        result.update(status='FAIL', error=repr(exc))
        save()
        raise


if __name__ == '__main__':
    main()
