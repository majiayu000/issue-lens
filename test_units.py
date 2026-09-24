"""离线单元测试:纯函数、内存库检索、提炼接口契约。CI 与本地统一入口:
    python3 -m unittest test_units -v
"""
import os
import sqlite3
import unittest

from config import FORMS
from extract import extract_issue
from s03_report import excerpt, md_escape
from s04_search import search

SEED = [
    (1, "vscode", "desktop", "Crash on startup with GPU disabled", "crash startup gpu linux", 233),
    (2, "vscode", "desktop", "Window flashes when opening menu", "menu window flash render", 100),
    (3, "yt-dlp", "cli", "UnicodeDecodeError on UTF-8 filenames", "utf-8 encoding filename crash", 380),
]


def memory_db() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    with open("schema.sql", encoding="utf-8") as f:
        db.executescript(f.read())
    for iid, repo, form, title, body, reactions in SEED:
        db.execute(
            "INSERT INTO issues (id, repo_full_name, number, form, title, body, reactions) "
            "VALUES (?,?,?,?,?,?,?)",
            (iid, repo, iid, form, title, body, reactions))
        db.execute("INSERT INTO issues_fts (title, body, issue_id) VALUES (?,?,?)",
                   (title, body, iid))
    db.commit()
    return db


class FormatTests(unittest.TestCase):
    def test_excerpt_collapses_whitespace_and_truncates(self):
        self.assertEqual(excerpt("a\n\n  b\tc", 10), "a b c")
        long = excerpt("x" * 300, 220)
        self.assertEqual(len(long), 221)
        self.assertTrue(long.endswith("…"))

    def test_md_escape_pipes_and_newlines(self):
        self.assertEqual(md_escape("a|b\nc"), r"a\|b c")


class SearchTests(unittest.TestCase):
    def test_top_mode_orders_by_reactions(self):
        rows = search(memory_db(), ["desktop"], [], True, "reactions", 10, 0)
        self.assertEqual([r[0] for r in rows], [233, 100])

    def test_fts_matches_and_filters_form(self):
        rows = search(memory_db(), ["cli"], ["crash"], False, "relevance", 10, 0)
        self.assertEqual(len(rows), 1)
        self.assertIn("UnicodeDecodeError", rows[0][1])

    def test_fts_form_filter_excludes_other_forms(self):
        rows = search(memory_db(), ["desktop"], ["utf-8"], False, "relevance", 10, 0)
        self.assertEqual(rows, [])

    def test_min_reactions_applies(self):
        rows = search(memory_db(), ["desktop"], [], True, "reactions", 10, 200)
        self.assertEqual(len(rows), 1)


class ExtractTests(unittest.TestCase):
    def test_engine_none_returns_none(self):
        saved = os.environ.pop("ISSUE_LENS_LLM_ENGINE", None)
        try:
            self.assertIsNone(extract_issue({"title": "x"}, "cli"))
        finally:
            if saved is not None:
                os.environ["ISSUE_LENS_LLM_ENGINE"] = saved

    def test_unknown_engine_raises(self):
        os.environ["ISSUE_LENS_LLM_ENGINE"] = "definitely-not-registered"
        try:
            with self.assertRaises(ValueError):
                extract_issue({"title": "x"}, "cli")
        finally:
            os.environ.pop("ISSUE_LENS_LLM_ENGINE", None)


class ConfigTests(unittest.TestCase):
    def test_forms_have_taxonomy_and_topics(self):
        for name, cfg in FORMS.items():
            with self.subTest(form=name):
                self.assertTrue(cfg["topics"])
                self.assertTrue(cfg["taxonomy"])
                self.assertGreater(cfg["min_stars"], 0)


if __name__ == "__main__":
    unittest.main()
