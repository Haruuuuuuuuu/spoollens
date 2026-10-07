"""Small keyboard-operated visual authoring UI. Parsing lives only in engine.py."""
from __future__ import annotations

import curses
import json
from pathlib import Path

from .engine import (
    canonical_rule_bytes, empty_rule, execute, export_result, load_rule,
)


class App:
    def __init__(self, screen, source=None, rule=None):
        self.screen = screen
        self.rule = load_rule(rule) if rule else empty_rule()
        self.rule_path = Path(rule) if rule else None
        self.path = None
        self.source = b""
        self.result = None
        self.line = 0
        self.column = 0
        self.anchor = None
        self.scroll = 0
        self.history = []
        self.dirty = False
        self.status = "Open a report with o. Press ? for help."
        self.inspection = None
        self.running = True
        curses.curs_set(0)
        screen.keypad(True)
        if source:
            self.open_source(source)

    def put(self, y, x, text, attr=0):
        height, width = self.screen.getmaxyx()
        if 0 <= y < height and 0 <= x < width:
            try:
                self.screen.addnstr(y, x, str(text), max(0, width - x - 1), attr)
            except curses.error:
                pass

    def raw_line(self):
        if not self.result or not self.result.source_lines:
            return ""
        return self.result.source_lines[self.line]

    def selection(self):
        if self.anchor is None:
            return None
        return min(self.anchor, self.column), max(self.anchor, self.column) + 1

    def refresh_result(self):
        self.result = execute(self.source, self.rule,
                              source_name=self.path.name if self.path else "source.txt",
                              source_path=self.path)
        self.inspection = None
        self.line = max(0, min(self.line, len(self.result.source_lines) - 1))
        self.column = min(self.column, max(0, len(self.raw_line()) - 1))

    def open_source(self, path):
        target = Path(path).expanduser().resolve()
        data = target.read_bytes()
        result = execute(data, self.rule, source_name=target.name, source_path=target)
        self.path, self.source, self.result = target, data, result
        self.line = self.column = self.scroll = 0
        self.anchor = None
        self.inspection = None
        self.status = f"Opened {target.name} read-only; rules unchanged"

    def draw(self):
        self.screen.erase()
        height, width = self.screen.getmaxyx()
        title = f"SpoolLens | {self.path.name if self.path else 'No report'} | {self.rule.get('encoding')} / ASCII | ? help"
        self.put(0, 0, title, curses.A_BOLD)
        self.put(1, 0, "Arrows move | Space select | f field | h warehouse | i ignore | p page break | ? help")
        self.put(2, 0, "w save | l reload | o open report | v inspect value | e clean CSV | x exception | u undo | q quit")
        if not self.result:
            self.put(5, 0, "Press o to open a TXT or PRN report")
            self.put(height - 2, 0, self.status)
            self.screen.refresh()
            return
        counts = self.result.counts
        self.put(3, 0, " | ".join(f"{name} {counts.get(name, 0)}" for name in
                 ("HEADER", "DETAIL", "IGNORED_BY_EXPLICIT_RULE", "UNRESOLVED", "REJECTED")))
        issues = list(self.result.rule_issues)
        gate = "CLEAN EXPORT READY" if self.result.clean_export_allowed else "CLEAN EXPORT BLOCKED | e explains; n finds issues"
        if issues:
            gate += " | draft: " + "; ".join(str(x) for x in issues)
        self.put(4, 0, gate, curses.A_BOLD)
        source_height = max(3, height - 16)
        if self.line < self.scroll:
            self.scroll = self.line
        if self.line >= self.scroll + source_height:
            self.scroll = self.line - source_height + 1
        label_width = 13
        visible = max(1, width - label_width - 1)
        xscroll = max(0, self.column - visible + 5)
        self.put(5, 0, "line/status  " + "".join(str(i // 10 % 10) if i % 10 == 0 else " "
                                               for i in range(xscroll, xscroll + visible)))
        self.put(6, 0, "char index   " + "".join(str(i % 10) for i in range(xscroll, xscroll + visible)))
        abbreviations = {"HEADER": "HEADER", "DETAIL": "DETAIL", "IGNORED_BY_EXPLICIT_RULE": "IGNORE",
                         "UNRESOLVED": "UNKNOWN", "REJECTED": "REJECT", "WHITESPACE_ONLY": "BLANK"}
        span = self.selection()
        for pos in range(source_height):
            idx = self.scroll + pos
            if idx >= len(self.result.lines):
                break
            item = self.result.lines[idx]
            selected = idx == self.line
            self.put(7 + pos, 0, f"{'>' if selected else ' '}{idx + 1:3} {abbreviations[item['category']]:7}",
                     curses.A_BOLD if selected else 0)
            raw = item["raw"]
            if not raw:
                self.put(7 + pos, label_width, "(empty)", curses.A_DIM)
            for column in range(xscroll, min(len(raw), xscroll + visible)):
                char = "\u240c" if raw[column] == "\f" else raw[column]
                attr = 0
                if selected and span and span[0] <= column < span[1]:
                    attr = curses.A_REVERSE
                elif selected and column == self.column:
                    attr = curses.A_REVERSE | curses.A_BOLD
                self.put(7 + pos, label_width + column - xscroll, char, attr)
        lower = 7 + source_height
        line_info = self.result.lines[self.line] if self.result.lines else None
        selected_text = f" | selected [{span[0]},{span[1]})" if span else ""
        if line_info:
            self.put(lower, 0, f"Line {self.line + 1} char {self.column}{selected_text} | {line_info['category']}: {line_info['reason']}")
        self.put(lower + 1, 0, "Candidate output (inspect any row/field with v)", curses.A_BOLD)
        self.put(lower + 2, 0, " row  warehouse    item       qty        price       detail source")
        for offset, row in enumerate(self.result.rows[:3]):
            fields = row["fields"]
            values = [fields.get(name, {}).get("value", "") for name in ("warehouse", "item", "qty", "price")]
            self.put(lower + 3 + offset, 0,
                     f" {row['row']:3}  {values[0]:12} {values[1]:10} {values[2]:10} {values[3]:11} line {row['detail_line']}")
        if len(self.result.rows) > 3:
            self.put(lower + 6, 0, f"{len(self.result.rows)} rows total; v can inspect every row")
        self.put(height - 2, 0, self.status if len(self.status) < width else self.status[:max(0, width - 17)] + "... [a: full]", curses.A_BOLD)
        if self.inspection:
            e = self.inspection
            tail = f"raw={e['raw']!r} source={e['source_sha256']}"
        else:
            tail = f"{'UNSAVED rule' if self.dirty else 'Rule unchanged'} | a full status/paths | r review rules | g go to line/character | s add space guard | Esc clear selection"
        self.put(height - 1, 0, tail)
        self.screen.refresh()

    def prompt(self, title, default=""):
        value = str(default)
        replace_default = True
        self.draw()
        while True:
            height, width = self.screen.getmaxyx()
            self.screen.move(height - 2, 0)
            self.screen.clrtoeol()
            self.put(height - 2, 0, title + " (Enter accepts, Esc cancels)", curses.A_BOLD)
            self.screen.move(height - 1, 0)
            self.screen.clrtoeol()
            self.put(height - 1, 0, "> " + value[-max(1, width - 4):])
            self.screen.refresh()
            key = self.screen.get_wch()
            if key in ("\n", "\r", curses.KEY_ENTER):
                return value
            if key == "\x1b":
                return None
            if key in (curses.KEY_BACKSPACE, "\b", "\x7f"):
                value = value[:-1]
                replace_default = False
            elif key == "\x15":
                value = ""
                replace_default = False
            elif isinstance(key, str) and key.isprintable():
                if replace_default:
                    value = ""
                    replace_default = False
                value += key

    def modal(self, title, lines):
        # Preserve exact characters rather than silently truncating evidence.
        lines = [str(line) for line in lines]
        offset = column = 0
        while True:
            self.screen.erase()
            height, width = self.screen.getmaxyx()
            self.put(0, 0, title, curses.A_BOLD)
            visible = max(1, height - 4)
            content_width = max(1, width - 3)
            max_column = max(0, max((len(line) for line in lines), default=0) - content_width)
            column = min(column, max_column)
            offset = min(offset, max(0, len(lines) - visible))
            for i, line in enumerate(lines[offset:offset + visible]):
                left = "<" if column else " "
                right = ">" if len(line) > column + content_width else " "
                self.put(2 + i, 0, left + line[column:column + content_width] + right)
            self.put(height - 2, 0,
                     f"Lines {offset + 1}-{min(len(lines), offset + visible)}/{len(lines)} | chars from {column} | < > means more text")
            self.put(height - 1, 0, "Enter/Esc close | arrows scroll | Home/End width | PgUp/PgDn lines")
            self.screen.refresh()
            key = self.screen.get_wch()
            if key in ("\n", "\r", "\x1b", curses.KEY_ENTER):
                return
            if key == curses.KEY_DOWN:
                offset = min(max(0, len(lines) - visible), offset + 1)
            elif key == curses.KEY_UP:
                offset = max(0, offset - 1)
            elif key == curses.KEY_RIGHT:
                column = min(max_column, column + max(1, content_width // 2))
            elif key == curses.KEY_LEFT:
                column = max(0, column - max(1, content_width // 2))
            elif key == curses.KEY_HOME:
                column = 0
            elif key == curses.KEY_END:
                column = max_column
            elif key == curses.KEY_NPAGE:
                offset = min(max(0, len(lines) - visible), offset + visible)
            elif key == curses.KEY_PPAGE:
                offset = max(0, offset - visible)

    def choice(self, title, options):
        while True:
            self.screen.erase()
            self.put(0, 0, title, curses.A_BOLD)
            for index, option in enumerate(options):
                self.put(index + 2, 0, f"{index + 1}. {option}")
            self.put(len(options) + 4, 0, "Choose a number. Esc cancels")
            self.screen.refresh()
            key = self.screen.get_wch()
            if key == "\x1b":
                return None
            if isinstance(key, str) and key.isdigit() and 1 <= int(key) <= len(options):
                return int(key) - 1

    def confirm(self, title):
        return self.choice(title, ["Yes", "No"]) == 0

    def mutate(self, new_rule, message):
        # Do not preserve LoadedRule's byte metadata when authoring changes.
        old_rule = json.loads(json.dumps(self.rule))
        canonical_rule_bytes(new_rule)  # structural validation before changing state
        self.history.append(old_rule)
        self.rule = new_rule
        self.dirty = True
        self.anchor = None
        self.refresh_result()
        self.status = message

    def new_rule_copy(self):
        return json.loads(json.dumps(self.rule))

    def need_selection(self):
        span = self.selection()
        if span is None:
            self.status = "Select a range first: arrows to its first character, Space, arrows to its last"
            return None
        if span[1] > len(self.raw_line()):
            self.status = "Selection must stay inside the source line"
            return None
        return span

    def field(self):
        span = self.need_selection()
        if span is None:
            return
        selection = self.raw_line()[span[0]:span[1]]
        index = self.choice(f"Make {selection!r} [{span[0]},{span[1]}) a detail field", [
            "item: one uppercase letter + three digits, left aligned",
            "qty: unsigned whole number, right aligned",
            "price: unsigned decimal, exactly two decimal places, right aligned",
        ])
        if index is None:
            return
        name, kind, alignment = [
            ("item", "item_code", "left"), ("qty", "unsigned_integer", "right"),
            ("price", "decimal_2", "right"),
        ][index]
        rule = self.new_rule_copy()
        if not rule["detail"]:
            rule["detail"] = {"width": len(self.raw_line()),
                              "detector": {"kind": "letter_digits", "start": 0, "letters": 1, "digits": 3},
                              "fields": [], "spaces": []}
        detail = rule["detail"]
        if name == "item":
            detail["detector"]["start"] = span[0]
        detail["fields"] = [f for f in detail["fields"] if f["name"] != name]
        detail["fields"].append({"name": name, "start": span[0], "end": span[1], "type": kind, "alignment": alignment})
        order = {"item": 0, "qty": 1, "price": 2}
        detail["fields"].sort(key=lambda f: order[f["name"]])
        adjacent = []
        for start, end in ((span[0] - 2, span[0]), (span[1], span[1] + 2)):
            if start >= 0 and end <= len(self.raw_line()) and self.raw_line()[start:end] == "  ":
                if not any(start < f["end"] and end > f["start"] for f in detail["fields"]):
                    adjacent.append([start, end])
        if adjacent and self.confirm(f"Require adjacent two-space separators {adjacent}? Prevents shifted columns"):
            detail["spaces"] = sorted({tuple(s) for s in detail["spaces"] + adjacent})
            detail["spaces"] = [list(s) for s in detail["spaces"]]
        # Replacing a field may move into an old guard. The user must remove it explicitly.
        self.mutate(rule, f"Defined {name} [{span[0]},{span[1]}); exact record width {detail['width']}")

    def header(self):
        span = self.need_selection()
        if span is None:
            return
        prefix = self.raw_line()[:span[0]]
        if not prefix:
            self.status = "Warehouse header needs a non-empty fixed prefix before its value"
            return
        if not self.confirm(f"Inherit warehouse from {self.raw_line()[span[0]:span[1]]!r}; prefix {prefix!r}? Invalid header clears context"):
            return
        rule = self.new_rule_copy()
        rule["header"] = {"name": "warehouse", "prefix": prefix, "width": len(self.raw_line()),
                          "field": {"name": "warehouse", "start": span[0], "end": span[1],
                                    "type": "uppercase", "alignment": "left"},
                          "invalid_clears_context": True}
        self.mutate(rule, f"Warehouse context [{span[0]},{span[1]}); valid headers replace it, invalid headers clear it")

    def ignore(self):
        raw = self.raw_line()
        if not raw or raw.strip(" ") == "":
            self.status = "Blank lines are already counted separately and preserve context"
            return
        span = self.selection()
        choices = ["Ignore exactly this whole line"]
        if span and span[0] == 0:
            choices.append("Ignore every line starting with the selected prefix")
        kind = self.choice("Choose an explicit ignore rule", choices)
        if kind is None:
            return
        mode = "exact" if kind == 0 else "prefix"
        text = raw if kind == 0 else raw[:span[1]]
        if mode == "prefix" and not text.strip(" "):
            self.status = "A prefix cannot be blank"
            return
        reset = self.choice("What happens to inherited warehouse context?", [
            "Clear it here (page heading, footer, or boundary)",
            "Keep it (repeated column heading)",
        ])
        if reset is None:
            return
        name = self.prompt("Short label for this ignore rule", f"ignore_{len(self.rule['ignore']) + 1}")
        if not name:
            return
        rule = self.new_rule_copy()
        rule["ignore"] = [i for i in rule["ignore"] if i["name"] != name]
        rule["ignore"].append({"name": name, "mode": mode, "text": text, "reset": reset == 0})
        self.mutate(rule, f"Ignored {mode} {text!r}; context {'cleared' if reset == 0 else 'preserved'}")

    def page_break(self):
        if not self.confirm("Explicitly ignore standalone form-feed (FF) lines and clear warehouse context?"):
            return
        rule = self.new_rule_copy()
        rule["ignore"] = [r for r in rule["ignore"] if r["name"] != "form_feed_boundary"]
        rule["ignore"].append({"name": "form_feed_boundary", "mode": "exact", "text": "\f", "reset": True})
        self.mutate(rule, "Standalone FF is explicitly ignored and clears warehouse context")

    def space_guard(self):
        span = self.need_selection()
        if span is None:
            return
        if not self.rule["detail"]:
            self.status = "Define a detail field first"
            return
        if self.raw_line()[span[0]:span[1]] != " " * (span[1] - span[0]):
            self.status = "A space guard must contain ASCII spaces only"
            return
        rule = self.new_rule_copy()
        rule["detail"]["spaces"] = [list(x) for x in sorted({tuple(s) for s in rule["detail"]["spaces"]} | {span})]
        self.mutate(rule, f"Required ASCII spaces in [{span[0]},{span[1]})")

    def safe_target(self, value):
        target = Path(value).expanduser().resolve()
        if self.path and (target == self.path or (target.exists() and target.samefile(self.path))):
            raise ValueError("Cannot overwrite the read-only source report")
        return target

    def save(self):
        value = self.prompt("Save open JSON rule; Ctrl-U clears text", str(self.rule_path or "inventory.rule.json"))
        if not value:
            return
        target = self.safe_target(value)
        if target.exists() and not self.confirm(f"Replace saved rule {target.name}?"):
            return
        if target.suffix.lower() != ".json":
            raise ValueError("Rules must be saved as a .json file, never as a source report")
        data = canonical_rule_bytes(self.rule)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        self.rule = load_rule(target)
        self.rule_path = target
        self.dirty = False
        self.refresh_result()
        self.status = f"Saved {target.name}; rule SHA256 {self.result.rule_sha256}"

    def load(self):
        if self.dirty and not self.confirm("Discard unsaved rule edits and reopen a saved rule?"):
            return
        value = self.prompt("Reopen rule; Ctrl-U clears text", str(self.rule_path or "inventory.rule.json"))
        if not value:
            return
        loaded = load_rule(Path(value).expanduser())
        result = execute(self.source, loaded, source_name=self.path.name if self.path else "source.txt", source_path=self.path)
        self.rule = loaded
        self.rule_path = Path(value).expanduser().resolve()
        self.result = result
        self.dirty = False
        self.history.clear()
        self.anchor = None
        self.status = f"Reopened {self.rule_path.name}; rule SHA256 {result.rule_sha256}"

    def export(self, exception=False):
        if not self.result:
            return
        if not exception and not self.result.clean_export_allowed:
            self.modal("CLEAN EXPORT BLOCKED: no CSV was created", [
                f"UNRESOLVED {self.result.counts['UNRESOLVED']}; REJECTED {self.result.counts['REJECTED']}",
                *[str(issue) for issue in self.result.rule_issues],
                "Use n to jump through problem lines and read the reason.",
                "Correct your rule only when the source justifies it.",
                "For an explicit incomplete-data bundle, use x. It is never a clean CSV.",
                "",
                *[text for entry in self.result.lines
                  if entry["category"] in ("UNRESOLVED", "REJECTED")
                  for text in (f"Line {entry['line']}: {entry['category']} - {entry['reason']}",
                               f"  Exact source text: {entry['raw']!r}")],
            ])
            self.status = "Normal CSV blocked; source problems remain visible"
            return
        if exception and not self.confirm(
                f"Export EXPLICIT_EXCEPTION with {self.result.counts['UNRESOLVED']} unresolved and {self.result.counts['REJECTED']} rejected lines?"):
            return
        suffix = ".exception.zip" if exception else ".csv"
        stem = self.path.stem if self.path else "report"
        value = self.prompt("New export path (existing files are never overwritten)", str(Path("output") / (stem + suffix)))
        if not value:
            return
        target = self.safe_target(value)
        target.parent.mkdir(parents=True, exist_ok=True)
        result = export_result(self.result, target, exception=exception)
        self.modal("EXPLICIT EXCEPTION bundle saved" if exception else "Clean CSV saved with audit evidence", [
            str(target), f"Input SHA256 {self.result.source_sha256}",
            f"Rule SHA256 {self.result.rule_sha256}",
            json.dumps(result, ensure_ascii=True),
        ])
        self.status = f"Saved {'EXPLICIT_EXCEPTION' if exception else 'clean'} output: {target.name}"

    def inspect(self):
        if not self.result or not self.result.rows:
            self.status = "No accepted candidate values to inspect yet"
            return
        value = self.prompt(f"Output row number (1..{len(self.result.rows)})", "1")
        if value is None:
            return
        row = self.result.rows[int(value) - 1] if 1 <= int(value) <= len(self.result.rows) else None
        if row is None:
            raise ValueError("No such output row")
        name_index = self.choice("Inspect output field and jump to its exact source", [
            f"{name}: {row['fields'].get(name, {}).get('value', '')}" for name in self.result.columns
        ])
        if name_index is None:
            return
        name = self.result.columns[name_index]
        evidence = row["fields"][name]
        self.line = evidence["line"] - 1
        self.anchor = evidence["range"][0]
        self.column = evidence["range"][1] - 1
        self.inspection = evidence
        inherited = f"inherited from header line {evidence['header_line']} " if evidence["inherited"] else ""
        self.status = f"row {row['row']} {name}={evidence['value']!r}: {inherited}line {evidence['line']} range {evidence['range']}"
        self.modal("Exact source evidence; Enter returns to highlighted source", [
            self.status, f"Source SHA256: {evidence['source_sha256']}",
            f"Exact raw substring: {evidence['raw']!r}",
            f"Detail line: {row['detail_line']}",
            "Coordinates: line is 1-based; character range is 0-based, end-exclusive.",
        ])

    def next_problem(self):
        if not self.result:
            return
        problems = [i for i, line in enumerate(self.result.lines) if line["category"] in ("UNRESOLVED", "REJECTED")]
        if not problems:
            self.status = "No unresolved or rejected source lines"
            return
        self.line = next((i for i in problems if i > self.line), problems[0])
        self.column = 0
        self.anchor = None
        error = next((e for e in self.result.errors if e["line"] == self.line + 1), {})
        if "range" in error:
            self.anchor = error["range"][0]
            self.column = error["range"][1] - 1
        self.status = self.result.lines[self.line]["reason"]

    def inspect_line(self):
        if not self.result or not self.result.lines:
            return
        entry = self.result.lines[self.line]
        errors = [e for e in self.result.errors if e["line"] == self.line + 1]
        self.modal("Source line audit", [
            f"Physical line {entry['line']}: {entry['category']}",
            f"Reason: {entry['reason']}",
            f"Exact source text: {entry['raw']!r}",
            f"Warehouse before: {entry['context_before']!r}; after: {entry['context_after']!r}",
            *[f"Validation: {json.dumps(error, ensure_ascii=True)}" for error in errors],
            f"Source SHA256: {self.result.source_sha256}",
        ])

    def full_status(self):
        lines = [self.status, f"Source path: {self.path or '(none)'}",
                 f"Rule path: {self.rule_path or '(unsaved)'}"]
        if self.result:
            lines += [f"Source SHA256: {self.result.source_sha256}",
                      f"Rule SHA256: {self.result.rule_sha256}",
                      f"Clean export allowed: {self.result.clean_export_allowed}",
                      *[f"Rule incomplete: {issue}" for issue in self.result.rule_issues]]
        self.modal("Full status and paths", lines)

    def review(self):
        lines = [f"Encoding: {self.rule['encoding']}; character policy: ASCII only",
                 "Source coordinates: zero-based, end-exclusive ranges", ""]
        if self.rule["header"]:
            h = self.rule["header"]
            f = h["field"]
            lines += [f"WAREHOUSE prefix {h['prefix']!r}, width {h['width']}, [{f['start']},{f['end']})",
                      "Valid header replaces context; invalid header clears it"]
        else:
            lines += ["WAREHOUSE: not defined"]
        if self.rule["detail"]:
            d = self.rule["detail"]
            lines += [f"DETAIL width {d['width']}; candidate: letter + 3 digits at char {d['detector']['start']}"]
            lines += [f"  {f['name']}: [{f['start']},{f['end']}) {f['type']} {f['alignment']}" for f in d["fields"]]
            lines += [f"  Required-space guards: {d['spaces']}"]
        else:
            lines += ["DETAIL: not defined"]
        lines += ["", "EXPLICIT IGNORE RULES (in order)"]
        lines += [f"  {i + 1}. {r['name']}: {r['mode']} {r['text']!r}; reset={r['reset']}" for i, r in enumerate(self.rule["ignore"])]
        lines += ["", "u undoes the last authoring change. Re-marking a named field replaces it.",
                  "d opens a delete menu for an ignore or space guard; c changes encoding.",
                  f"Rule SHA256: {self.result.rule_sha256 if self.result else 'not loaded'}"]
        self.modal("Review declarative rule", lines)

    def delete(self):
        kind = self.choice("Remove a rule component", ["An explicit ignore rule", "A required-space guard", "A detail field", "Warehouse header"])
        if kind is None:
            return
        rule = self.new_rule_copy()
        if kind == 0:
            if not rule["ignore"]:
                return
            value = self.prompt("Ignore rule number to remove (see r)", "1")
            if value is None:
                return
            if not 1 <= int(value) <= len(rule["ignore"]):
                raise ValueError("Ignore number is outside the rule list")
            del rule["ignore"][int(value) - 1]
        elif kind == 1:
            if not rule["detail"] or not rule["detail"]["spaces"]:
                return
            options = [str(s) for s in rule["detail"]["spaces"]]
            index = self.choice("Choose space guard to remove", options)
            if index is None:
                return
            del rule["detail"]["spaces"][index]
        elif kind == 2:
            if not rule["detail"] or not rule["detail"]["fields"]:
                return
            index = self.choice("Choose field to remove", [f["name"] for f in rule["detail"]["fields"]])
            if index is None:
                return
            del rule["detail"]["fields"][index]
        else:
            rule["header"] = None
        self.mutate(rule, "Removed rule component; preview updated")

    def encoding(self):
        option = self.choice("Explicit input encoding (probe supports ASCII characters only)", [
            "UTF-8, strict; no BOM, CR, tabs, or non-ASCII characters",
            "ASCII, strict; no CR or tabs",
        ])
        if option is None:
            return
        rule = self.new_rule_copy()
        rule["encoding"] = "utf-8" if option == 0 else "ascii"
        self.mutate(rule, "Explicit input encoding updated")

    def help(self):
        self.modal("SpoolLens keyboard guide", [
            "1. o opens a report read-only. UTF-8 is explicit default; c chooses ASCII.",
            "2. Arrows move the cursor. Home/End jump to the first/last character.",
            "   g goes to a line and zero-based character index.",
            "3. Space anchors selection. Move LEFT/RIGHT to its last included character.",
            "   The status shows [start,end), including selected padding spaces.",
            "4. f marks item/qty/price. Choose the slot from its numbered menu.",
            "   First field sets exact detail width. Item identifies candidate lines.",
            "   Approve adjacent two-space guards to reject shifted columns.",
            "5. Select the full padded warehouse value; h creates inherited context.",
            "6. i marks whole-line ignores. Select a prefix starting at char 0 first",
            "   to ignore changing page headings by their stable prefix.",
            "   Choose Clear at page headings/footers, Keep at column headings.",
            "7. p explicitly handles standalone FF page breaks and clears context.",
            "8. n cycles unknown/rejected lines and highlights a failing range.",
            "   Enter shows the current line audit, context, and validation details.",
            "   Audit/evidence windows: arrows scroll both axes, Home/End go across.",
            "   < and > mark hidden text. a shows complete status and file paths.",
            "9. v queries an output row/field, shows evidence, jumps to source.",
            "10. w saves rules; l reopens them; o replays them on another report.",
            "11. e exports clean CSV only if the rule is complete and all lines safe.",
            "    x explicitly exports an exception bundle with hashes and counts.",
            "r reviews rules; s adds a selected space guard; d removes a component.",
            "u undoes authoring; Esc clears selection. q quits, checking unsaved edits.",
            "Prompt shortcuts: Ctrl-U clears text; Enter accepts; Esc cancels.",
            "Reports are never edited. This probe has no code or template editor.",
        ])

    def handle(self, key):
        if key == "?":
            self.help()
        elif key == "q":
            if not self.dirty or self.confirm("Quit and discard unsaved rule edits?"):
                self.running = False
        elif key == "o":
            value = self.prompt("Report path; Ctrl-U clears text", str(self.path or "tests/fixtures/A_clean.txt"))
            if value:
                self.open_source(value)
        elif key == "l":
            self.load()
        elif key == "c":
            self.encoding()
        elif key == "w":
            self.save()
        elif not self.result:
            self.status = "Open a source report first (o)"
        elif key in (curses.KEY_UP, curses.KEY_DOWN):
            self.line = max(0, min(len(self.result.source_lines) - 1, self.line + (1 if key == curses.KEY_DOWN else -1)))
            self.column = min(self.column, max(0, len(self.raw_line()) - 1))
            self.anchor = None
            self.inspection = None
        elif key in (curses.KEY_LEFT, curses.KEY_RIGHT):
            self.column = max(0, min(max(0, len(self.raw_line()) - 1), self.column + (1 if key == curses.KEY_RIGHT else -1)))
        elif key in (curses.KEY_HOME, "\x01"):
            self.column = 0
        elif key in (curses.KEY_END, "\x05"):
            self.column = max(0, len(self.raw_line()) - 1)
        elif key == curses.KEY_NPAGE:
            self.line = min(len(self.result.source_lines) - 1, self.line + 10)
            self.anchor = None
        elif key == curses.KEY_PPAGE:
            self.line = max(0, self.line - 10)
            self.anchor = None
        elif key == " ":
            self.anchor = self.column
            self.inspection = None
            self.status = "Selection started; move to the last included character, then f/h/i/s"
        elif key == "\x1b":
            self.anchor = None
            self.inspection = None
        elif key == "g":
            line = self.prompt("Go to source line (1-based)", str(self.line + 1))
            if line is not None:
                column = self.prompt("Go to character (0-based)", str(self.column))
                if column is not None:
                    ln, col = int(line) - 1, int(column)
                    if not 0 <= ln < len(self.result.source_lines):
                        raise ValueError("Line is outside this report")
                    if not 0 <= col <= max(0, len(self.result.source_lines[ln]) - 1):
                        raise ValueError("Character is outside this line")
                    if ln != self.line:
                        self.anchor = None
                    self.line, self.column = ln, col
        elif key == "f":
            self.field()
        elif key == "h":
            self.header()
        elif key == "i":
            self.ignore()
        elif key == "p":
            self.page_break()
        elif key == "s":
            self.space_guard()
        elif key == "r":
            self.review()
        elif key == "a":
            self.full_status()
        elif key == "d":
            self.delete()
        elif key == "e":
            self.export(False)
        elif key == "x":
            self.export(True)
        elif key == "v":
            self.inspect()
        elif key == "n":
            self.next_problem()
        elif key in ("\n", "\r", curses.KEY_ENTER):
            self.inspect_line()
        elif key == "u":
            if self.history:
                self.rule = self.history.pop()
                self.dirty = True
                self.refresh_result()
                self.status = "Undid last authoring change"
            else:
                self.status = "Nothing to undo since opening this rule"

    def run(self):
        while self.running:
            self.draw()
            try:
                self.handle(self.screen.get_wch())
            except (ValueError, OSError, IndexError, KeyError) as error:
                self.modal("Action not completed", [str(error), "No source report was changed."])
                self.status = str(error)


def launch(source=None, rule=None):
    """Enter curses only when requested; CLI replay never requires a terminal."""
    return curses.wrapper(lambda screen: App(screen, source, rule).run())
