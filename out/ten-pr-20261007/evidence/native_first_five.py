"""Run frozen PR native test files in separate venvs; preserve command evidence."""
import json
import os
from pathlib import Path
import platform
import subprocess
import time
import xml.etree.ElementTree as ET

EVIDENCE = Path('/Users/apple/.codex/task-evidence/issue-lens-20261007')
OUT = Path('/Users/apple/.codex/worktrees/issue-lens-comparison-20261007/out/ten-pr-20261007')
PYTHON = '/Users/apple/.local/bin/python3.12'
CONFIG = {
    'Textualize--rich': ['pytest>=7,<8', 'pytest-cov>=3,<4', 'attrs>=21.4,<22'],
    'pallets--click': ['pytest'],
    'fastapi--typer': ['pytest>=9', 'pytest-cov>=7', 'pytest-sugar>=1', 'pytest-xdist>=3.6.1'],
    'theskumar--python-dotenv': ['pytest>=9.0.3', 'pytest-cov', 'click', 'ipython'],
    'tox-dev--platformdirs': ['appdirs==1.4.4', 'covdefaults>=2.3', 'diff-cover>=10.2', 'pytest>=9.0.2', 'pytest-cov>=7', 'pytest-mock>=3.15.1'],
}
NOTES = {
    'Textualize--rich': 'Current diff changes cell-aware folding and chop_cells. Native cells/text files exercise CJK width and wrapping; no historical-benefit inference follows from passing them. Terminal presentation outside these assertions is unverified.',
    'pallets--click': 'Current diff changes first-paragraph shortening, sentence boundaries and textwrap.shorten. The selected native file is the full helper regression suite. Passing it does not establish whether abbreviations and lowercase continuation are universally semantically correct.',
    'fastapi--typer': 'Current diff changes empty/default list argument conversion. The types suite compares explicit values, options, list arguments and envvar defaults. This baseline is runtime validation on Python 3.12, not a full supported-version matrix.',
    'theskumar--python-dotenv': 'Current diff changes CLI get missing/None versus empty-string behavior. The full CLI file exercises real CliRunner and isolated files. Error exit contracts for missing/bare keys should remain distinct from valid empty values.',
    'tox-dev--platformdirs': 'Current diff validates appname/appauthor/version on assignment through setters. The API suite exercises construction, assignment, containment and mocked platform behavior. Real Windows drive paths/known-folder APIs require Windows; mocked tests are not device verification.',
}

def run(slug, label, argv, cwd, extra_env=None):
    log_dir = EVIDENCE / 'native-logs' / slug
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / (label + '.log')
    attempt = 2
    while path.exists():
        path = log_dir / (label + f'.attempt-{attempt}.log')
        attempt += 1
    env = os.environ.copy()
    # Avoid forwarding plugin/provider credentials into sample processes.
    for key in list(env):
        if any(part in key.upper() for part in ('TOKEN', 'SECRET', 'API_KEY', 'PASSWORD')):
            env.pop(key)
    env.update(extra_env or {})
    begin = time.monotonic()
    with path.open('w') as stream:
        proc = subprocess.run(argv, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT)
    entry = {'command': argv, 'cwd': str(cwd), 'exit_code': proc.returncode,
             'seconds': round(time.monotonic() - begin, 3), 'log': str(path.relative_to(EVIDENCE)),
             'environment_overrides': extra_env or {}}
    print(slug, label, proc.returncode, entry['seconds'], flush=True)
    return entry

def main():
    for slug, deps in CONFIG.items():
        data = json.loads((OUT / (slug + '.input.json')).read_text())
        checkout = Path(data['checkout'])
        head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=checkout, text=True).strip()
        if head != data['head_sha']:
            raise RuntimeError(f'{slug}: frozen head mismatch')
        initial_status = subprocess.check_output(['git', 'status', '--short'], cwd=checkout, text=True)
        venv = EVIDENCE / 'native-venvs' / slug
        commands = [run(slug, '01-venv', [PYTHON, '-m', 'venv', str(venv)], checkout)]
        python = str(venv / 'bin/python')
        if commands[-1]['exit_code'] == 0:
            commands.append(run(slug, '02-install', [python, '-m', 'pip', 'install', '-e', '.', *deps], checkout))
        xml_path = EVIDENCE / 'native-logs' / slug / 'pytest.xml'
        test_paths = [x['path'] for x in data['tests']]
        extra_env = {'TERMINAL_WIDTH': '3000', '_TYPER_FORCE_DISABLE_TERMINAL': '1', '_TYPER_RUN_INSTALL_COMPLETION_TESTS': '1'} if slug == 'fastapi--typer' else {}
        extra_env['PATH'] = str(venv / 'bin') + os.pathsep + os.environ.get('PATH', '')
        if commands[-1]['exit_code'] == 0:
            commands.append(run(slug, '03-pytest', [python, '-m', 'pytest', '-q', '--junitxml', str(xml_path), *test_paths], checkout, extra_env))
            commands.append(run(slug, '04-freeze', [python, '-m', 'pip', 'freeze'], checkout))
            commands.append(run(slug, '05-environment', [python, '-c', 'import sys,platform;print(sys.version);print(platform.platform())'], checkout))
        counts = None
        if xml_path.exists():
            root = ET.parse(xml_path).getroot()
            suites = [root] if root.tag == 'testsuite' else root.findall('testsuite')
            counts = {key: sum(int(s.get(key, 0)) for s in suites) for key in ['tests','failures','errors','skipped']}
            counts['passed'] = counts['tests'] - counts['failures'] - counts['errors'] - counts['skipped']
        test_command = next((c for c in commands if c['log'].endswith('03-pytest.log')), None)
        result = {'id': slug, 'repo': data['repo'], 'pr': data['pr']['number'],
                  'head_sha': head, 'native_test_files': test_paths, 'commands': commands,
                  'environment': {'python': python, 'python_base': PYTHON, 'platform': platform.platform()},
                  'result': 'passed' if test_command and test_command['exit_code'] == 0 else 'failed' if test_command else 'environment_blocked',
                  'test_counts': counts, 'initial_git_status': initial_status,
                  'final_git_status': subprocess.check_output(['git','status','--short'],cwd=checkout,text=True),
                  'platform_limits': ['Only the local macOS Python 3.12 environment was run; supported OS/Python matrices were not run.'],
                  'notes': NOTES[slug], 'evidence_root': str(EVIDENCE)}
        (OUT / ('native_' + slug + '.json')).write_text(json.dumps(result, indent=2) + '\n')

if __name__ == '__main__':
    main()
