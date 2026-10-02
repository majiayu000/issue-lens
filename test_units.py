"""离线单元测试:纯函数、内存库检索、提炼接口契约。CI 与本地统一入口:
    python3 -m unittest test_units -v
"""
import os
import copy
import http.client
import json
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
import urllib.error

from config import FORMS
from evidence import EvidenceError, attach_pr_evidence, fetch_pr_evidence, load_tests as load_test_files
from extract import enrich, extract_batch, extract_issue, find_issues
from llm import ModelError, generate_json
from s03_report import excerpt, md_escape
from s04_search import search
from s05_plan import build_plan, get_requirements, render_markdown, retrieve, validate_plan
from retrieval import collect_candidates

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
        db.execute("UPDATE issues SET url=? WHERE id=?",
                   (f"https://github.com/example/{repo}/issues/{iid}", iid))
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


def extraction(iid=3, quote="UnicodeDecodeError on UTF-8 filenames"):
    return {"id": iid, "issue_kind": "bug", "symptom": "Unicode 文件名失败",
            "root_cause": None, "root_cause_category": "编码",
            "environment": [], "evidence_quote": quote,
            "test_ideas": ["以 Unicode 文件名执行命令并检查退出码。"]}


class ModelBoundaryTests(unittest.TestCase):
    @staticmethod
    def completed(stdout='', stderr='', returncode=0):
        process = Mock(returncode=returncode)
        process.communicate.return_value = (stdout, stderr)
        process.__enter__ = Mock(return_value=process)
        process.__exit__ = Mock(return_value=False)
        return process

    @patch.dict(os.environ, {"ISSUE_LENS_LLM_ENGINE": "codex"})
    @patch("llm.subprocess.Popen")
    def test_nonzero_exit_does_not_echo_provider_credentials(self, run):
        run.return_value = self.completed('private-token', 'private-token', 2)
        with self.assertRaises(ModelError) as error:
            generate_json("hello", {})
        self.assertNotIn("private-token", str(error.exception))
        self.assertIn("exit 2", str(error.exception))

    @patch.dict(os.environ, {"ISSUE_LENS_LLM_ENGINE": "codex"})
    @patch("llm.subprocess.Popen")
    def test_truncated_response_is_rejected_even_with_parseable_json(self, run):
        run.return_value = self.completed(json.dumps(
            {"type": "turn.failed", "error": {"message": "truncated"}}))
        with self.assertRaises(ModelError):
            generate_json("hello", {})

    @patch.dict(os.environ, {"ISSUE_LENS_LLM_ENGINE": "codex"})
    @patch("llm.os.killpg")
    @patch("llm.subprocess.Popen")
    def test_timeout_is_a_failure(self, run, killpg):
        process = self.completed()
        process.pid = 123
        process.communicate.side_effect = [subprocess.TimeoutExpired('codex', 300), ('', '')]
        run.return_value = process
        with self.assertRaisesRegex(ModelError, "300-second"):
            generate_json("hello", {})
        killpg.assert_called_once_with(123, signal.SIGKILL)

    @patch.dict(os.environ, {"ISSUE_LENS_LLM_ENGINE": "codex"})
    def test_timeout_stops_launcher_and_its_child(self):
        real_popen = subprocess.Popen
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            child_pid = root/'child.pid'
            launcher = root/'codex'
            launcher.write_text(
                f'#!{sys.executable}\nimport subprocess, sys, time\nfrom pathlib import Path\n'
                'p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])\n'
                f'Path({str(child_pid)!r}).write_text(str(p.pid))\n'
                'time.sleep(60)\n')
            launcher.chmod(0o700)

            def start(*args, **kwargs):
                process = real_popen([sys.executable, str(launcher)], **kwargs)
                deadline = time.monotonic() + 5
                while not child_pid.exists() and process.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.01)
                communicate = process.communicate
                process.communicate = lambda input=None, timeout=None: communicate(
                    input=input, timeout=0.1 if timeout else None)
                return process

            with patch('llm.subprocess.Popen', side_effect=start), \
                    self.assertRaisesRegex(ModelError, '300-second'):
                generate_json('hello', {})
            pid = int(child_pid.read_text())
            status = subprocess.run(['ps', '-p', str(pid), '-o', 'stat='],
                                    capture_output=True, text=True).stdout.strip()
            if status and not status.startswith('Z'):
                os.kill(pid, signal.SIGKILL)
                self.fail('Timed-out Codex child is still running')

    @patch.dict(os.environ, {"ISSUE_LENS_LLM_ENGINE": "codex"})
    @patch("llm.subprocess.Popen")
    def test_tool_events_are_rejected_even_after_success(self, run):
        events = [{"type": "item.completed", "item": {"type": "command_execution"}},
                  {"type": "turn.completed"}]
        run.return_value = self.completed("\n".join(map(json.dumps, events)))
        with self.assertRaisesRegex(ModelError, "tool call"):
            generate_json("hello", {})

    @patch.dict(os.environ, {"ISSUE_LENS_LLM_ENGINE": "codex"})
    @patch("llm.subprocess.Popen")
    def test_invalid_output_is_rejected_even_after_success(self, run):
        def complete(command, **kwargs):
            Path(command[command.index("--output-last-message") + 1]).write_text('{"partial":')
            return self.completed('{"type":"turn.completed"}')
        run.side_effect = complete
        with self.assertRaisesRegex(ModelError, "invalid JSON"):
            generate_json("hello", {})

    @patch.dict(os.environ, {"ISSUE_LENS_LLM_ENGINE": "codex"})
    @patch("llm.subprocess.Popen")
    def test_success_preserves_provenance_without_inventing_cost(self, run):
        def complete(command, **kwargs):
            Path(command[command.index("--output-last-message") + 1]).write_text('{"ok":true}')
            events = [{"type": "thread.started", "thread_id": "real-session"},
                      {"type": "turn.completed", "usage": {"input_tokens": 20}}]
            return self.completed("\n".join(map(json.dumps, events)))
        run.side_effect = complete
        data, provenance = generate_json("hello", {})
        self.assertEqual(data, {"ok": True})
        self.assertEqual(provenance["thread_id"], "real-session")
        self.assertNotIn("total_cost_usd", provenance)
        command = run.call_args.args[0]
        self.assertIn("--ignore-user-config", command)
        self.assertEqual(command[command.index("--sandbox") + 1], "read-only")


class ExtractionGroundingTests(unittest.TestCase):
    @patch("extract.generate_json")
    def test_fabricated_quote_is_not_cached(self, generate):
        db = memory_db()
        issues = find_issues(db, "cli", ["utf-8"], 5)
        generate.return_value = ({"issues": [extraction(quote="The fix was to disable security")]}, {})
        with self.assertRaisesRegex(ModelError, "verbatim"):
            enrich(db, issues, "cli")
        self.assertEqual(db.execute("SELECT COUNT(extract_json) FROM issues").fetchone()[0], 0)

    @patch("extract.generate_json")
    def test_partial_or_duplicate_batch_is_rejected(self, generate):
        issues = [{"id": 3, "title": "UnicodeDecodeError on UTF-8 filenames", "body": ""},
                  {"id": 4, "title": "Other issue", "body": ""}]
        for rows in ([extraction()], [extraction(), extraction()]):
            with self.subTest(rows=len(rows)):
                generate.return_value = ({"issues": rows}, {})
                with self.assertRaises(ModelError):
                    extract_batch(issues, "cli")

    @patch("extract.generate_json")
    def test_repeat_run_reuses_saved_extraction_and_preserves_unknown_cause(self, generate):
        db = memory_db()
        generate.return_value = ({"issues": [extraction()]}, {"sessionId": "extract-session"})
        first = enrich(db, find_issues(db, "cli", ["utf-8"], 5), "cli")
        second = enrich(db, find_issues(db, "cli", ["utf-8"], 5), "cli")
        self.assertEqual(first, second)
        self.assertIsNone(second[0]["extraction"]["root_cause"])
        self.assertEqual(generate.call_count, 1)


class PlanGroundingTests(unittest.TestCase):
    def setUp(self):
        self.requirements = [{"id": "R1", "title": "Unicode 文件", "quote": "接受中文文件名",
                              "queries": [["unicode", "filename"]], "retrieved_source_ids": [3]}]
        self.sources = [{"id": 3, "title": "Unicode filename", "repo": "example/tool",
                         "url": "https://github.com/example/tool/issues/3", "extraction": extraction()}]
        self.plan = {"cases": [{"requirement_id": "R1", "category": "编码", "title": "中文路径",
                               "preconditions": [], "steps": ["传入中文文件名"],
                               "expected_result": "文件被正确处理，退出码为 0",
                               "source_ids": [3], "rationale": "相同的文件名边界",
                               "coverage": "not_reviewed", "incremental_value": "尚未对照现有测试",
                               "existing_tests": []}],
                     "coverage_gaps": []}

    def test_unknown_source_is_rejected(self):
        self.plan["cases"][0]["source_ids"] = [999]
        with self.assertRaisesRegex(ModelError, "source"):
            validate_plan(self.plan, self.requirements, self.sources)

    def test_omitted_requirement_requires_an_explicit_gap(self):
        self.requirements.append({"id": "R2"})
        with self.assertRaisesRegex(ModelError, "omitted"):
            validate_plan(self.plan, self.requirements, self.sources)
        self.plan["coverage_gaps"] = [{"requirement_id": "R2", "reason": "没有权限相关案例"}]
        validate_plan(self.plan, self.requirements, self.sources)

    @patch("s05_plan.generate_json")
    def test_invented_prd_requirement_quote_is_rejected(self, generate):
        generate.return_value = ({"requirements": copy.deepcopy(self.requirements),
                                  "open_questions": []}, {})
        with self.assertRaisesRegex(ModelError, "quote"):
            get_requirements("只支持 ASCII 文件名", "cli")

    @patch("s05_plan.generate_json")
    def test_no_matches_still_generates_prd_tests_without_fake_sources(self, generate):
        requirement = {"title": "未知功能", "quote": "仅测试 xyzzyquux",
                       "queries": [["xyzzyquux", "zzzznone"]]}
        self.plan['cases'][0]['source_ids'] = []
        generate.side_effect = [({"requirements": [requirement], "open_questions": []}, {}),
                                (self.plan, {})]
        report = build_plan(memory_db(), "仅测试 xyzzyquux", "cli", 3)
        self.assertEqual(report["sources"], [])
        self.assertEqual(len(report["cases"]), 1)
        self.assertEqual(report["cases"][0]["source_ids"], [])
        self.assertEqual(generate.call_count, 2)

    @patch("s05_plan.retrieve", return_value=([], {}))
    @patch("s05_plan.enrich")
    @patch("s05_plan.generate_json")
    def test_model_cannot_replace_trusted_sources_or_execution_status(self, generate, enrich_mock, retrieve_mock):
        poisoned = {**self.plan, "status": "passed", "sources": [], "prd_sha256": "fake"}
        generate.side_effect = [({"requirements": copy.deepcopy(self.requirements),
                                 "open_questions": []}, {}), (poisoned, {})]
        enrich_mock.return_value = self.sources
        report = build_plan(memory_db(), "接受中文文件名", "cli", 3)
        self.assertEqual(report["status"], "draft_not_executed")
        self.assertEqual(report["sources"], self.sources)
        self.assertNotEqual(report["prd_sha256"], "fake")

    @patch("retrieval.generate_json")
    def test_retrieval_honors_form_and_allocates_candidates_across_themes(self, generate):
        requirements = [{"id": "R1", "queries": [["crash", "startup"]]},
                        {"id": "R2", "queries": [["menu", "window"]]}]
        generate.return_value = ({"matches": [
            {"requirement_id": "R1", "source_id": 1, "quote": SEED[0][3], "reason": "启动"},
            {"requirement_id": "R2", "source_id": 2, "quote": SEED[1][3], "reason": "菜单"}]}, {})
        selected, _ = retrieve(memory_db(), "desktop", requirements, 2)
        self.assertEqual({row["id"] for row in selected}, {1, 2})
        self.assertNotIn(3, {row["id"] for row in selected})

    def test_render_resolves_links_from_database_sources_and_marks_unexecuted(self):
        validate_plan(self.plan, self.requirements, self.sources)
        report = {"form": "cli", "corpus_issue_count": 1, "requirements": self.requirements,
                  "sources": self.sources, "open_questions": [], **self.plan}
        rendered = render_markdown(report)
        self.assertIn("https://github.com/example/tool/issues/3", rendered)
        self.assertIn("未执行", rendered)
        self.assertIn("UnicodeDecodeError on UTF-8 filenames", rendered)


class RetrievalImprovementTests(unittest.TestCase):
    def test_conjunction_rejects_single_keyword_overlap(self):
        requirements = [{"id": "R1", "queries": [["crash", "menu"]]}]
        self.assertEqual(collect_candidates(memory_db(), "desktop", requirements), [])

    @patch("retrieval.generate_json")
    def test_semantic_rejection_does_not_fall_back_to_keyword_hits(self, generate):
        generate.return_value = ({"matches": []}, {"engine": "codex"})
        reqs = [{"id": "R1", "queries": [["crash", "startup"]]}]
        selected, _ = retrieve(memory_db(), "desktop", reqs, 2)
        self.assertEqual(selected, [])
        self.assertEqual(reqs[0]["candidate_ids"], [1])
        self.assertEqual(reqs[0]["retrieved_source_ids"], [])

    @patch("retrieval.generate_json")
    def test_unknown_id_and_fabricated_selection_quote_are_rejected(self, generate):
        for iid, quote in [(99, SEED[0][3]), (1, "invented cause")]:
            generate.return_value = ({"matches": [{"requirement_id": "R1", "source_id": iid,
                                                   "quote": quote, "reason": "reason"}]}, {})
            with self.subTest(iid=iid), self.assertRaises(ModelError):
                retrieve(memory_db(), "desktop", [{"id": "R1", "queries": [["crash", "startup"]]}], 2)

    @patch("retrieval.generate_json")
    def test_no_candidate_does_not_call_model(self, generate):
        selected, provenance = retrieve(memory_db(), "cli", [
            {"id": "R1", "queries": [["xyzzy", "missing"]]}], 3)
        self.assertEqual((selected, provenance), ([], {}))
        generate.assert_not_called()

    def test_quoted_terms_cannot_change_query_boolean_structure(self):
        reqs = [{"id": "R1", "queries": [['crash" OR "menu', 'absentword']]}]
        self.assertEqual(collect_candidates(memory_db(), "desktop", reqs), [])


class CoverageEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.requirements = [{"id": "R1"}]
        self.tests = [{"id": "T1", "path": "/tests/test_paths.py",
                       "content": "# fixture\nassert outside.read_text() == 'keep'\n", "sha256": "hash"}]
        self.case = {"requirement_id": "R1", "category": "文件安全", "title": "检查根替换",
                     "preconditions": [], "steps": ["替换根"], "expected_result": "拒绝",
                     "source_ids": [], "rationale": "PRD 契约", "coverage": "partial",
                     "incremental_value": "增加根替换时序", "existing_tests": [{
                         "test_id": "T1", "quote": "assert outside.read_text() == 'keep'",
                         "reason": "已有外部文件保持不变的断言"}]}

    def test_source_line_is_computed_and_model_path_is_ignored(self):
        self.case["existing_tests"][0].update(path="/fake", line=999)
        validate_plan({"cases": [self.case], "coverage_gaps": []}, self.requirements, [], self.tests)
        self.assertEqual(self.case["existing_tests"][0]["path"], self.tests[0]["path"])
        self.assertEqual(self.case["existing_tests"][0]["line"], 2)

    def test_fabricated_or_ambiguous_assertion_cannot_prove_coverage(self):
        for quote, content in [("assert invented", self.tests[0]["content"]),
                               ("assert x", "assert x\nassert x")]:
            self.case["existing_tests"][0]["quote"] = quote
            self.tests[0]["content"] = content
            with self.subTest(quote=quote), self.assertRaises(ModelError):
                validate_plan({"cases": [self.case], "coverage_gaps": []}, self.requirements, [], self.tests)

    def test_no_tests_cannot_be_reported_as_missing_or_covered(self):
        for status in ("covered", "partial", "not_found"):
            self.case.update(coverage=status, existing_tests=[])
            with self.subTest(status=status), self.assertRaises(ModelError):
                validate_plan({"cases": [self.case], "coverage_gaps": []}, self.requirements, [])

    def test_potential_additions_sort_before_covered_cases(self):
        covered = copy.deepcopy(self.case)
        covered["coverage"] = "covered"
        new = {**self.case, "coverage": "not_found", "existing_tests": []}
        plan = {"cases": [covered, new], "coverage_gaps": []}
        validate_plan(plan, self.requirements, [], self.tests)
        self.assertEqual([c['coverage'] for c in plan['cases']], ['not_found', 'covered'])
        self.assertEqual([c['id'] for c in plan['cases']], ['TC001', 'TC002'])

    def test_test_input_deduplicates_files_and_records_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.py'
            path.write_text('assert True\n')
            loaded = load_test_files([path, path])
        self.assertEqual(len(loaded), 1)
        self.assertEqual(len(loaded[0]['sha256']), 64)


class PullEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.source = {'id': 1, 'url': 'https://github.com/owner/repo/issues/9'}
        self.event = {'event': 'cross-referenced', 'source': {'issue': {
            'html_url': 'https://github.com/another/project/pull/7', 'pull_request': {'url': 'unused'}}}}
        self.pr = {'title': 'Patch', 'body': 'Proposed fix', 'state': 'open', 'merged': False,
                   'head': {'sha': 'head'}, 'base': {'sha': 'base'}, 'changed_files': 101}

    def test_cross_repo_reference_and_partial_patches_are_not_claimed_as_fixed(self):
        client = Mock()
        client.get.side_effect = [[self.event, self.event], self.pr,
                                  [{'filename': 'test_paths.rs', 'status': 'added', 'patch': '+' * 13000},
                                   {'filename': 'binary.png', 'status': 'modified'}]]
        evidence = fetch_pr_evidence(self.source, client)
        self.assertEqual(len(evidence['pulls']), 1)
        pr = evidence['pulls'][0]
        self.assertFalse(pr['merged'])
        self.assertEqual(pr['relation'], 'cross_reference_not_verified_fix')
        self.assertTrue(pr['files_truncated'])
        self.assertTrue(pr['files'][0]['patch_truncated'])
        self.assertTrue(pr['files'][1]['patch_unavailable'])
        self.assertEqual(client.get.call_args_list[1].args[0], '/repos/another/project/pulls/7')

    def test_timeline_paginates_and_flags_cap_without_fake_completeness(self):
        client = Mock()
        client.get.return_value = [{'event': 'commented'}] * 100
        evidence = fetch_pr_evidence(self.source, client)
        self.assertEqual(client.get.call_count, 3)
        self.assertTrue(evidence['timeline_may_be_truncated'])
        self.assertEqual(evidence['pulls'], [])

    def test_foreign_origin_reference_is_never_requested(self):
        self.event['source']['issue']['html_url'] = 'https://evil.invalid/owner/repo/pull/7'
        client = Mock()
        client.get.return_value = [self.event]
        with self.assertRaises(EvidenceError):
            fetch_pr_evidence(self.source, client)
        self.assertEqual(client.get.call_count, 1)

    @patch('evidence.GitHub')
    def test_only_cited_sources_are_fetched(self, github):
        github.return_value.get.return_value = []
        other = {'id': 2, 'url': 'https://github.com/owner/repo/issues/10'}
        attach_pr_evidence([self.source, other], {1})
        self.assertIn('pr_evidence', self.source)
        self.assertNotIn('pr_evidence', other)
        self.assertEqual(github.return_value.get.call_count, 1)

    @patch('evidence.GitHub')
    def test_malformed_timeline_fails_with_evidence_error(self, github):
        github.return_value.get.return_value = [None]
        with self.assertRaises(EvidenceError):
            attach_pr_evidence([self.source], {1})
        self.assertNotIn('pr_evidence', self.source)

    @patch('evidence.GitHub')
    def test_fetch_failure_is_not_silently_recorded_as_no_prs(self, github):
        github.return_value.get.side_effect = urllib.error.HTTPError(
            'https://api.github.com/path', 403, 'private-token', {}, None)
        with self.assertRaises(EvidenceError) as error:
            attach_pr_evidence([self.source], {1})
        self.assertIn('403', str(error.exception))
        self.assertNotIn('private-token', str(error.exception))
        self.assertNotIn('pr_evidence', self.source)

    @patch('evidence.GitHub')
    def test_incomplete_http_response_fails_without_exposing_payload(self, github):
        github.return_value.get.side_effect = http.client.IncompleteRead(b'private-token')
        with self.assertRaises(EvidenceError) as error:
            attach_pr_evidence([self.source], {1})
        self.assertNotIn('private-token', str(error.exception))
        self.assertNotIn('pr_evidence', self.source)


class ImprovementIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.requirement = {'title': '中文文件名', 'quote': '接受中文文件名',
                            'queries': [['utf-8', 'filename']]}
        self.test = {'id': 'T1', 'path': '/tests/unicode.py',
                     'content': "assert filename == '中文.txt'\n", 'sha256': 'hash'}
        self.case = {'requirement_id': 'R1', 'category': '编码', 'title': 'Unicode 路径',
                     'preconditions': [], 'steps': ['执行'], 'expected_result': '成功',
                     'source_ids': [3], 'rationale': '文件名边界', 'coverage': 'partial',
                     'incremental_value': '补充异常编码', 'existing_tests': [
                         {'test_id': 'T1', 'quote': "assert filename == '中文.txt'", 'reason': '已有基本断言'}]}

    @patch('evidence.GitHub')
    @patch('extract.generate_json')
    @patch('retrieval.generate_json')
    @patch('s05_plan.generate_json')
    def test_full_pipeline_selects_extracts_reviews_tests_then_uses_pr_evidence(
            self, plan_model, select_model, extract_model, github):
        draft = {'cases': [copy.deepcopy(self.case)], 'coverage_gaps': []}
        revised = copy.deepcopy(draft)
        revised['cases'][0]['steps'] = ['依据补丁补充边界执行']
        plan_model.side_effect = [({'requirements': [self.requirement], 'open_questions': []}, {}),
                                  (draft, {}), (revised, {'engine': 'codex'})]
        select_model.return_value = ({'matches': [{'requirement_id': 'R1', 'source_id': 3,
            'quote': SEED[2][3], 'reason': '相同输入边界'}]}, {})
        extract_model.return_value = ({'issues': [extraction()]}, {'engine': 'codex'})
        github.return_value.get.side_effect = [[{'event': 'cross-referenced', 'source': {'issue': {
            'html_url': 'https://github.com/example/yt-dlp/pull/4', 'pull_request': { 'url': 'unused'}}}}],
            {'title': 'Unicode fix', 'body': 'Fix', 'state': 'closed', 'merged': True,
             'head': {'sha': 'head'}, 'base': {'sha': 'base'}, 'changed_files': 1},
            [{'filename': 'tests/test.py', 'status': 'modified', 'patch': '+assert filename'}]]
        report = build_plan(memory_db(), '接受中文文件名', 'cli', 12, [self.test], True)
        self.assertEqual(report['cases'][0]['steps'], ['依据补丁补充边界执行'])
        self.assertEqual(report['test_inputs'][0]['sha256'], 'hash')
        self.assertNotIn('content', report['test_inputs'][0])
        self.assertEqual(report['sources'][0]['pr_evidence']['pulls'][0]['head_sha'], 'head')
        self.assertEqual(report['generation']['pr_review']['engine'], 'codex')
        self.assertEqual(extract_model.call_count, 1)
        self.assertEqual(select_model.call_count, 1)
        self.assertEqual(plan_model.call_count, 3)
        rendered = render_markdown(report)
        self.assertIn('补充边界', rendered)
        self.assertIn('/tests/unicode.py:1', rendered)
        self.assertIn('https://github.com/example/yt-dlp/pull/4', rendered)
        self.assertIn('交叉引用不等于确认修复', rendered)

    @patch('evidence.GitHub')
    @patch('s05_plan.generate_json')
    def test_prd_only_plan_does_not_request_github_even_with_pr_option(self, model, github):
        self.requirement['queries'] = [['xyzzy', 'absent']]
        self.case.update(source_ids=[], coverage='not_reviewed', existing_tests=[])
        model.side_effect = [({'requirements': [self.requirement], 'open_questions': []}, {}),
                             ({'cases': [self.case], 'coverage_gaps': []}, {})]
        report = build_plan(memory_db(), '接受中文文件名', 'cli', 12, with_pr_evidence=True)
        github.assert_not_called()
        self.assertEqual(report['sources'], [])
        self.assertIn('PRD 基础用例', render_markdown(report))

    @patch('s05_plan.build_plan', side_effect=EvidenceError('PR fetch failed'))
    def test_cli_failure_does_not_publish_a_report(self, build):
        from s05_plan import main
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prd, output = root/'prd.md', root/'plan.md'
            prd.write_text('scope')
            database = root/'issues.db'
            sqlite3.connect(database).close()
            with patch('sys.argv', ['s05_plan.py', '--form', 'cli', '--prd', str(prd),
                                    '--out', str(output), '--with-pr-evidence']), \
                    patch('config.DB_PATH', str(database)), patch('sys.stderr'), \
                    self.assertRaises(SystemExit) as error:
                main()
            self.assertEqual(error.exception.code, 1)
            self.assertFalse(output.exists())
            self.assertFalse(output.with_suffix('.json').exists())

    @patch('s05_plan.build_plan')
    def test_cli_non_utf8_test_file_fails_before_model_call(self, build):
        from s05_plan import main
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prd, test, output = root/'prd.md', root/'test.py', root/'plan.md'
            prd.write_text('scope')
            test.write_bytes(b'\xff')
            with patch('sys.argv', ['s05_plan.py', '--form', 'cli', '--prd', str(prd),
                                    '--out', str(output), '--tests', str(test)]), \
                    patch('sys.stderr'), self.assertRaises(SystemExit) as error:
                main()
            self.assertEqual(error.exception.code, 1)
            build.assert_not_called()
            self.assertFalse(output.exists())
            self.assertFalse(output.with_suffix('.json').exists())


if __name__ == "__main__":
    unittest.main()
