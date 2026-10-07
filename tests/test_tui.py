"""UI state regressions; separate from actual PTY and independent usability tests."""
import curses
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from spoollens.tui import App
from spoollens.engine import load_rule

ROOT = Path(__file__).resolve().parents[1]


class Screen:
    def __init__(self, keys=()):
        self.keys = iter(keys)
    def getmaxyx(self): return (38, 120)
    def keypad(self, value): pass
    def erase(self): pass
    def refresh(self): pass
    def move(self, *args): pass
    def clrtoeol(self): pass
    def addnstr(self, *args): pass
    def get_wch(self): return next(self.keys)


class TuiTests(unittest.TestCase):
    def app(self, keys=(), rule=None):
        with patch('spoollens.tui.curses.curs_set'):
            return App(Screen(keys), ROOT / 'tests/fixtures/A_clean.txt', rule)

    def test_prompt_default_replace_edit_and_cancel(self):
        for keys, expected in ((['1','\n'], '1'), (['\n'], '123'),
                               (['\x15','4','\n'], '4'),
                               (['\x7f','4','\n'], '124'), (['\x1b'], None)):
            app = self.app(keys)
            self.assertEqual(app.prompt('value', '123'), expected)

    def test_visual_fields_generate_guards_and_undo(self):
        app = self.app()
        app.line = 4
        for index, (start, end) in enumerate(((0,8),(32,37),(39,47))):
            app.anchor, app.column = start, end - 1
            with patch.object(app, 'choice', return_value=index), patch.object(app, 'confirm', return_value=True):
                app.field()
        self.assertEqual(app.rule['detail']['spaces'], [[8,10],[30,32],[37,39]])
        self.assertEqual(len(app.rule['detail']['fields']), 3)
        self.assertFalse(app.result.clean_export_allowed)
        app.handle('u')
        self.assertEqual(len(app.rule['detail']['fields']), 2)
        self.assertFalse(app.result.clean_export_allowed)

    def test_keyboard_selection_uses_exact_characters(self):
        app = self.app()
        app.line = 4
        app.handle(' ')
        for _ in range(7): app.handle(curses.KEY_RIGHT)
        self.assertEqual(app.selection(), (0,8))
        self.assertEqual(app.raw_line()[0:8], 'A100    ')
        app.handle(curses.KEY_DOWN)
        self.assertIsNone(app.selection())

    def test_source_alias_cannot_be_saved_over(self):
        app = self.app()
        with tempfile.TemporaryDirectory() as temp:
            original = Path(temp) / 'source.txt'
            original.write_bytes(app.source)
            app.open_source(original)
            alias = Path(temp) / 'source.json'
            os.link(app.path, alias)
            with self.assertRaisesRegex(ValueError, 'read-only'):
                app.safe_target(alias)

    def test_zero_ignore_index_does_not_delete_last_rule(self):
        app = self.app(rule=ROOT / 'examples/inventory.rule.json')
        before = list(app.rule['ignore'])
        with patch.object(app, 'choice', return_value=0), patch.object(app, 'prompt', return_value='0'):
            with self.assertRaises(ValueError): app.delete()
        self.assertEqual(app.rule['ignore'], before)

    def test_problem_navigation_highlights_engine_error_span(self):
        app = self.app(rule=ROOT / 'examples/inventory.rule.json')
        app.open_source(ROOT / 'tests/fixtures/C_dangerous.txt')
        app.next_problem()
        self.assertEqual(app.line, 2)
        app.next_problem()
        self.assertEqual(app.line, 6)
        self.assertEqual(app.selection(), (37,39))
        self.assertEqual(app.raw_line()[37:39], '7 ')

    def test_cancel_open_preserves_current_source(self):
        app = self.app()
        before = app.path, app.source
        with patch.object(app, 'prompt', return_value=None): app.handle('o')
        self.assertEqual((app.path,app.source), before)

    def test_blocked_export_does_not_even_prompt_for_destination(self):
        app = self.app(rule=ROOT / 'examples/inventory.rule.json')
        app.open_source(ROOT / 'tests/fixtures/C_dangerous.txt')
        with patch.object(app, 'modal') as modal, patch.object(app, 'prompt') as prompt:
            app.export()
            modal.assert_called_once()
            prompt.assert_not_called()


class RecordingScreen(Screen):
    def __init__(self, keys=(), height=10, width=40):
        super().__init__(keys)
        self.size = (height, width)
        self.frames = []
        self.lines = {}
    def getmaxyx(self): return self.size
    def erase(self): self.lines = {}
    def addnstr(self, y, x, text, count, attr=0): self.lines[y] = text[:count]
    def refresh(self): self.frames.append(dict(self.lines))


class LongTextTests(unittest.TestCase):
    def app(self, screen):
        with patch('spoollens.tui.curses.curs_set'):
            return App(screen, ROOT / 'tests/fixtures/C_dangerous.txt', ROOT / 'examples/inventory.rule.json')

    def test_modal_exposes_both_ends_of_long_hash_path_and_source(self):
        screen = RecordingScreen([curses.KEY_END, curses.KEY_HOME, '\n'])
        app = self.app(screen)
        text = 'source/' + 'x' * 120 + '/EXACT_END.txt'
        app.modal('Evidence', [text])
        self.assertTrue(screen.frames[0][2].startswith(' source/'))
        self.assertTrue(screen.frames[0][2].endswith('>'))
        self.assertIn('EXACT_END.txt', screen.frames[1][2])
        self.assertTrue(screen.frames[1][2].startswith('<'))
        self.assertEqual(screen.frames[0][2], screen.frames[2][2])

    def test_modal_arrow_and_page_scroll_reaches_all_text(self):
        screen = RecordingScreen([curses.KEY_RIGHT, curses.KEY_LEFT, curses.KEY_NPAGE, curses.KEY_PPAGE, '\n'])
        app = self.app(screen)
        lines = [f'row {i} ' + 'abcdefghij' * 8 for i in range(20)]
        app.modal('Evidence', lines)
        self.assertTrue(screen.frames[1][2].startswith('<'))
        self.assertEqual(screen.frames[0][2], screen.frames[2][2])
        self.assertIn('row 6 ', screen.frames[3][2])
        self.assertEqual(screen.frames[0][2], screen.frames[4][2])

    def test_blocked_export_includes_actual_problem_lines(self):
        app = self.app(RecordingScreen())
        with patch.object(app, 'modal') as modal:
            app.export()
        text = '\n'.join(modal.call_args.args[1])
        for entry in app.result.lines:
            if entry['category'] in ('UNRESOLVED', 'REJECTED'):
                self.assertIn(f"Line {entry['line']}: {entry['category']}", text)
                self.assertIn(repr(entry['raw']), text)

    def test_full_status_preserves_complete_paths_and_hashes(self):
        app = self.app(RecordingScreen())
        app.status = 'Long failure: ' + 'z' * 200
        with patch.object(app, 'modal') as modal:
            app.handle('a')
        text = '\n'.join(modal.call_args.args[1])
        self.assertIn(str(app.path), text)
        self.assertIn(str(app.rule_path), text)
        self.assertIn(app.status, text)
        self.assertIn(app.result.source_sha256, text)


if __name__ == '__main__':
    unittest.main()
