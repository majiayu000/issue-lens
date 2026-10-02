"""Five historical-issue-inspired black-box tests, using disposable fixtures only.

python3 experiments/rclean_acceptance.py --binary /path/to/rclean --out results.json
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile
import time


class Fixture:
    def __init__(self, binary, root):
        self.binary, self.root = binary, root
        self.env = {**os.environ, 'HOME': str(root / 'home'),
                    'XDG_DATA_HOME': str(root / 'data'), 'XDG_CACHE_HOME': str(root / 'cache'),
                    'XDG_CONFIG_HOME': str(root / 'config'), 'NO_COLOR': '1'}
        for directory in ['home', 'data', 'cache', 'config']:
            (root / directory).mkdir()
        self.calls = []

    def run(self, *args, closed_stdout=False):
        writer = None
        try:
            if closed_stdout:
                reader, writer = os.pipe()
                os.close(reader)
            result = subprocess.run([str(self.binary), *map(str, args)], cwd=self.root,
                                    env=self.env, input='', text=True, timeout=20,
                                    stdout=writer if closed_stdout else subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        finally:
            if writer is not None:
                os.close(writer)
        self.calls.append({'args': [str(arg).replace(str(self.root), '<fixture>') for arg in args],
                           'closed_stdout': closed_stdout, 'exit_code': result.returncode,
                           'stderr': result.stderr.replace(str(self.root), '<fixture>')})
        return result

    def node(self, name='project'):
        project = self.root / name
        (project / 'node_modules').mkdir(parents=True)
        (project / 'package.json').write_text('{}')
        (project / 'node_modules/payload').write_bytes(b'rebuildable-fixture')
        return project

    def bury(self):
        project = self.node()
        result = self.run('clean', project, '--all', '--graveyard', '--yes', '--min-size', '0')
        assert result.returncode == 0, result.stderr
        assert not (project / 'node_modules').exists()
        listed = self.run('graveyard', 'list', '--json')
        assert listed.returncode == 0, listed.stderr
        records = json.loads(listed.stdout)
        assert len(records) == 1
        return project, records[0]['id']

    def stored_bytes(self):
        return {str(p.relative_to(self.root / 'data')): p.read_bytes()
                for p in (self.root / 'data').rglob('*') if p.is_file()}


def project_name_exchange(f):
    parent = f.root / 'workspace'
    excluded = f.node('workspace/a')
    included = f.node('workspace/b')
    # rclean loads .rcleanignore at the scan root, not inside each subproject.
    (parent / '.rcleanignore').write_text('a/node_modules/\n')
    def scan():
        result = f.run('scan', parent, '--json', '--min-size', '0', '--ignore', 'not-present/**')
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        return {Path(c['path']).relative_to(parent).as_posix()
                for p in data['projects'] for c in p['candidates']}
    actual = scan()
    assert actual == {'b/node_modules'}, actual
    temporary = parent / 'exchange'
    excluded.rename(temporary)
    included.rename(excluded)
    temporary.rename(included)
    (parent / '.rcleanignore').write_text('b/node_modules/\n')
    actual = scan()
    assert actual == {'a/node_modules'}, actual
    assert (excluded / 'node_modules/payload').read_bytes() == b'rebuildable-fixture'
    assert (included / 'node_modules/payload').read_bytes() == b'rebuildable-fixture'


def age_filter_preserves_warning(f):
    project = f.node()
    (project / '.rcleanignore').write_text('{invalid,glob\n')
    baseline = f.run('scan', project, '--json', '--min-size', '0')
    assert baseline.returncode == 0, baseline.stderr
    original = json.loads(baseline.stdout)
    assert original['summary']['candidates'] == 1
    assert any(w['kind'] == 'ignoreFileLoad' for w in original['warnings'])
    filtered = f.run('scan', project, '--json', '--min-size', '0', '--older-than', '30d')
    assert filtered.returncode == 3, filtered.stderr
    actual = json.loads(filtered.stdout)
    assert actual['summary']['candidates'] == 0
    assert actual['warnings'] == original['warnings']


def closed_pipe_preserves_shortfall(f):
    project = f.node()
    normal = f.run('free', '1gb', project, '--json', '--min-size', '0',
                   '--write-plan', f.root / 'normal-plan.json')
    assert normal.returncode == 3, normal.stderr
    assert json.loads(normal.stdout)['targetMet'] is False
    broken = f.run('free', '1gb', project, '--json', '--min-size', '0',
                   '--write-plan', f.root / 'pipe-plan.json', closed_stdout=True)
    assert broken.returncode == normal.returncode, broken.stderr
    assert 'panicked' not in broken.stderr
    assert (project / 'node_modules/payload').read_bytes() == b'rebuildable-fixture'


def restore_conflict_keeps_both_copies(f):
    project, record_id = f.bury()
    before = f.stored_bytes()
    (project / 'node_modules').mkdir()
    user_file = project / 'node_modules/user.txt'
    user_file.write_bytes(b'user-data-must-survive')
    result = f.run('restore', '--id', record_id)
    assert result.returncode != 0
    assert user_file.read_bytes() == b'user-data-must-survive'
    assert not (project / 'node_modules/payload').exists()
    assert f.stored_bytes() == before


def restore_dry_run_has_no_writes(f):
    project, record_id = f.bury()
    before = f.stored_bytes()
    target = f.root / 'absent-parent/restored'
    result = f.run('restore', '--id', record_id, '--to', target, '--dry-run')
    assert result.returncode == 0, result.stderr
    assert 'would attempt to restore' in result.stdout
    assert not target.parent.exists()
    assert not (project / 'node_modules').exists()
    assert f.stored_bytes() == before


CASES = [project_name_exchange, age_filter_preserves_warning, closed_pipe_preserves_shortfall,
         restore_conflict_keeps_both_copies, restore_dry_run_has_no_writes]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    binary = args.binary.resolve(strict=True)
    if args.out.exists():
        parser.error('Output already exists')
    if os.name != 'posix':
        parser.error('This experiment requires macOS/Linux (closed-pipe fixture)')
    version = subprocess.run([str(binary), '--version'], capture_output=True, text=True, check=True).stdout.strip()
    results = []
    for case in CASES:
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix='issue-lens-acceptance-') as directory:
            fixture = Fixture(binary, Path(directory).resolve())
            entry = {'case': case.__name__}
            try:
                case(fixture)
                entry['status'] = 'passed'
            except Exception as error:
                entry.update(status='failed', error_type=type(error).__name__,
                             error=str(error).replace(str(fixture.root), '<fixture>'))
            entry.update(seconds=round(time.monotonic() - started, 3), commands=fixture.calls)
            results.append(entry)
            print(case.__name__ + ': ' + entry['status'], flush=True)
    report = {'binary_version': version, 'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
              'platform': platform.platform(), 'cases': results}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write('\n')
    return 0 if all(row['status'] == 'passed' for row in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
