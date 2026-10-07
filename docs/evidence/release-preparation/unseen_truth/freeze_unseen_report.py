#!/usr/bin/env python3
"""One-time independent synthetic oracle authoring. Never imports SpoolLens.

The authored business rows and physical-line classifications below are the
truth source. Source substrings are copied from the independently authored
report at declared private ranges. No parser supplies expected answers.
"""
from pathlib import Path
from datetime import datetime, timezone
import csv
import hashlib
import io
import json

ROOT = Path(__file__).resolve().parent
INPUT = ROOT.parent / 'unseen_input'
NAME = 'workshop-replenishment-06a.txt'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')

def detail(item, description, qty, price):
    assert len(item) <= 7 and len(description) <= 25 and len(qty) <= 6 and len(price) <= 10
    return f'   {item:<7}  {description:<25}  {qty:>6}  {price:>10}'

def store(value):
    return 'DISPATCH STORE : ' + f'{value:<7}'

column = detail('ITEM', 'DESCRIPTION', 'QTY', 'PRICE')
shifted = detail('M499', 'RIVET REFILL', '381257', '0.03')
# Malformed business row: a right shift consumes one structural separator.
# A naive slice would silently misstate 381257 as 38125.
shifted = shifted[:39] + ' ' + shifted[39:45] + shifted[46:]
assert len(shifted) == 57 and shifted[45:47] == '7 '
annotation = 'NOTE FOR PLANNER: quoted lead times are informational only.'
footer = '=== DISPATCH PAGE COMPLETE ==='
page_prefix = 'WORKSHOP REPLENISHMENT / RUN 06A / PAGE '
lines = [
    page_prefix + '01',
    store('CENTRAL'),
    '',
    column,
    detail('M410', 'MOTOR MOUNT', '7', '48.20'),
    detail('M411', 'CABLE CLAMP', '104205', '0.07'),
    detail('M412', 'LINEAR ACTUATOR', '12', '1599.50'),
    column,
    detail('M413', 'WASHER PACK', '90', '2.00'),
    annotation,
    detail('M414', 'SERVICE GASKET', '0', '0.00'),
    shifted,
    detail('M415', 'TORQUE ADAPTOR', '3', '189.95'),
    footer,
    '',
    page_prefix + '02',
    store('MOBILE'),
    column,
    detail('R520', 'BRAKE HOSE', '21', '9.10'),
    detail('R521', 'SEAL KIT', '5', '62.35'),
    '     ',
    detail('R522', 'LOCK WASHER', '1800', '0.80'),
    store('HANGAR'),
    detail('R523', 'ENGINE MODULE', '1', '1234567.89'),
    detail('R524', 'FLUID FILTER', '40', '4.75'),
    column,
    detail('R525', 'TEST GAUGE', '8', '289.00'),
    footer,
    '',
    page_prefix + '03',
    store('HANGAR'),
    column,
    detail('S630', 'CABLE ASSEMBLY', '16', '22.10'),
    detail('S631', 'RUBBER BOOT', '48', '1.05'),
    detail('S632', 'SERVO CONTROLLER', '2', '17999.00'),
    detail('S633', 'DRAIN VALVE', '120', '8.40'),
    detail('S634', 'THERMAL SENSOR', '9', '39.99'),
    detail('S635', 'RETAINING PIN', '6', '0.50'),
    footer,
]
assert len(lines) == 39
source = ('\n'.join(lines) + '\n').encode('ascii')
source_path = INPUT / NAME
source_path.write_bytes(source)
source_hash = sha(source)

# Enumerated, independently authored output records; never inferred by parsing.
records = [
    (5,2,'CENTRAL','M410','7','48.20'),
    (6,2,'CENTRAL','M411','104205','0.07'),
    (7,2,'CENTRAL','M412','12','1599.50'),
    (9,2,'CENTRAL','M413','90','2.00'),
    (11,2,'CENTRAL','M414','0','0.00'),
    (13,2,'CENTRAL','M415','3','189.95'),
    (19,17,'MOBILE','R520','21','9.10'),
    (20,17,'MOBILE','R521','5','62.35'),
    (22,17,'MOBILE','R522','1800','0.80'),
    (24,23,'HANGAR','R523','1','1234567.89'),
    (25,23,'HANGAR','R524','40','4.75'),
    (27,23,'HANGAR','R525','8','289.00'),
    (33,31,'HANGAR','S630','16','22.10'),
    (34,31,'HANGAR','S631','48','1.05'),
    (35,31,'HANGAR','S632','2','17999.00'),
    (36,31,'HANGAR','S633','120','8.40'),
    (37,31,'HANGAR','S634','9','39.99'),
    (38,31,'HANGAR','S635','6','0.50'),
]
columns = ['warehouse','item','qty','price']
out = io.StringIO(newline='')
writer = csv.writer(out, lineterminator='\n')
writer.writerow(columns)
for _, _, *values in records:
    writer.writerow(values)
expected_csv = out.getvalue().encode('utf-8')
(ROOT / 'expected.rows.exception.csv').write_bytes(expected_csv)

ranges = {'warehouse':[17,24], 'item':[3,10], 'qty':[39,45], 'price':[47,57]}
provenance_rows = []
for row_number, (detail_line, header_line, *values) in enumerate(records, 1):
    fields = {}
    for name, value in zip(columns, values):
        origin = header_line if name == 'warehouse' else detail_line
        start,end = ranges[name]
        raw = lines[origin-1][start:end]
        assert raw.strip(' ') == value
        ev = {'value':value,'source_sha256':source_hash,'line':origin,'range':[start,end],
              'raw':raw,'inherited':name=='warehouse'}
        if name == 'warehouse':
            ev.update(header_line=header_line,header_range=[start,end])
        fields[name] = ev
    provenance_rows.append({'row':row_number,'detail_line':detail_line,'fields':fields})
provenance = {'source_sha256':source_hash,
    'coordinates':'1-based line; 0-based, end-exclusive character ranges; LF excluded',
    'rows':provenance_rows}
dump(ROOT / 'expected.canonical.provenance.json', provenance)

# For each physical line: category, reason, context AFTER processing.
classes = [
    ('IGNORED_BY_EXPLICIT_RULE','page_header',None),
    ('HEADER','warehouse_header','CENTRAL'),
    ('WHITESPACE_ONLY','blank_line','CENTRAL'),
    ('IGNORED_BY_EXPLICIT_RULE','column_header','CENTRAL'),
    ('DETAIL','accepted_detail','CENTRAL'),
    ('DETAIL','accepted_detail','CENTRAL'),
    ('DETAIL','accepted_detail','CENTRAL'),
    ('IGNORED_BY_EXPLICIT_RULE','column_header','CENTRAL'),
    ('DETAIL','accepted_detail','CENTRAL'),
    ('UNRESOLVED','no_explicit_rule_matched','CENTRAL'),
    ('DETAIL','accepted_detail','CENTRAL'),
    ('REJECTED','non_space_separator','CENTRAL'),
    ('DETAIL','accepted_detail','CENTRAL'),
    ('IGNORED_BY_EXPLICIT_RULE','page_footer',None),
    ('WHITESPACE_ONLY','blank_line',None),
    ('IGNORED_BY_EXPLICIT_RULE','page_header',None),
    ('HEADER','warehouse_header','MOBILE'),
    ('IGNORED_BY_EXPLICIT_RULE','column_header','MOBILE'),
    ('DETAIL','accepted_detail','MOBILE'),
    ('DETAIL','accepted_detail','MOBILE'),
    ('WHITESPACE_ONLY','blank_line','MOBILE'),
    ('DETAIL','accepted_detail','MOBILE'),
    ('HEADER','warehouse_header','HANGAR'),
    ('DETAIL','accepted_detail','HANGAR'),
    ('DETAIL','accepted_detail','HANGAR'),
    ('IGNORED_BY_EXPLICIT_RULE','column_header','HANGAR'),
    ('DETAIL','accepted_detail','HANGAR'),
    ('IGNORED_BY_EXPLICIT_RULE','page_footer',None),
    ('WHITESPACE_ONLY','blank_line',None),
    ('IGNORED_BY_EXPLICIT_RULE','page_header',None),
    ('HEADER','warehouse_header','HANGAR'),
    ('IGNORED_BY_EXPLICIT_RULE','column_header','HANGAR'),
    ('DETAIL','accepted_detail','HANGAR'),
    ('DETAIL','accepted_detail','HANGAR'),
    ('DETAIL','accepted_detail','HANGAR'),
    ('DETAIL','accepted_detail','HANGAR'),
    ('DETAIL','accepted_detail','HANGAR'),
    ('DETAIL','accepted_detail','HANGAR'),
    ('IGNORED_BY_EXPLICIT_RULE','page_footer',None),
]
assert len(classes) == len(lines)

def accounting(annotation_handled):
    counts = dict.fromkeys(['HEADER','DETAIL','IGNORED_BY_EXPLICIT_RULE','UNRESOLVED','REJECTED'],0)
    ledger = []
    previous = None
    for number,(raw,(category,reason,after)) in enumerate(zip(lines,classes),1):
        if number == 10 and annotation_handled:
            category,reason = 'IGNORED_BY_EXPLICIT_RULE','planner_note'
        ledger.append({'line':number,'raw':raw,'category':category,'reason':reason,
                       'context_before':previous,'context_after':after})
        if category in counts: counts[category] += 1
        previous = after
    return {'source_sha256':source_hash,'physical_line_count':39,'nonempty_line_count':35,
            'whitespace_only_line_count':4,'counts':counts,'lines':ledger}

for stage, handled in [('pre_handling',False),('final',True)]:
    account = accounting(handled)
    dump(ROOT / f'expected.{stage}.accounting.json',account)
    errors = [] if handled else [{'line':10,'category':'UNRESOLVED','reason':'no_explicit_rule_matched'}]
    errors.append({'line':12,'category':'REJECTED','reason':'non_space_separator','range':[45,47],'raw':'7 '})
    dump(ROOT / f'expected.{stage}.export.json',{
        'source_sha256':source_hash, 'accepted_row_count':18, 'rule_complete':True,
        'clean_export_allowed':False, 'unresolved_count':0 if handled else 1,
        'rejected_count':1, 'rule_issues':[], 'errors':errors,
        'rule_sha256':'Depends on the exact independently authored and saved rule; verify against actual bytes.'})

policy = {
 'schema_version':1,
 'status':'FROZEN_BEFORE_FIRST_EXECUTION',
 'baseline_commit_requested':'78a50976aeea88b92269956e5ec43af6ed2cbd4a',
 'authorship':'Synthetic workshop spare-parts replenishment report. Independently authored; no imported third-party data.',
 'scope':'Exactly three built-in detail fields and one built-in inherited warehouse field. Different positions, widths, report subject, prefix, and values from frozen A/B/C.',
 'source':{'name':NAME,'sha256':source_hash,'bytes':len(source),'encoding':'ASCII-compatible UTF-8',
           'physical_lines':39,'nonempty_lines':35,'whitespace_only_lines':4,'line_ending':'LF','terminal_lf':True},
 'canonical_private_layout':{
    'detail_width':57,'leading_spaces':[0,3],'item':[3,10],'description_not_exported':[12,37],
    'qty':[39,45],'price':[47,57],'required_space_guards':[[10,12],[37,39],[45,47]],
    'header_prefix':'DISPATCH STORE : ','header_width':24,'warehouse':[17,24]},
 'field_meanings':{'warehouse':'dispatch store from latest valid header on this page',
                   'item':'catalogue part code','qty':'replenishment units','price':'unit price as an exact decimal string'},
 'canonical_ignore_intent':[
    {'name':'page_header','mode':'prefix','text':page_prefix,'reset':True},
    {'name':'column_header','mode':'exact','text':column,'reset':False},
    {'name':'page_footer','mode':'exact','text':footer,'reset':True},
    {'name':'planner_note','mode':'exact','text':annotation,'reset':False,'stage':'only after explicit review'}],
 'stages':{
    'pre_handling':'After authoring fields/context/page-and-column/footer ignores, leave planner note unresolved. Attempt normal export. It must be blocked and create no clean CSV.',
    'final':'Explicitly ignore the informational planner note. Keep the malformed business row REJECTED. Attempt normal export again: still blocked. Explicitly confirm exception export; its accepted-row CSV must equal expected.rows.exception.csv. Preserve source bytes.'},
 'final_required_counts':{'HEADER':4,'DETAIL':18,'IGNORED_BY_EXPLICIT_RULE':12,'UNRESOLVED':0,'REJECTED':1},
 'exception_requirements':{
    'export_status':'EXPLICIT_EXCEPTION','accepted_row_count':18,'unresolved_count':0,'rejected_count':1,
    'omitted_problem_lines':[12],'normal_clean_export_blocked':True,
    'csv_sha256':sha(expected_csv),'input_bytes_must_match_source':True,
    'retain_full_line_accounting_and_per_value_provenance':True,
    'rule_bytes_and_manifest_member_hashes_must_verify':True},
 'unacceptable_shortcuts':[
    'Editing, normalizing, repairing, or replacing the input report',
    'Ignoring or classifying the malformed business-detail row as non-data',
    'Exporting its silently truncated quantity',
    'Presenting exception CSV as a clean extraction',
    'Writing a CSV directly from preview/API bytes to bypass normal export',
    'Giving hidden coordinates, private expected files, a ready-made rule, implementation code, or author hints to the tester'],
 'oracle_comparison_policy':{
    'csv':'Exact byte equality, including column order, row order, lexical values and LF endings.',
    'line_accounting':'Exact physical lines/raw bytes/categories/context transitions at both stages. Custom explicit-ignore labels may differ, provided the literal source match and reset intent are equivalent. Diagnostic reason wording may differ if it identifies the same defect without concealing its location.',
    'canonical_provenance':'expected.canonical.provenance.json freezes one canonical full-field representation before testing.',
    'independent_selection_equivalence':'Different field-padding spans are legitimate only if they select the same exact business value wholly within that field\'s canonical span, include all non-space characters in that field on every accepted row, and preserve all 18 expected accepted rows. Warehouse start must be its canonical start; item start must be its canonical start. Numeric end must be its canonical end. Each actual raw substring must equal original source[line][start:end], trim to the expected value, carry original source SHA-256, and have correct detail/header lineage and inherited markers. Record every coordinate difference; do not silently call it canonical equality.',
    'safety_for_equivalent_spans':'Malformed line must remain REJECTED, never unresolved or ignored in final output. The detector/guards must remain complete and clean export blocked.',
    'rule_hash':'Depends on exact saved bytes; verify directly against them. It is not a predetermined output.'},
 'independence':'Tester receives only raw report, business-intent handout, and public-facing README/instructions. This directory, generator, policy and answers are withheld. Auditor gets the frozen hash manifest before test results.',
 'acceptance_is_immutable':'Do not alter report, expected answers or these criteria after any SpoolLens execution. A mistake must be disclosed; a new dataset requires a new independent test, never a patched oracle.'
}
dump(ROOT / 'PRIVATE_ACCEPTANCE_POLICY.json',policy)

handout = '''# Workshop replenishment extraction task\n\nCreate a reusable extraction rule for this synthetic dispatch-store replenishment report using SpoolLens and its public-facing instructions. Start with an empty rule.\n\nThe requested CSV columns are warehouse, item, qty, price. The DISPATCH STORE heading is the inherited warehouse context. ITEM is the catalogue part code, QTY is replenishment units, and PRICE is unit price. Descriptions help you identify the rows but are not part of the requested CSV. Preserve the values as printed, including decimal places and zero quantities. A page begins a new context; do not carry a store across a page boundary without its heading. A later store heading on the same page replaces the earlier store.\n\nPage and column headings and page-complete footers are non-data. Review any other unmatched text before deciding how to handle it. An informational note may be explicitly ignored after review. A malformed business row must not be ignored or silently repaired to obtain a clean result. Keep the input unchanged and use the documented, clearly labelled exception-export route if needed, retaining its evidence with the CSV.\n\nUse the UI to define the fields and inherited context, inspect unknown or rejected lines, preview values, and inspect at least one value's exact source provenance. Save your rule, close and reopen it, and replay it. Attempt normal CSV export while unmatched text remains, inspect the explanation, then explicitly handle the issues and generate the permitted output.\n\nRecord elapsed time, mistakes, documentation lookups, confusing controls or wording, whether regex or code/template syntax was necessary, and whether you needed information beyond this report, this task, and the public instructions. Do not inspect the implementation, tests, previous rules, private expected answers, or other authoring evidence.\n'''
(INPUT / 'TASK.txt').write_text(handout,encoding='utf-8')

# Content hashes establish pre-execution expectations. This generator itself is
# included; the manifest cannot contain its own hash recursively.
paths = sorted([source_path,INPUT/'TASK.txt'] + [p for p in ROOT.iterdir() if p.is_file() and p.name != 'FREEZE.json'])
manifest = {'frozen_at_utc':datetime.now(timezone.utc).isoformat(),
            'before_any_spoollens_execution':True,'report_name':NAME,
            'source_sha256':source_hash,'expected_csv_sha256':sha(expected_csv),
            'files':{str(p.relative_to(ROOT.parent)):{'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in paths}}
dump(ROOT / 'FREEZE.json',manifest)
print(json.dumps({'source':str(source_path),'source_sha256':source_hash,'source_bytes':len(source),
                  'physical_lines':39,'expected_rows':len(records),'expected_csv_sha256':sha(expected_csv),
                  'manifest':str(ROOT/'FREEZE.json'),'manifest_sha256':sha((ROOT/'FREEZE.json').read_bytes()),
                  'frozen_at_utc':manifest['frozen_at_utc']},indent=2))
