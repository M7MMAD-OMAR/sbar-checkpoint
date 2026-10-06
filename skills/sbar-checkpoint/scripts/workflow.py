#!/usr/bin/env python3
"""Checkpoint evidence engine. Uses Python's standard library on POSIX systems."""
import argparse
import contextlib
import copy
import datetime
import fcntl
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import tempfile
import time
import uuid

VERSION = '1.0.0'
MAX_LOG = 4 * 1024 * 1024
MAX_JSON = 8 * 1024 * 1024
ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$')
EXCLUDED = {'.git', '.hg', '.svn', '__pycache__', 'node_modules', '.venv', 'venv'}


class WorkflowError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise WorkflowError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def file_hash(path):
    h = hashlib.sha256()
    before = Path(path).stat()
    with Path(path).open('rb') as stream:
        while block := stream.read(1024 * 1024):
            h.update(block)
    after = Path(path).stat()
    require((before.st_ino, before.st_size, before.st_mtime_ns) == (after.st_ino, after.st_size, after.st_mtime_ns), 'File changed while hashing')
    return h.hexdigest()


def read_json(path):
    path = Path(path)
    require(path.is_file(), f'Missing JSON file: {path}')
    require(path.stat().st_size <= MAX_JSON, 'JSON file exceeds size limit')
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            require(key not in obj, f'Duplicate JSON key: {key}')
            obj[key] = value
        return obj
    try:
        return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique,
                          parse_constant=lambda x: (_ for _ in ()).throw(WorkflowError('Nonfinite JSON number')))
    except (ValueError, UnicodeError) as exc:
        raise WorkflowError(f'Invalid JSON: {exc}') from exc


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.tmp-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(canonical(value) + b'\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        dfd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def text_field(value, label):
    require(isinstance(value, str) and bool(value.strip()), f'{label} must be a nonempty string')
    return value


def integer(value, label, minimum=0, maximum=1000000):
    require(type(value) is int and minimum <= value <= maximum, f'{label} must be an integer from {minimum} to {maximum}')
    return value


def identifier(value, label):
    require(isinstance(value, str) and bool(ID.fullmatch(value)), f'Invalid {label}')
    return value


def safe_relative(value, label, glob=False):
    text_field(value, label)
    require('\\' not in value and '\x00' not in value, f'Unsafe {label}')
    path = Path(value)
    require(not path.is_absolute() and '..' not in path.parts and value != '.', f'Unsafe {label}')
    require(not any(part in EXCLUDED for part in path.parts), f'Excluded directory in {label}')
    if not glob:
        require(not any(ch in value for ch in '*?['), f'Wildcard in {label}')
    return value


def validate_plan(plan):
    require(isinstance(plan, dict), 'Plan must be an object')
    require(type(plan.get('schema_version')) is int and plan['schema_version'] == 1, 'schema_version must be 1')
    require(plan.get('mode') in {'feature', 'migration', 'repair', 'audit', 'plan'}, 'Invalid mode')
    require(plan.get('approval') in {'delegated', 'milestone', 'checkpoint'}, 'Invalid approval policy')
    require(plan.get('environment') in {'local-isolated', 'read-only', 'staging', 'production'}, 'Invalid environment')
    if plan['environment'] == 'production':
        auth = plan.get('production_authorization')
        require(isinstance(auth, dict) and auth.get('allowed') is True and isinstance(auth.get('reason'), str)
                and auth['reason'].strip(), 'Production requires explicit production_authorization allowed and reason')
    requirements = plan.get('requirements')
    require(isinstance(requirements, list) and requirements, 'requirements must be a nonempty array')
    rids = set()
    for item in requirements:
        require(isinstance(item, dict), 'Requirement must be object')
        rid = identifier(item.get('id'), 'requirement ID')
        require(rid not in rids, 'Duplicate requirement ID')
        rids.add(rid)
        text_field(item.get('text'), 'requirement text')
    excluded = set()
    for item in plan.get('exclusions', []):
        require(isinstance(item, dict), 'Exclusion must be object')
        require(item.get('id') in rids, 'Exclusion references unknown requirement')
        text_field(item.get('reason'), 'exclusion reason')
        excluded.add(item['id'])
    checkpoints = plan.get('checkpoints')
    require(isinstance(checkpoints, list) and checkpoints, 'checkpoints must be nonempty array')
    cids, covered = set(), set()
    for cp in checkpoints:
        require(isinstance(cp, dict), 'Checkpoint must be object')
        cid = identifier(cp.get('id'), 'checkpoint ID')
        require(cid not in cids, 'Duplicate checkpoint ID')
        cids.add(cid)
        text_field(cp.get('title'), 'checkpoint title')
        require(isinstance(cp.get('covers'), list) and cp['covers'], 'covers must be nonempty array')
        require(all(isinstance(x, str) and x in rids for x in cp['covers']), 'covers references unknown requirement')
        covered.update(cp['covers'])
        require(isinstance(cp.get('depends_on'), list) and all(isinstance(x, str) for x in cp['depends_on']), 'depends_on must be array of IDs')
        require(len(set(cp['depends_on'])) == len(cp['depends_on']), 'Duplicate dependency')
        require(isinstance(cp.get('scope'), list) and cp['scope'], 'scope must be nonempty array')
        for pattern in cp['scope']:
            safe_relative(pattern, 'scope', glob=True)
        gates = cp.get('gates')
        require(isinstance(gates, dict) and gates, 'gates must be nonempty object')
        require(set(gates) <= {'behavior', 'review', 'ui'}, 'Unknown gate')
        for name, gate in gates.items():
            require(isinstance(gate, dict), 'Gate must be object')
            kind = gate.get('kind')
            if kind == 'not_applicable':
                text_field(gate.get('reason'), 'not_applicable reason')
                continue
            require(kind == {'behavior': 'command', 'review': 'review', 'ui': 'ui'}[name], f'Invalid {name} gate kind')
            if name == 'behavior':
                checks = gate.get('checks')
                require(isinstance(checks, list) and checks, 'checks must be nonempty array')
                checks_ids = set()
                for check in checks:
                    require(isinstance(check, dict), 'Check must be object')
                    checkid = identifier(check.get('id'), 'check ID')
                    require(checkid not in checks_ids, 'Duplicate check ID')
                    checks_ids.add(checkid)
                    argv = check.get('argv')
                    require(isinstance(argv, list) and argv and all(isinstance(x, str) and '\x00' not in x for x in argv)
                            and argv[0], 'argv must be nonempty string array')
                    require(check.get('parser') in {'unittest', 'json', 'exit'}, 'Unknown test parser')
                    integer(check.get('min_tests'), 'min_tests', 0)
                    if check['parser'] == 'exit':
                        require(check['min_tests'] == 0, 'exit parser cannot claim test counts: min_tests must be 0')
                    else:
                        require(check['min_tests'] >= 1, 'Test parsers require min_tests >= 1')
                    timeout = check.get('timeout_seconds')
                    require(type(timeout) in (int, float) and 0 < timeout <= 86400, 'Invalid timeout_seconds')
                    integer(check.get('max_attempts', 3), 'max_attempts', 1, 100)
            elif name == 'review':
                integer(gate.get('reviewers'), 'reviewers', 1, 2)
                axes = gate.get('axes', ['specification', 'standards'][:gate['reviewers']])
                require(isinstance(axes, list) and len(axes) == gate['reviewers'] and len(set(axes)) == len(axes)
                        and all(isinstance(x, str) and x for x in axes), 'review axes must be distinct and match reviewers')
            else:
                identity = gate.get('identity')
                require(isinstance(identity, dict), 'UI requires identity object')
                for key in ('fixture', 'language', 'reference', 'role', 'state'):
                    text_field(identity.get(key), f'UI identity {key}')
                vp = identity.get('viewport')
                require(isinstance(vp, list) and len(vp) == 2, 'viewport must be [width,height]')
                for value in vp:
                    integer(value, 'viewport size', 1, 20000)
    require(rids <= covered | excluded, 'Every requirement must be covered or explicitly excluded')
    graph = {cp['id']: cp['depends_on'] for cp in checkpoints}
    require(all(dep in cids for deps in graph.values() for dep in deps), 'Unknown checkpoint dependency')
    visiting, done = set(), set()
    def visit(cid):
        require(cid not in visiting, 'Checkpoint dependency cycle')
        if cid in done:
            return
        visiting.add(cid)
        for dep in graph[cid]:
            visit(dep)
        visiting.remove(cid)
        done.add(cid)
    for cid in graph:
        visit(cid)
    return copy.deepcopy(plan)


def project_identity(project):
    project = Path(project).resolve(strict=True)
    require(project.is_dir(), 'project must be directory')
    stat = project.stat()
    result = {'path': str(project), 'device': stat.st_dev, 'inode': stat.st_ino}
    try:
        git = subprocess.run(['git', '-C', str(project), 'rev-parse', '--show-toplevel', '--git-common-dir'],
                             capture_output=True, text=True, timeout=5)
        if git.returncode == 0:
            lines = git.stdout.splitlines()
            root = Path(lines[0]).resolve()
            common = Path(lines[1])
            if not common.is_absolute():
                common = project / common
            result.update(git_root=str(root), git_common_dir=str(common.resolve()))
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return result


def checkpoint_plan(state, cid):
    require(cid in state['checkpoints'], f'Unknown checkpoint: {cid}')
    return next(cp for cp in state['plan']['checkpoints'] if cp['id'] == cid)


def scope_patterns(state, cid):
    visited, result = set(), []
    def visit(name):
        if name in visited:
            return
        visited.add(name)
        cp = checkpoint_plan(state, name)
        result.extend(cp['scope'])
        for dep in cp['depends_on']:
            visit(dep)
    visit(cid)
    return sorted(set(result))


def source_manifest(state, cid):
    project = Path(state['project']['path'])
    require(project_identity(project) == state['project'], 'Project identity changed; cannot resume in a different project')
    patterns = scope_patterns(state, cid)
    files = {}
    for pattern in patterns:
        # Resolve the fixed prefix even when a wildcard has no matches.
        prefix = []
        for part in Path(pattern).parts:
            if any(c in part for c in '*?['):
                break
            prefix.append(part)
        candidate = project.joinpath(*prefix)
        require(candidate.resolve().is_relative_to(project), 'Scope follows a symlink outside project')
        for path in project.glob(pattern):
            relative = path.relative_to(project)
            if any(part in EXCLUDED for part in relative.parts):
                continue
            require(path.resolve().is_relative_to(project), f'Source symlink escapes project: {relative}')
            if path.is_dir():
                require(False, f'Scope matched a directory; use a file glob: {relative}')
            require(path.is_file(), f'Scope contains nonregular file: {relative}')
            files[relative.as_posix()] = {'sha256': file_hash(path), 'mode': path.stat().st_mode & 0o777}
    manifest = {'project': state['project'], 'patterns': patterns, 'files': files}
    return {'hash': digest(manifest), 'manifest': manifest}


def evidence_valid(state, evidence, source_hash):
    if evidence.get('source_hash') != source_hash or evidence.get('plan_hash') != state['plan_hash']:
        return False
    run = Path(state['_run'])
    for item in evidence.get('artifacts', []):
        try:
            path = run / item['path']
            if not path.resolve().is_relative_to(run) or not path.is_file() or file_hash(path) != item['sha256']:
                return False
        except (KeyError, OSError):
            return False
    return True


def gate_statuses(state, cid, source_hash):
    cp = checkpoint_plan(state, cid)
    recorded = state['checkpoints'][cid]
    result = {}
    for name, gate in cp['gates'].items():
        if gate['kind'] == 'not_applicable':
            result[name] = {'status': 'not_applicable', 'reason': gate['reason']}
            continue
        entries = [e for e in recorded['evidence'] if e['gate'] == name]
        current = [e for e in entries if evidence_valid(state, e, source_hash)]
        if name == 'behavior':
            latest = {}
            for entry in current:
                latest[entry['check_id']] = entry
            checks = {item['id']: latest.get(item['id'], {}).get('verdict', 'pending') for item in gate['checks']}
            passed = all(value == 'pass' for value in checks.values())
            status = 'pass' if passed else ('stale' if entries and not current else ('invalid' if 'invalid' in checks.values() else ('fail' if 'fail' in checks.values() else 'pending')))
            result[name] = {'status': status, 'checks': checks, 'reasons': {k: e.get('reason') for k, e in latest.items() if e.get('reason')}}
        elif name == 'review':
            latest = {}
            for entry in current:
                latest[entry['reviewer']] = entry
            axes = gate.get('axes', ['specification', 'standards'][:gate['reviewers']])
            selected = [entry for entry in latest.values() if entry['verdict'] == 'pass']
            passed = all(any(entry['axis'] == axis for entry in selected) for axis in axes)
            # One reviewer is not allowed to fill two independent axes.
            passed = passed and len(selected) >= gate['reviewers'] and all(e['verdict'] == 'pass' for e in latest.values())
            verdicts = [e['verdict'] for e in latest.values()]
            status = 'pass' if passed else ('stale' if entries and not current else ('invalid' if 'invalid' in verdicts else ('fail' if 'fail' in verdicts else 'pending')))
            result[name] = {'status': status,
                            'reviewers': [{'reviewer': e['reviewer'], 'axis': e['axis'], 'verdict': e['verdict']} for e in latest.values()]}
        else:
            latest = current[-1] if current else None
            result[name] = {'status': latest['verdict'] if latest else ('stale' if entries else 'pending')}
    return result


def public_status(state):
    result = {'engine_version': VERSION, 'run_id': state['run_id'], 'plan': state['plan'], 'base_commit': state.get('base_commit'), 'revision': state['revision'], 'plan_hash': state['plan_hash'],
              'run_status': state['run_status'], 'project': state['project'], 'mode': state['plan']['mode'],
              'approval': state['plan']['approval'], 'environment': state['plan']['environment'], 'checkpoints': {}}
    for cid, data in state['checkpoints'].items():
        source = source_manifest(state, cid)
        gates = gate_statuses(state, cid, source['hash'])
        status = data['status']
        current = data.get('proven_source') == source['hash'] and data.get('proven_plan') == state['plan_hash']
        if status in {'accepted', 'proven'} and (not current or any(g['status'] not in {'pass', 'not_applicable'} for g in gates.values())):
            status = 'verifying'
        result['checkpoints'][cid] = {'status': status, 'recorded_status': data['status'], 'source_hash': source['hash'],
                                     'source_files': list(source['manifest']['files']), 'implementer': data.get('implementer'),
                                     'gates': gates, 'evidence_count': len(data['evidence']),
                                     'attempts': data['attempts'], 'pending_commands': data['pending_commands']}
    # Propagate a stale dependency into accepted descendants even when a narrow glob was unchanged.
    changed = True
    while changed:
        changed = False
        for cp in state['plan']['checkpoints']:
            current = result['checkpoints'][cp['id']]
            if current['status'] in {'accepted', 'proven'} and any(result['checkpoints'][d]['status'] != 'accepted' for d in cp['depends_on']):
                current['status'] = 'verifying'
                changed = True
    if state.get('reason'):
        result['reason'] = state['reason']
    return result


class Journal:
    def __init__(self, run):
        self.run = Path(run).resolve()
        self.stream = None
        self.state = None
        self.last_hash = '0' * 64

    def __enter__(self):
        require(self.run.is_dir(), 'Run does not exist; initialize it first')
        lockpath = self.run / '.lock'
        require(not lockpath.is_symlink(), 'Lock cannot be symlink')
        self.stream = lockpath.open('a+b')
        fcntl.flock(self.stream, fcntl.LOCK_EX)
        self.load()
        return self

    def __exit__(self, *_):
        if self.stream:
            fcntl.flock(self.stream, fcntl.LOCK_UN)
            self.stream.close()

    def load(self):
        path = self.run / 'events.jsonl'
        require(path.is_file() and not path.is_symlink(), 'Missing or unsafe event journal')
        previous, revision, state = '0' * 64, 0, None
        with path.open('rb') as stream:
            for lineno, line in enumerate(stream, 1):
                require(line.endswith(b'\n'), 'Incomplete journal final line; use explicit recover command')
                try:
                    event = json.loads(line)
                except (ValueError, UnicodeError) as exc:
                    raise WorkflowError(f'Corrupt journal at line {lineno}') from exc
                require(isinstance(event, dict) and 'checksum' in event, f'Invalid journal line {lineno}')
                checksum = event.pop('checksum')
                require(checksum == digest(event), f'Journal checksum mismatch at line {lineno}')
                require(event.get('previous') == previous and event.get('revision') == revision + 1, 'Journal chain/revision mismatch')
                state = event.get('state')
                require(isinstance(state, dict) and state.get('revision') == event['revision'], 'Invalid journal state')
                previous, revision = checksum, event['revision']
        require(state is not None, 'Empty journal')
        validate_plan(state['plan'])
        require(state['plan_hash'] == digest(state['plan']), 'Journal plan hash mismatch')
        state['_run'] = str(self.run)
        self.state, self.last_hash = state, previous

    def expected(self, revision):
        if revision is not None:
            require(revision == self.state['revision'], 'Revision conflict; reload status before retrying')

    def append(self, action):
        self.state['revision'] += 1
        snapshot = {k: v for k, v in self.state.items() if k != '_run'}
        event = {'revision': self.state['revision'], 'time': now(), 'action': action,
                 'previous': self.last_hash, 'state': snapshot}
        event['checksum'] = digest(event)
        with (self.run / 'events.jsonl').open('ab') as stream:
            stream.write(canonical(event) + b'\n')
            stream.flush()
            os.fsync(stream.fileno())
        self.last_hash = event['checksum']
        atomic_json(self.run / 'state.json', snapshot)


def active(state):
    require(state['run_status'] == 'active', f'Run is {state["run_status"]}; operation refused')


def stage_open(state, cid):
    active(state)
    status = public_status(state)
    cp = checkpoint_plan(state, cid)
    require(state['plan']['mode'] != 'plan', 'Plan mode cannot execute or accept checkpoints')
    require(all(status['checkpoints'][dep]['status'] == 'accepted' for dep in cp['depends_on']), 'Dependencies must be currently accepted')
    return cp


def initialized_checkpoint():
    return {'status': 'ready', 'evidence': [], 'attempts': {}, 'tokens': {}, 'pending_commands': {}, 'implementer': None}


def init(args):
    plan = validate_plan(read_json(args.plan))
    project = Path(args.project).resolve(strict=True)
    run = Path(args.run).resolve()
    require(not run.is_relative_to(project), 'Run directory must be outside project source')
    require(not run.exists() or not any(run.iterdir()), 'Run directory already contains files')
    identity = project_identity(project)
    base_commit = None
    try:
        git_head = subprocess.run(['git', '-C', str(project), 'rev-parse', 'HEAD'], capture_output=True, text=True, timeout=5)
        if git_head.returncode == 0:
            base_commit = git_head.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    state = {'schema_version': 1, 'revision': 0, 'run_id': uuid.uuid4().hex, 'project': identity,
             'plan': plan, 'plan_hash': digest(plan), 'base_commit': base_commit, 'run_status': 'active',
             'checkpoints': {cp['id']: initialized_checkpoint() for cp in plan['checkpoints']}}
    state['_run'] = str(run)
    for cp in plan['checkpoints']:
        source_manifest(state, cp['id'])
    run.mkdir(parents=True, exist_ok=True)
    (run / 'events.jsonl').touch(exist_ok=False)
    # Initial event uses the same format but cannot load an empty journal.
    with (run / '.lock').open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        journal = Journal(run)
        journal.state = state
        journal.append('init')
    return public_status(state)


def parse_results(parser, output, returncode, min_tests):
    counts = {'total': 0, 'failed': 0, 'skipped': 0}
    reason = None
    if parser == 'exit':
        pass
    elif parser == 'json':
        try:
            data = json.loads(output)
            require(isinstance(data, dict), 'Test JSON must be object')
            counts = {key: integer(data.get(key), key) for key in counts}
            require(counts['failed'] + counts['skipped'] <= counts['total'], 'Invalid test counts')
        except (ValueError, WorkflowError) as exc:
            reason = str(exc)
    else:
        matches = re.findall(r'Ran (\d+) tests? in [^\n]+', output)
        if len(matches) != 1:
            reason = 'Expected one unittest summary with executed test count'
        else:
            counts['total'] = int(matches[0])
            failed = re.search(r'FAILED\s*\(([^)]*)\)', output)
            skipped = re.search(r'(?:OK|FAILED)\s*\(([^)]*)\)', output)
            if failed:
                counts['failed'] = sum(int(x) for x in re.findall(r'(?:failures|errors)=(\d+)', failed[1]))
                if not counts['failed']:
                    counts['failed'] = 1
            if skipped:
                match = re.search(r'skipped=(\d+)', skipped[1])
                counts['skipped'] = int(match[1]) if match else 0
            if not re.search(r'\n(?:OK(?:\s*\([^)]*\))?|FAILED\s*\([^)]*\))\s*$', output):
                reason = 'Missing unittest final result'
    if counts['total'] < min_tests or counts['total'] - counts['skipped'] < min_tests:
        reason = 'Insufficient executed tests or all required tests skipped'
    verdict = 'pass' if returncode == 0 and counts['failed'] == 0 and reason is None else 'fail'
    return verdict, counts, reason


def artifact_directory(run):
    run = Path(run).resolve()
    directory = run / 'artifacts'
    require(not directory.is_symlink(), 'Artifact directory cannot be symlink')
    directory.mkdir(exist_ok=True)
    require(directory.resolve().is_relative_to(run), 'Artifact directory escapes run')
    return directory


def process_marker(pid):
    try:
        # starttime disambiguates PID reuse on Linux. Other POSIX systems use a PID check.
        stat = Path(f'/proc/{pid}/stat').read_text()
        return stat[stat.rfind(')') + 2:].split()[19]
    except (OSError, IndexError):
        return None


def process_alive(pid, marker):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    current = process_marker(pid)
    return marker is None or current is None or marker == current


def copy_artifact(run, path, prefix):
    path = Path(path)
    require(path.is_file(), f'Missing artifact: {path}')
    require(path.stat().st_size <= 128 * 1024 * 1024, 'Artifact too large')
    target = artifact_directory(run) / f'{prefix}-{uuid.uuid4().hex}{path.suffix[:12]}'
    data = path.read_bytes()
    target.write_bytes(data)
    return {'path': target.relative_to(run).as_posix(), 'sha256': file_hash(target), 'bytes': len(data)}


def check(args):
    token = args.token or uuid.uuid4().hex
    identifier(token, 'invocation token')
    with Journal(args.run) as journal:
        journal.expected(args.expected_revision)
        state = journal.state
        cp = stage_open(state, args.checkpoint)
        data = state['checkpoints'][args.checkpoint]
        require(data['status'] in {'implementing', 'verifying', 'proven', 'accepted'}, 'Start checkpoint before checking')
        require(not data['pending_commands'], 'A command is already running or interrupted; resume/recover it first')
        gate = cp['gates'].get('behavior')
        require(gate and gate['kind'] == 'command', 'Checkpoint has no behavior command gate')
        command = next((x for x in gate['checks'] if x['id'] == args.check), None)
        require(command is not None, 'Unknown planned check')
        source = source_manifest(state, args.checkpoint)
        existing = data['tokens'].get(token)
        if existing:
            require(existing['check_id'] == args.check and existing['source_hash'] == source['hash']
                    and existing['plan_hash'] == state['plan_hash'], 'Invocation token belongs to a different command/source/plan')
            require(existing['status'] == 'finished', 'Invocation token was interrupted; use a new token after resume')
            return {'replayed': True, 'evidence': existing['evidence'], 'revision': state['revision']}
        attempt_key = digest({'source': source['hash'], 'plan': state['plan_hash'], 'check': args.check})
        attempts = data['attempts'].get(attempt_key, 0)
        require(attempts < command.get('max_attempts', 3), 'Retry limit reached for this source and check; revise approach or plan')
        data['attempts'][attempt_key] = attempts + 1
        data['tokens'][token] = {'status': 'running', 'check_id': args.check, 'source_hash': source['hash'], 'plan_hash': state['plan_hash']}
        data['pending_commands'][token] = {'check_id': args.check, 'started': now(), 'engine_pid': os.getpid(), 'engine_marker': process_marker(os.getpid())}
        data['status'] = 'verifying'
        journal.append('check_started')
        run = journal.run
        project = state['project']['path']
        plan_hash = state['plan_hash']
    started = time.monotonic()
    reason, process, returncode = None, None, None
    artifact_dir = artifact_directory(run)
    logfile = artifact_dir / f'check-{token}.log'
    require(not logfile.exists() and not logfile.is_symlink(), 'Command log already exists; refusing overwrite')
    try:
        process = subprocess.Popen(command['argv'], cwd=project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   start_new_session=True, stdin=subprocess.DEVNULL)
        output_bytes = bytearray()
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while process.poll() is None:
                elapsed = time.monotonic() - started
                with Journal(run) as journal:
                    if journal.state['run_status'] != 'active':
                        reason = f'Run {journal.state["run_status"]}'
                if elapsed >= command['timeout_seconds']:
                    reason = 'Command timed out'
                for key, _ in selector.select(timeout=0.05):
                    block = os.read(key.fileobj.fileno(), 65536)
                    if block:
                        available = MAX_LOG - len(output_bytes)
                        output_bytes.extend(block[:available])
                        if len(block) > available:
                            reason = 'Command output limit exceeded'
                    else:
                        selector.unregister(key.fileobj)
                if reason:
                    terminate_group(process)
                    break
            returncode = process.wait()
            # Commands are checks, so their process groups cannot own persistent services.
            terminate_group(process)
            # Drain buffered output without allowing an escaped daemon to keep us waiting.
            for _ in range(80):
                events = selector.select(timeout=0)
                if not events:
                    break
                for key, _ in events:
                    block = os.read(key.fileobj.fileno(), 65536)
                    if not block:
                        selector.unregister(key.fileobj)
                        continue
                    available = MAX_LOG - len(output_bytes)
                    output_bytes.extend(block[:available])
                    if len(block) > available:
                        reason = 'Command output limit exceeded'
            process.stdout.close()
        logfile.write_bytes(output_bytes)
    except KeyboardInterrupt:
        reason = 'User interrupted command'
        if process:
            terminate_group(process)
            returncode = process.wait()
        logfile.write_text(reason + '\n', encoding='utf-8')
    except (OSError, ValueError) as exc:
        reason = f'Cannot execute command: {exc}'
        logfile.write_text(reason + '\n', encoding='utf-8')
    output = logfile.read_text(encoding='utf-8', errors='replace')
    verdict, counts, parser_reason = parse_results(command['parser'], output, returncode, command['min_tests'])
    if reason:
        verdict = 'invalid'
    with Journal(run) as journal:
        state = journal.state
        data = state['checkpoints'][args.checkpoint]
        current = source_manifest(state, args.checkpoint)['hash']
        if current != source['hash'] or state['plan_hash'] != plan_hash:
            verdict, reason = 'invalid', 'Source or plan changed during command'
        evidence = {'id': uuid.uuid4().hex, 'gate': 'behavior', 'check_id': args.check, 'verdict': verdict,
                    'source_hash': source['hash'], 'plan_hash': plan_hash, 'time': now(),
                    'argv': command['argv'], 'cwd': project, 'environment': state['plan']['environment'],
                    'returncode': returncode, 'counts': counts, 'reason': reason or parser_reason,
                    'duration_seconds': round(time.monotonic() - started, 6), 'attempt': attempts + 1,
                    'artifacts': [{'path': logfile.relative_to(run).as_posix(), 'sha256': file_hash(logfile), 'bytes': logfile.stat().st_size}]}
        data['evidence'].append(evidence)
        data['tokens'][token]['status'] = 'finished'
        data['tokens'][token]['evidence'] = evidence
        data['pending_commands'].pop(token, None)
        if reason == 'User interrupted command':
            state['run_status'] = 'paused'
            state['reason'] = reason
        journal.append('check_finished')
        return {'replayed': False, 'token': token, 'evidence': evidence, 'revision': state['revision']}


def terminate_group(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    # Wait briefly and always send KILL to the group, including surviving grandchildren.
    time.sleep(0.15)
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def report(args, gate_name):
    report_path = Path(args.report).resolve(strict=True)
    content = read_json(report_path)
    require(isinstance(content, dict), 'Report must be object')
    with Journal(args.run) as journal:
        journal.expected(args.expected_revision)
        state = journal.state
        cp = stage_open(state, args.checkpoint)
        data = state['checkpoints'][args.checkpoint]
        require(data['status'] in {'implementing', 'verifying', 'proven', 'accepted'}, 'Start checkpoint before importing evidence')
        gate = cp['gates'].get(gate_name)
        require(gate and gate['kind'] == gate_name, f'No {gate_name} gate')
        source = source_manifest(state, args.checkpoint)
        require(content.get('source_hash') == source['hash'] and content.get('plan_hash') == state['plan_hash'], 'Report belongs to stale source or plan')
        reviewer = text_field(content.get('reviewer'), 'reviewer')
        require(reviewer != data['implementer'], 'Reviewer must differ from implementer')
        verdict = content.get('verdict')
        require(verdict in {'pass', 'fail', 'invalid'}, 'Invalid report verdict')
        artifacts = []
        copied = copy.deepcopy(content)
        if gate_name == 'review':
            axis = content.get('axis')
            require(axis in gate.get('axes', ['specification', 'standards'][:gate['reviewers']]), 'Unexpected review axis')
            findings = content.get('findings')
            require(isinstance(findings, list), 'Review requires findings array')
            fids = set()
            blocking = False
            for finding in findings:
                require(isinstance(finding, dict), 'Finding must be object')
                fid = identifier(finding.get('id'), 'finding ID')
                require(fid not in fids, 'Duplicate finding ID')
                fids.add(fid)
                require(finding.get('severity') in {'blocker', 'major', 'minor'}, 'Unknown finding severity')
                text_field(finding.get('evidence'), 'finding evidence')
                resolution = finding.get('resolution')
                require(resolution in {None, 'fixed', 'dismissed', 'deferred'}, 'Invalid finding resolution')
                if resolution:
                    text_field(finding.get('reason'), 'finding resolution reason')
                if finding['severity'] in {'blocker', 'major'} and resolution not in {'fixed', 'dismissed'}:
                    blocking = True
                if finding['severity'] == 'minor' and resolution not in {'fixed', 'dismissed'}:
                    policy = state['plan'].get('minor_deferral_policy')
                    if not (resolution == 'deferred' and isinstance(policy, str) and policy.strip()):
                        blocking = True
            require(not (verdict == 'pass' and blocking), 'Passing review contains unresolved findings')
            paths = content.get('artifacts', [])
            require(isinstance(paths, list), 'Review artifacts must be array')
        else:
            identity = content.get('identity')
            if identity != gate['identity']:
                verdict = 'invalid'
                copied['verdict'] = verdict
                copied['reason'] = 'UI identity mismatch'
            paths = content.get('artifacts')
            require(isinstance(paths, dict) and set(paths) == {'capture', 'reference'}, 'UI requires capture and reference artifact paths')
            paths = list(paths.values())
        for pathvalue in paths:
            safe_relative(pathvalue, 'report artifact')
            path = (report_path.parent / pathvalue).resolve(strict=True)
            require(path.is_relative_to(report_path.parent), 'Report artifact escapes report directory')
            artifacts.append(copy_artifact(journal.run, path, gate_name))
        require(gate_name != 'ui' or len(artifacts) == 2, 'UI requires two artifacts')
        tmp = journal.run / 'artifacts' / f'report-{uuid.uuid4().hex}.json'
        atomic_json(tmp, copied)
        artifacts.append({'path': tmp.relative_to(journal.run).as_posix(), 'sha256': file_hash(tmp), 'bytes': tmp.stat().st_size})
        evidence = {'id': uuid.uuid4().hex, 'gate': gate_name, 'verdict': verdict,
                    'source_hash': source['hash'], 'plan_hash': state['plan_hash'], 'time': now(),
                    'reviewer': reviewer, 'artifacts': artifacts, 'report': copied}
        if gate_name == 'review':
            evidence['axis'] = content['axis']
        data['evidence'].append(evidence)
        data['status'] = 'verifying'
        journal.append(f'{gate_name}_imported')
        return {'evidence': evidence, 'revision': state['revision']}


def mutation(args):
    with Journal(args.run) as journal:
        journal.expected(args.expected_revision)
        state = journal.state
        cmd = args.command
        if cmd in {'pause', 'cancel'}:
            require(state['run_status'] != 'cancelled', 'Run already cancelled')
            state['run_status'] = 'paused' if cmd == 'pause' else 'cancelled'
            state['reason'] = args.reason or ('User pause' if cmd == 'pause' else 'User cancellation')
        elif cmd == 'resume':
            require(state['run_status'] == 'paused', 'Only paused runs can resume')
            for cid, cp in state['checkpoints'].items():
                source_manifest(state, cid)
                for token, pending in cp['pending_commands'].items():
                    pid = pending.get('engine_pid')
                    require(pid is None or not process_alive(pid, pending.get('engine_marker')), 'Paused command is still stopping; wait for its engine process before resuming')
                    cp['tokens'][token]['status'] = 'interrupted'
                cp['pending_commands'] = {}
            state['run_status'] = 'active'
            state.pop('reason', None)
        elif cmd == 'revise':
            active(state)
            require(not any(cp['pending_commands'] for cp in state['checkpoints'].values()), 'Cannot revise while command pending')
            plan = validate_plan(read_json(args.plan))
            require(plan['mode'] == state['plan']['mode'], 'A revised run must keep mode; create a new run to change mode')
            state['plan'], state['plan_hash'] = plan, digest(plan)
            state['checkpoints'] = {cp['id']: initialized_checkpoint() for cp in plan['checkpoints']}
            for cp in plan['checkpoints']:
                source_manifest(state, cp['id'])
        else:
            cid = args.checkpoint
            cp = stage_open(state, cid)
            data = state['checkpoints'][cid]
            require(not data['pending_commands'], 'Command pending; stop or resume it before transition')
            if cmd == 'start':
                actor = text_field(args.actor, 'actor')
                require(data['status'] in {'ready', 'implementing', 'verifying', 'proven', 'accepted'}, 'Invalid start state')
                if data['implementer'] is not None:
                    require(actor == data['implementer'], 'Implementer cannot silently change during checkpoint')
                data['implementer'] = actor
                data['status'] = 'implementing'
            elif cmd == 'prove':
                require(data['status'] in {'implementing', 'verifying', 'proven', 'accepted'}, 'Checkpoint not started')
                status = public_status(state)['checkpoints'][cid]
                require(all(g['status'] in {'pass', 'not_applicable'} for g in status['gates'].values()), 'Required gates are missing, failed, invalid, or stale')
                data['status'] = 'proven'
                data['proven_source'] = status['source_hash']
                data['proven_plan'] = state['plan_hash']
            elif cmd == 'accept':
                require(public_status(state)['checkpoints'][cid]['status'] == 'proven', 'Checkpoint must be currently proven before accept')
                if state['plan']['approval'] != 'delegated':
                    text_field(args.approval_note, 'approval-note recording user authorization')
                data['status'] = 'accepted'
                data['approval_note'] = args.approval_note or 'Delegated plan policy'
        journal.append(cmd)
        return public_status(state)


def export(args):
    with Journal(args.run) as journal:
        result = public_status(journal.state)
        atomic_json(journal.run / 'status.json', result)
        lines = ['# Resume checkpoint workflow', '', f'Run: {journal.state["run_id"]}',
                 f'Project: {result["project"]["path"]}', f'Run status: {result["run_status"]}',
                 f'Plan hash: {result["plan_hash"]}', f'Revision: {result["revision"]}', '',
                 '## Checkpoints', '']
        for cp in journal.state['plan']['checkpoints']:
            status = result['checkpoints'][cp['id']]
            lines.append(f'- {cp["id"]}: {cp["title"]}, {status["status"]}, source {status["source_hash"]}')
            for name, gate in status['gates'].items():
                lines.append(f'  - {name}: {gate["status"]}')
        lines.extend(['', '## Next action', '', 'Reload status, honor paused/cancelled state, and work on the first checkpoint with accepted dependencies.',
                      'Do not replay a completed command token. Source and plan changes invalidate prior evidence.',
                      '', 'Reviewer identity and authorization notes are local assertions, not authenticated signatures.',
                      'Checks are executable planned commands; the engine is not a filesystem or network sandbox.', ''])
        (journal.run / 'resume.md').write_text('\n'.join(lines), encoding='utf-8')
        return {'status': result, 'files': [str(journal.run / 'status.json'), str(journal.run / 'resume.md')]}


def recover(args):
    run = Path(args.run).resolve(strict=True)
    require(args.truncate_final_line, 'Recovery requires --truncate-final-line')
    lockpath = run / '.lock'
    require(not lockpath.is_symlink(), 'Unsafe lock')
    with lockpath.open('a+b') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        path = run / 'events.jsonl'
        require(not path.is_symlink(), 'Unsafe journal')
        payload = path.read_bytes()
        require(payload and not payload.endswith(b'\n'), 'Recovery only permits an incomplete final line')
        cut = payload.rfind(b'\n') + 1
        require(cut > 0, 'No complete journal record to recover')
        previous, revision = '0' * 64, 0
        recovered_state = None
        for line in payload[:cut].splitlines():
            try:
                event = json.loads(line)
            except (ValueError, UnicodeError) as exc:
                raise WorkflowError('Cannot recover a corrupt complete journal record') from exc
            require(isinstance(event, dict) and 'checksum' in event, 'Invalid complete journal record')
            checksum = event.pop('checksum')
            require(checksum == digest(event) and event.get('previous') == previous and event.get('revision') == revision + 1, 'Cannot recover a corrupt complete journal chain')
            recovered_state = event.get('state')
            require(isinstance(recovered_state, dict) and recovered_state.get('revision') == event['revision'], 'Invalid recovered journal state')
            previous, revision = checksum, event['revision']
        require(args.expected_revision is None or args.expected_revision == revision, 'Revision conflict; recovery refused before changing journal')
        validate_plan(recovered_state['plan'])
        require(recovered_state['plan_hash'] == digest(recovered_state['plan']), 'Recovered plan hash mismatch')
        backup = run / f'corrupt-tail-{uuid.uuid4().hex}.bin'
        backup.write_bytes(payload[cut:])
        with path.open('r+b') as journalfile:
            journalfile.truncate(cut)
            journalfile.flush()
            os.fsync(journalfile.fileno())
        journal = Journal(run)
        journal.load()
        journal.expected(args.expected_revision)
        journal.state['run_status'] = 'paused'
        journal.state['reason'] = 'Recovered incomplete journal tail; review before resuming'
        journal.append('recover_final_line')
        return public_status(journal.state)


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('--version', action='version', version=VERSION)
    commands = result.add_subparsers(dest='command', required=True)
    for cmd in ('init', 'status', 'start', 'check', 'review', 'ui', 'prove', 'accept', 'pause', 'resume', 'cancel', 'revise', 'export', 'recover'):
        p = commands.add_parser(cmd)
        p.add_argument('--run', required=True)
        if cmd not in {'init', 'status', 'export'}:
            p.add_argument('--expected-revision', type=int)
        if cmd in {'start', 'check', 'review', 'ui', 'prove', 'accept'}:
            p.add_argument('--checkpoint', required=True)
        if cmd == 'init':
            p.add_argument('--project', required=True)
            p.add_argument('--plan', required=True)
        if cmd == 'revise':
            p.add_argument('--plan', required=True)
        if cmd == 'start':
            p.add_argument('--actor', required=True)
        if cmd == 'check':
            p.add_argument('--check', required=True)
            p.add_argument('--token')
        if cmd in {'review', 'ui'}:
            p.add_argument('--report', required=True)
        if cmd == 'accept':
            p.add_argument('--approval-note')
        if cmd in {'pause', 'resume', 'cancel'}:
            p.add_argument('--reason')
        if cmd == 'recover':
            p.add_argument('--truncate-final-line', action='store_true')
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == 'init':
            result = init(args)
        elif args.command == 'status':
            with Journal(args.run) as journal:
                result = public_status(journal.state)
        elif args.command == 'check':
            result = check(args)
        elif args.command in {'review', 'ui'}:
            result = report(args, args.command)
        elif args.command == 'export':
            result = export(args)
        elif args.command == 'recover':
            result = recover(args)
        else:
            result = mutation(args)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
        if args.command == 'check' and result['evidence']['verdict'] != 'pass':
            return 1
        return 0
    except (WorkflowError, OSError, KeyError, TypeError, ValueError, RecursionError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
