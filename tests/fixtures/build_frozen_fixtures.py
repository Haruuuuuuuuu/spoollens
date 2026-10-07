#!/usr/bin/env python3
"""One-time fixture authoring, not a report parser. All expected rows/categories are enumerated manually."""
from pathlib import Path
import csv
import hashlib
import io
import json
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
EXPECTED = ROOT / 'expected'
EXPECTED.mkdir(exist_ok=True)

def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def detail(item, description, qty, price):
    return f'{item:<8}  {description:<20}  {qty:>5}  {price:>8}'

def warehouse(value):
    return 'WAREHOUSE: ' + f'{value:<8}'

COL = detail('ITEM', 'DESCRIPTION', 'QTY', 'PRICE')
shifted = detail('C111', 'SHIFTED QTY', '17', '2.00')
# Move the QTY cell right by one column, consuming one separator space.
# Total width stays 47; naive slicing would silently return QTY=1 instead of 17.
shifted = shifted[:32] + ' ' + shifted[32:38] + shifted[39:]
malformed = detail('C112', 'BAD QUANTITY', '2O', '8.00')
truncated = detail('C113', 'SHORT RECORD', '9', '4.75')[:-1]

# Input lines, their classifications, and expected rows are each authored explicitly.
# No detector or parser executes in this generator.
reports = {
    'A_clean': {
        'lines': [
            'INVENTORY VALUATION  PAGE 001', warehouse('NORTH'), '', COL,
            detail('A100', 'WIDGET BLUE', '12', '9.95'),
            detail('A101', 'WIDGET RED', '5', '10.50'), '   ',
            warehouse('SOUTH'), detail('A100', 'WIDGET BLUE', '8', '9.95'),
            'END OF PAGE',
        ],
        'categories': [
            ('IGNORED_BY_EXPLICIT_RULE', 'page_header', None),
            ('HEADER', 'warehouse_header', 'NORTH'),
            ('WHITESPACE_ONLY', 'blank_line', 'NORTH'),
            ('IGNORED_BY_EXPLICIT_RULE', 'column_header', 'NORTH'),
            ('DETAIL', 'accepted_detail', 'NORTH'),
            ('DETAIL', 'accepted_detail', 'NORTH'),
            ('WHITESPACE_ONLY', 'blank_line', 'NORTH'),
            ('HEADER', 'warehouse_header', 'SOUTH'),
            ('DETAIL', 'accepted_detail', 'SOUTH'),
            ('IGNORED_BY_EXPLICIT_RULE', 'page_footer', None),
        ],
        'rows': [
            (5, 2, 'NORTH', 'A100', '12', '9.95'),
            (6, 2, 'NORTH', 'A101', '5', '10.50'),
            (9, 8, 'SOUTH', 'A100', '8', '9.95'),
        ],
        'errors': [],
    },
    'B_boundaries': {
        'lines': [
            'INVENTORY VALUATION  PAGE 001', warehouse('NORTH'), COL,
            detail('B200', 'HEX BOLT', '24', '0.35'), '', 'END OF PAGE', '\f',
            'INVENTORY VALUATION  PAGE 002', COL, '', warehouse('SOUTH'),
            detail('B201', 'LOCK NUT', '40', '0.20'), '    ', warehouse('EAST'),
            detail('B202', 'FLAT WASHER', '60', '0.10'), COL,
            detail('B203', 'SPRING WASHER', '30', '0.15'), 'END OF PAGE',
        ],
        'categories': [
            ('IGNORED_BY_EXPLICIT_RULE', 'page_header', None),
            ('HEADER', 'warehouse_header', 'NORTH'),
            ('IGNORED_BY_EXPLICIT_RULE', 'column_header', 'NORTH'),
            ('DETAIL', 'accepted_detail', 'NORTH'),
            ('WHITESPACE_ONLY', 'blank_line', 'NORTH'),
            ('IGNORED_BY_EXPLICIT_RULE', 'page_footer', None),
            ('IGNORED_BY_EXPLICIT_RULE', 'form_feed_boundary', None),
            ('IGNORED_BY_EXPLICIT_RULE', 'page_header', None),
            ('IGNORED_BY_EXPLICIT_RULE', 'column_header', None),
            ('WHITESPACE_ONLY', 'blank_line', None),
            ('HEADER', 'warehouse_header', 'SOUTH'),
            ('DETAIL', 'accepted_detail', 'SOUTH'),
            ('WHITESPACE_ONLY', 'blank_line', 'SOUTH'),
            ('HEADER', 'warehouse_header', 'EAST'),
            ('DETAIL', 'accepted_detail', 'EAST'),
            ('IGNORED_BY_EXPLICIT_RULE', 'column_header', 'EAST'),
            ('DETAIL', 'accepted_detail', 'EAST'),
            ('IGNORED_BY_EXPLICIT_RULE', 'page_footer', None),
        ],
        'rows': [
            (4, 2, 'NORTH', 'B200', '24', '0.35'),
            (12, 11, 'SOUTH', 'B201', '40', '0.20'),
            (15, 14, 'EAST', 'B202', '60', '0.10'),
            (17, 14, 'EAST', 'B203', '30', '0.15'),
        ],
        'errors': [],
    },
    'C_dangerous': {
        'lines': [
            'INVENTORY VALUATION  PAGE 001', COL,
            detail('C000', 'ORPHAN BEFORE', '2', '1.00'), '', warehouse('NORTH'),
            detail('C100', 'VALID GEAR', '3', '12.50'), shifted, malformed,
            'NOTICE: PRICE REVIEW PENDING', truncated, 'END OF PAGE', '\f',
            'INVENTORY VALUATION  PAGE 002', COL,
            detail('C200', 'ORPHAN AFTER', '1', '6.00'), warehouse('SOUTH'),
            detail('C201', 'VALID SEAL', '6', '3.25'), '  ', 'END OF PAGE',
        ],
        'categories': [
            ('IGNORED_BY_EXPLICIT_RULE', 'page_header', None),
            ('IGNORED_BY_EXPLICIT_RULE', 'column_header', None),
            ('REJECTED', 'missing_warehouse_context', None),
            ('WHITESPACE_ONLY', 'blank_line', None),
            ('HEADER', 'warehouse_header', 'NORTH'),
            ('DETAIL', 'accepted_detail', 'NORTH'),
            ('REJECTED', 'non_space_separator', 'NORTH'),
            ('REJECTED', 'invalid_qty_integer', 'NORTH'),
            ('UNRESOLVED', 'no_explicit_rule_matched', 'NORTH'),
            ('REJECTED', 'invalid_record_width', 'NORTH'),
            ('IGNORED_BY_EXPLICIT_RULE', 'page_footer', None),
            ('IGNORED_BY_EXPLICIT_RULE', 'form_feed_boundary', None),
            ('IGNORED_BY_EXPLICIT_RULE', 'page_header', None),
            ('IGNORED_BY_EXPLICIT_RULE', 'column_header', None),
            ('REJECTED', 'missing_warehouse_context', None),
            ('HEADER', 'warehouse_header', 'SOUTH'),
            ('DETAIL', 'accepted_detail', 'SOUTH'),
            ('WHITESPACE_ONLY', 'blank_line', 'SOUTH'),
            ('IGNORED_BY_EXPLICIT_RULE', 'page_footer', None),
        ],
        'rows': [
            (6, 5, 'NORTH', 'C100', '3', '12.50'),
            (17, 16, 'SOUTH', 'C201', '6', '3.25'),
        ],
        'errors': [
            {'line': 3, 'category': 'REJECTED', 'reason': 'missing_warehouse_context'},
            {'line': 7, 'category': 'REJECTED', 'reason': 'non_space_separator', 'range': [37, 39], 'raw': '7 '},
            {'line': 8, 'category': 'REJECTED', 'reason': 'invalid_qty_integer', 'range': [32, 37], 'raw': '   2O'},
            {'line': 9, 'category': 'UNRESOLVED', 'reason': 'no_explicit_rule_matched'},
            {'line': 10, 'category': 'REJECTED', 'reason': 'invalid_record_width', 'expected_width': 47, 'actual_width': 46},
            {'line': 15, 'category': 'REJECTED', 'reason': 'missing_warehouse_context'},
        ],
    },
}

policy = {
    'version': 1,
    'purpose': 'Frozen extraction contract; declarative fixture truth, not an implementation',
    'encoding': 'utf-8',
    'character_repertoire': 'ASCII printable characters, LF, and standalone FF only',
    'line_separator': 'LF',
    'terminal_lf_creates_line': False,
    'coordinates': '1-based line; 0-based, end-exclusive character ranges; LF excluded',
    'blank_line_characters': 'ASCII space only; empty line also blank',
    'detail': {
        'detector': {'first_four_characters': 'one uppercase ASCII letter then three ASCII digits'},
        'record_width': 47,
        'fields': [
            {'name': 'item', 'range': [0, 8], 'trim': 'ASCII space', 'type': 'one uppercase ASCII letter then three ASCII digits', 'alignment': 'left'},
            {'name': 'qty', 'range': [32, 37], 'trim': 'ASCII space', 'type': 'unsigned ASCII integer', 'alignment': 'right'},
            {'name': 'price', 'range': [39, 47], 'trim': 'ASCII space', 'type': 'unsigned ASCII decimal with exactly two fractional digits', 'alignment': 'right'},
        ],
        'separator_ranges_must_be_spaces': [[8, 10], [30, 32], [37, 39]],
        'description_range_not_exported': [10, 30],
        'required_context': 'warehouse',
        'validation_order': ['record_width', 'separators', 'item', 'qty', 'price', 'required_context'],
    },
    'header': {
        'detector': {'prefix': 'WAREHOUSE: '},
        'record_width': 19,
        'field': {'name': 'warehouse', 'range': [11, 19], 'trim': 'ASCII space', 'type': 'one to eight uppercase ASCII letters', 'alignment': 'left'},
        'on_valid_header': 'replace previous context and its provenance',
        'on_invalid_header': 'clear context and REJECT the header',
    },
    'ignore': [
        {'name': 'page_header', 'starts_with': 'INVENTORY VALUATION  PAGE ', 'reset_context': True},
        {'name': 'column_header', 'equals': COL, 'reset_context': False},
        {'name': 'page_footer', 'equals': 'END OF PAGE', 'reset_context': True},
        {'name': 'form_feed_boundary', 'equals': '\f', 'reset_context': True},
    ],
    'initial_context': None,
    'blank_lines_change_context': False,
    'rejected_detail_changes_context': False,
    'unresolved_line_changes_context': False,
    'classification_order': ['explicit_ignore_in_declared_order', 'ASCII_space_only_blank', 'header_candidate', 'detail_candidate', 'UNRESOLVED'],
    'candidate_validation_failure': 'REJECTED',
    'accepted_detail_classification': 'DETAIL',
    'csv': {'columns': ['warehouse', 'item', 'qty', 'price'], 'delimiter': ',', 'quoting': 'minimal', 'line_ending': 'LF', 'encoding': 'utf-8', 'terminal_lf': True, 'preserve_lexical_decimal': True},
    'clean_export': 'block if any UNRESOLVED or REJECTED lines exist; no clean CSV artifact',
    'exception_export': 'requires explicit request; accepted detail rows only, with an inseparable exception manifest',
}
dump(ROOT / 'reference-policy.json', policy)
policy_hash = sha((ROOT / 'reference-policy.json').read_bytes())

summary = []
for name, report in reports.items():
    lines = report['lines']
    assert len(lines) == len(report['categories'])
    data = ('\n'.join(lines) + '\n').encode('ascii')
    (ROOT / (name + '.txt')).write_bytes(data)
    source_hash = sha(data)
    out = io.StringIO(newline='')
    writer = csv.writer(out, lineterminator='\n')
    writer.writerow(['warehouse', 'item', 'qty', 'price'])
    provenance = []
    for ordinal, (line_no, header_line, wh, item, qty, price) in enumerate(report['rows'], 1):
        writer.writerow([wh, item, qty, price])
        vals = [
            ('warehouse', wh, header_line, 11, 19, True),
            ('item', item, line_no, 0, 8, False),
            ('qty', qty, line_no, 32, 37, False),
            ('price', price, line_no, 39, 47, False),
        ]
        fields = {}
        for field, value, origin, start, end, inherited in vals:
            raw = lines[origin-1][start:end]
            assert raw.strip(' ') == value, (name, field, raw, value)
            evidence = {'value': value, 'source_sha256': source_hash, 'line': origin, 'range': [start, end], 'raw': raw, 'inherited': inherited}
            if inherited:
                evidence.update({'header_line': origin, 'header_range': [start, end]})
            fields[field] = evidence
        provenance.append({'row': ordinal, 'detail_line': line_no, 'fields': fields})
    csv_data = out.getvalue().encode('ascii')
    (EXPECTED / (name + '.rows.csv')).write_bytes(csv_data)
    dump(EXPECTED / (name + '.provenance.json'), {'source_sha256': source_hash, 'coordinates': policy['coordinates'], 'rows': provenance})
    names = ['HEADER', 'DETAIL', 'IGNORED_BY_EXPLICIT_RULE', 'UNRESOLVED', 'REJECTED']
    counts = {n: sum(category == n for category, _, _ in report['categories']) for n in names}
    blank_count = sum(category == 'WHITESPACE_ONLY' for category, _, _ in report['categories'])
    line_records = []
    before = None
    for number, (raw, (category, reason, after)) in enumerate(zip(lines, report['categories']), 1):
        line_records.append({'line': number, 'raw': raw, 'category': category, 'reason': reason, 'context_before': before, 'context_after': after})
        before = after
    accounting = {'source_sha256': source_hash, 'physical_line_count': len(lines), 'nonempty_line_count': len(lines)-blank_count, 'whitespace_only_line_count': blank_count, 'counts': counts, 'lines': line_records}
    dump(EXPECTED / (name + '.accounting.json'), accounting)
    blocked = bool(counts['UNRESOLVED'] or counts['REJECTED'])
    expected_export = {
        'source_sha256': source_hash, 'reference_policy_sha256': policy_hash,
        'accepted_row_count': len(report['rows']), 'clean_export_allowed': not blocked,
        'normal_csv_artifact_created': not blocked, 'unresolved_count': counts['UNRESOLVED'],
        'rejected_count': counts['REJECTED'], 'errors': report['errors'],
    }
    dump(EXPECTED / (name + '.export.json'), expected_export)
    summary.append({'report': name, 'input_sha256': source_hash, 'input_bytes': len(data), 'accepted_csv_sha256': sha(csv_data), 'row_count': len(report['rows']), 'counts': counts, 'whitespace_only_line_count': blank_count, 'clean_export_allowed': not blocked})

c = summary[2]
dump(EXPECTED / 'C_dangerous.exception.manifest.json', {
    'exception_status': 'EXPLICIT_EXCEPTION',
    'source_file': 'C_dangerous.txt', 'source_sha256': c['input_sha256'],
    'rule_sha256': policy_hash,
    'rule_hash_basis': 'Exact bytes of reference-policy.json for this frozen reference. A tool must instead record the exact bytes of its actual saved rule.',
    'unresolved_count': 1, 'rejected_count': 5,
    'accepted_row_count': 2, 'csv_file': 'C_dangerous.exception.csv',
    'csv_sha256': c['accepted_csv_sha256'],
    'omitted_line_numbers': [3, 7, 8, 9, 10, 15],
    'normal_clean_export_blocked': True,
})
dump(ROOT / 'FREEZE.json', {
    'frozen_at_utc': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
    'phase': 'Competitor verification, before implementation or repository creation',
    'ground_truth_method': 'Manual enumeration of accepted values, source line numbers, header line numbers, classifications, and exceptions. Generator only formats known records and attaches exact source slices; no extraction engine runs.',
    'reference_policy_sha256': policy_hash,
    'reports': summary,
    'do_not_modify_after_freeze': True,
})
print(json.dumps(summary, indent=2))
