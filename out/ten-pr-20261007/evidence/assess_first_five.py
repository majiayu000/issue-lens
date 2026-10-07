"""Materialize manually reviewed case assessments with verified source quotes."""
import json
from pathlib import Path

EVIDENCE = Path('/Users/apple/.codex/task-evidence/issue-lens-20261007')
OUT = Path('/Users/apple/.codex/worktrees/issue-lens-comparison-20261007/out/ten-pr-20261007')
ADDITIONAL = {
    'Textualize--rich': {
        ('A', 'TC001'): 'test_A_TC001_direct_console_print',
        ('A', 'TC002'): 'test_A_TC002_whole_ascii_word_moves_to_new_line',
        ('B', 'TC001'): 'test_B_TC001_whole_cjk_word_moves_to_new_line',
        ('B', 'TC002'): 'test_B_TC002_cjk_long_word_after_prefix',
    },
    'pallets--click': {
        ('A', 'TC001'): 'test_A_TC001_marker_only_first_paragraph',
        ('A', 'TC002'): 'test_A_TC002_B_TC001_eg_abbreviation',
        ('B', 'TC001'): 'test_A_TC002_B_TC001_eg_abbreviation',
        ('B', 'TC002'): 'test_B_TC002_empty_and_whitespace_and_marker',
    },
    'fastapi--typer': {
        ('A', 'TC001'): 'test_A_TC001_required_list_missing_stays_usage_error',
        ('A', 'TC002'): 'test_A_TC002_envvar_absent_and_present',
        ('B', 'TC001'): 'test_B_TC001_explicit_empty_string_is_one_element',
        ('B', 'TC002'): 'test_B_TC002_envvar_actual_lists',
    },
    'theskumar--python-dotenv': {
        ('A', 'TC001'): 'test_A_TC001_B_TC001_quoted_empty',
        ('B', 'TC001'): 'test_A_TC001_B_TC001_quoted_empty',
        ('A', 'TC002'): 'test_A_TC002_B_TC002_missing_key_nonempty_file',
        ('B', 'TC002'): 'test_A_TC002_B_TC002_missing_key_nonempty_file',
    },
    'tox-dev--platformdirs': {
        ('A', 'TC001'): 'test_A_TC001_public_construction_assignment_docs',
        ('A', 'TC002'): 'test_B_TC001_private_storage_and_public_attributes',
        ('A', 'TC003'): 'test_A_TC003_B_TC002_unix_component_no_escape_after_rejected_assignment',
        ('A', 'TC004'): 'test_B_TC003_none_public_api_and_mock_windows',
        ('B', 'TC001'): 'test_B_TC001_private_storage_and_public_attributes',
        ('B', 'TC002'): 'test_A_TC003_B_TC002_unix_component_no_escape_after_rejected_assignment',
        ('B', 'TC003'): 'test_B_TC003_none_public_api_and_mock_windows',
    },
}
SOURCE_REVIEWS = {
    'fastapi--typer': [{
        'source_id': 4560755924, 'url': 'https://github.com/Hmbown/Codewhale/issues/2483',
        'relevance': 'weak_analogy', 'shared_trigger_mechanism': False,
        'reason': 'Both invite omitted/default/empty-list distinction, but serde deserialize_with without a default annotation is not Typer list conversion. This is a transferable input-partition idea, not evidence of a shared causal defect.',
        'target_evidence': [{'path': 'typer/main.py', 'line': 1458, 'quote': 'if (value is None) or (default_value is None and len(value) == 0):'},
                            {'path': 'typer/main.py', 'line': 1690, 'quote': 'default_value=default_value'}],
        'adoptable_transfer': 'Only current-diff omission/explicit empty/default partitions, if executable requirements support them.',
        'rejected_transfer': 'Rust configuration deserializer root cause and upgrade/config platform work.'
    }],
    'tox-dev--platformdirs': [{
        'source_id': 4536421142, 'url': 'https://github.com/stablyai/orca/issues/2929',
        'relevance': 'weak_analogy', 'shared_trigger_mechanism': False,
        'reason': 'Both concern unsafe path-derived filesystem side effects, but clone abort ownership and recursive deletion differs from assignment validation before directory creation. The target API has no abort or recursive-removal operation.',
        'target_evidence': [{'path': 'src/platformdirs/api.py', 'line': 93, 'quote': '_ensure_inside_base("appname", value)'},
                            {'path': 'src/platformdirs/api.py', 'line': 147, 'quote': 'Path(path).mkdir(parents=True, exist_ok=True)'},
                            {'path': 'src/platformdirs/api.py', 'line': 539, 'quote': 'drive, tail = os.path.splitdrive(value)'}],
        'adoptable_transfer': 'Current-diff containment checks can inspect filesystem side effects in owned temporary directories.',
        'rejected_transfer': 'Clone abort, deletion ownership tracking, git processes and new cleanup abstractions.'
    }],
}

def assess(slug):
    native = json.loads((OUT / ('native_' + slug + '.json')).read_text())
    history = json.loads((OUT / 'runs-1' / slug / 'history.json').read_text())
    source_reviews = SOURCE_REVIEWS.get(slug, [])
    for source in source_reviews:
        for ref in source['target_evidence']:
            text = (EVIDENCE / 'samples' / slug / ref['path']).read_text()
            if ref['quote'] not in text:
                raise RuntimeError('Missing target causal evidence')
            ref['line'] = text[:text.index(ref['quote'])].count('\n') + 1
            ref['verified_against_frozen_head'] = True
    execution_file = OUT / ('execution_' + slug + '.json')
    additional_command = json.loads(execution_file.read_text()) if execution_file.exists() else None
    rows = []
    for arm in ['A', 'B']:
        proposal = json.loads((OUT / 'runs-1' / slug / (arm + '.json')).read_text())
        for case in proposal['plan']['cases']:
            citations = []
            for ref in case['existing_tests']:
                source = (EVIDENCE / 'samples' / slug / ref['path']).read_text()
                quote = ref['quote']
                if quote not in source:
                    raise RuntimeError(f'Unverified source quote: {slug} {arm} {case["id"]}')
                citations.append({'path': ref['path'], 'line': source[:source.index(quote)].count('\n') + 1,
                                  'quote': quote, 'verified_against_frozen_head': True, 'scope': ref['reason']})
            test_name = ADDITIONAL.get(slug, {}).get((arm, case['id']))
            if test_name:
                execution = {'kind': 'additional_boundary_check', 'command': additional_command,
                             'test': str(EVIDENCE / 'model-checks' / slug / 'test_model_cases.py') + '::' + test_name,
                             'result': 'passed' if additional_command['exit_code'] == 0 else 'failed'}
                level = 'partial' if citations else 'not_found'
                adoption = True
                reason = 'Adopted as an isolated executable regression candidate for a distinct current-diff boundary; not committed to upstream. Passing validates executability and the stated output only.'
            else:
                command = next(c for c in reversed(native['commands']) if 'pytest' in c['command'])
                execution = {'kind': 'reuse_native_assertions', 'command': command, 'result': native['result'],
                             'assertion_citations': citations}
                level = 'covered'
                adoption = False
                reason = 'Same trigger and output assertions already exist at the frozen head. Reused the passing native suite; no new regression candidate adopted.'
            row = {'arm': arm, 'case_id': case['id'], 'title': case['title'], 'applicable': True,
                         'existing_coverage': {'level': level, 'citations': citations,
                                               'review_scope': 'Frozen native test files and targeted whole-tests-directory literal search; semantic comparison of cited assertions.'},
                         'execution': execution, 'new_defect': False if execution['result'] == 'passed' else None,
                         'technical_adoption': adoption, 'technical_adoption_reason': reason,
                         'human_maintainer_adoption': None, 'source_ids': case['source_ids']}
            if slug == 'tox-dev--platformdirs':
                row['execution']['platform_scope'] = 'Native local macOS Python 3.12; Unix class with isolated XDG env and temporary real filesystem; Windows class with get_win_folder mocked. Windows drive paths were skipped in native matrix.'
                row['full_requirement_verified'] = case['id'] in ['TC001', 'TC002'] if arm == 'A' else case['id'] == 'TC001'
                row['platform_validation_pending'] = [] if row['full_requirement_verified'] else ['Native Windows validation (including drive-letter paths)', 'Linux and Android host runs, where named by the proposal']
            else:
                row['full_requirement_verified'] = execution['result'] == 'passed'
            rows.append(row)
    result = {'id': slug, 'head_sha': native['head_sha'], 'status': 'technically_assessed', 'cases': rows,
              'human_maintainer_adoption': None, 'history_source_count': len(history['sources']),
              'history_source_assessment': source_reviews,
              'limitations': ['Technical review is by this agent, not external maintainers.',
                             'No newly discovered product defect in executed cases.',
                             'Incremental checks passing do not prove historical retrieval improves review.',
                             'Technical review wall time was not separately timed; command durations are measured.'],
              'history_treatment': 'No retrieved historical cases in either arm for this sample; A/B differences are repeated generation variability, not evidence of historical-case benefit.' if not history['sources'] else 'B received retrieved history; source_ids are retained per case and no passing test is attributed causally to retrieval.'}
    (OUT / ('assessment_' + slug + '.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(slug, len(rows), 'cases assessed', sum(r['technical_adoption'] for r in rows), 'incremental arm-case candidates')

if __name__ == '__main__':
    for slug in ADDITIONAL:
        if (OUT / 'runs-1' / slug / 'B.json').exists():
            assess(slug)
