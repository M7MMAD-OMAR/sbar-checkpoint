"""Independent host compatibility and isolated installation contracts."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills' / 'sbar-checkpoint' / 'scripts'
SOURCE = SCRIPTS.parent
ROOT_VARIABLES = {
    'codex': 'CODEX_HOME',
    'claude': 'CLAUDE_CONFIG_DIR',
    'hermes': 'HERMES_HOME',
}
USER_FOLDERS = {'codex': '.codex', 'claude': '.claude', 'hermes': '.hermes'}
PROJECT_FOLDERS = {'codex': '.agents', 'claude': '.claude', 'hermes': '.hermes'}
SLUG = 'sbar-checkpoint'


def hosts_module():
    spec = importlib.util.spec_from_file_location('checkpoint_hosts_under_test', SCRIPTS / 'hosts.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def isolated_env(home):
    env = os.environ.copy()
    for variable in ROOT_VARIABLES.values():
        env.pop(variable, None)
    env['HOME'] = str(home)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return env


class HostPathTests(unittest.TestCase):
    def test_user_defaults_for_each_host(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            for host, folder in USER_FOLDERS.items():
                with self.subTest(host=host):
                    actual = hosts_module().resolve_destination(host, home=home, environ={})
                    self.assertEqual(Path(actual), home / folder / 'skills' / SLUG)

    def test_explicit_home_does_not_inherit_machine_host_overrides(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            overrides = {variable: str(home / 'wrong' / host) for host, variable in ROOT_VARIABLES.items()}
            with mock.patch.dict(os.environ, overrides):
                for host, folder in USER_FOLDERS.items():
                    with self.subTest(host=host):
                        self.assertEqual(Path(hosts_module().resolve_destination(host, home=home)), home / folder / 'skills' / SLUG)

    def test_absolute_environment_roots_are_respected(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            for host, variable in ROOT_VARIABLES.items():
                with self.subTest(host=host):
                    selected = home / 'custom' / host
                    result = hosts_module().resolve_destination(host, home=home, environ={variable: str(selected)})
                    self.assertEqual(Path(result), selected / 'skills' / SLUG)

    def test_tilde_environment_roots_use_explicit_fixture_home(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            for host, variable in ROOT_VARIABLES.items():
                with self.subTest(host=host):
                    result = hosts_module().resolve_destination(host, home=home, environ={variable: '~/custom/' + host})
                    self.assertEqual(Path(result), home / 'custom' / host / 'skills' / SLUG)

    def test_relative_environment_roots_reject_for_each_host(self):
        with tempfile.TemporaryDirectory() as directory:
            for host, variable in ROOT_VARIABLES.items():
                with self.subTest(host=host):
                    with self.assertRaises(ValueError):
                        hosts_module().resolve_destination(host, home=Path(directory), environ={variable: 'relative/config'})

    def test_project_scope_ignores_user_root_overrides(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / 'project'
            project.mkdir()
            overrides = {variable: str(root / 'unwanted' / host) for host, variable in ROOT_VARIABLES.items()}
            for host, folder in PROJECT_FOLDERS.items():
                with self.subTest(host=host):
                    result = hosts_module().resolve_destination(host, scope='project', project=project, home=root, environ=overrides)
                    self.assertEqual(Path(result), project / folder / 'skills' / SLUG)
            self.assertFalse((root / 'unwanted').exists())

    def test_project_scope_requires_an_existing_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file_path = root / 'file'
            file_path.write_text('keep')
            for project in (None, root / 'missing', file_path):
                with self.subTest(project=project):
                    with self.assertRaises((ValueError, OSError)):
                        hosts_module().resolve_destination('claude', scope='project', project=project, home=root, environ={})
            self.assertEqual(file_path.read_text(), 'keep')
            self.assertFalse((root / 'missing').exists())

    def test_all_host_paths_cli_is_read_only_and_uses_supplied_home(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            env = isolated_env(home)
            for host, variable in ROOT_VARIABLES.items():
                env[variable] = str(home / 'wrong' / host)
            proc = subprocess.run([sys.executable, str(SCRIPTS / 'hosts.py'), 'paths', '--host', 'all', '--home', str(home)], env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            data = json.loads(proc.stdout)
            self.assertEqual(set(data), set(USER_FOLDERS))
            for host, folder in USER_FOLDERS.items():
                self.assertEqual(Path(data[host]['destination']), home / folder / 'skills' / SLUG)
            self.assertEqual(data['codex']['invoke'], '$sbar-checkpoint')
            self.assertEqual(data['claude']['invoke'], '/sbar-checkpoint')
            self.assertEqual(data['hermes']['invoke'], '/sbar-checkpoint')
            self.assertEqual(list(home.iterdir()), [])

    def test_unknown_host_or_scope_rejects(self):
        with tempfile.TemporaryDirectory() as directory:
            for kwargs in ({'host': 'unsupported'}, {'host': 'codex', 'scope': 'global'}):
                with self.subTest(kwargs=kwargs):
                    with self.assertRaises(ValueError):
                        hosts_module().resolve_destination(home=Path(directory), environ={}, **kwargs)



class HostInstallTests(unittest.TestCase):
    def invoke(self, home, *args, env=None):
        return subprocess.run([sys.executable, str(SCRIPTS / 'install.py'), '--source', str(SOURCE), *map(str, args)], env=env or isolated_env(home), capture_output=True, text=True, timeout=30)

    def test_all_three_user_installs_contain_runnable_engine(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for host, folder in USER_FOLDERS.items():
                with self.subTest(host=host):
                    proc = self.invoke(root, '--host', host)
                    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                    target = root / folder / 'skills' / SLUG
                    self.assertTrue((target / 'SKILL.md').is_file())
                    self.assertTrue((target / 'scripts' / 'hosts.py').is_file())
                    self.assertEqual((target / 'scripts' / 'workflow.py').read_bytes(), (SCRIPTS / 'workflow.py').read_bytes())
                    smoke = subprocess.run([sys.executable, str(target / 'scripts' / 'workflow.py'), '--help'], env=isolated_env(root), capture_output=True, text=True, timeout=15)
                    self.assertEqual(smoke.returncode, 0, smoke.stderr)
                    self.assertIn('checkpoint', smoke.stdout.lower())

    def test_all_three_project_installs_respect_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / 'project'
            project.mkdir()
            env = isolated_env(root)
            for host, variable in ROOT_VARIABLES.items():
                env[variable] = str(root / 'unwanted' / host)
            for host, folder in PROJECT_FOLDERS.items():
                with self.subTest(host=host):
                    proc = self.invoke(root, '--host', host, '--scope', 'project', '--project', project, env=env)
                    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                    self.assertTrue((project / folder / 'skills' / SLUG / 'SKILL.md').is_file())
            self.assertFalse((root / 'unwanted').exists())

    def test_relative_override_fails_without_installing_in_cwd(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for host, variable in ROOT_VARIABLES.items():
                with self.subTest(host=host):
                    env = isolated_env(root)
                    env[variable] = 'relative-root'
                    proc = self.invoke(root, '--host', host, env=env)
                    self.assertNotEqual(proc.returncode, 0)
                    self.assertNotIn('Traceback', proc.stdout + proc.stderr)
                    self.assertFalse((root / USER_FOLDERS[host]).exists())

    def test_host_destination_collision_preserves_existing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for host, folder in USER_FOLDERS.items():
                with self.subTest(host=host):
                    target = root / folder / 'skills' / SLUG
                    target.mkdir(parents=True)
                    marker = target / 'owner-note.txt'
                    marker.write_bytes(b'user-owned bytes\x00')
                    proc = self.invoke(root, '--host', host)
                    self.assertNotEqual(proc.returncode, 0)
                    self.assertEqual(marker.read_bytes(), b'user-owned bytes\x00')
                    self.assertEqual([item.name for item in target.iterdir()], ['owner-note.txt'])

    def test_broken_native_skill_symlink_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for host, folder in USER_FOLDERS.items():
                with self.subTest(host=host):
                    target = root / folder / 'skills' / SLUG
                    target.parent.mkdir(parents=True)
                    target.symlink_to(root / 'missing' / host)
                    proc = self.invoke(root, '--host', host)
                    self.assertNotEqual(proc.returncode, 0)
                    self.assertTrue(target.is_symlink())
                    self.assertEqual(os.readlink(target), str(root / 'missing' / host))
                    self.assertFalse((root / 'missing').exists())

    def test_explicit_host_and_destination_are_mutually_exclusive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proc = self.invoke(root, '--host', 'hermes', '--destination', root / 'custom')
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse((root / 'custom').exists())
            self.assertFalse((root / '.hermes').exists())

    def test_project_scope_missing_project_fails_without_side_effect(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proc = self.invoke(root, '--host', 'codex', '--scope', 'project')
            self.assertNotEqual(proc.returncode, 0)
            self.assertEqual(list(root.iterdir()), [])

    def test_user_override_cli_selects_only_requested_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for host, variable in ROOT_VARIABLES.items():
                with self.subTest(host=host):
                    custom = root / 'custom' / host
                    env = isolated_env(root)
                    env[variable] = str(custom)
                    proc = self.invoke(root, '--host', host, env=env)
                    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                    self.assertTrue((custom / 'skills' / SLUG / 'SKILL.md').is_file())
                    self.assertFalse((root / USER_FOLDERS[host]).exists())


class HostDoctorTests(unittest.TestCase):
    def test_presence_does_not_become_a_host_verification_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for host, folder in USER_FOLDERS.items():
                with self.subTest(host=host):
                    target = root / folder / 'skills' / SLUG
                    command = [sys.executable, str(SCRIPTS / 'doctor.py'), '--host', host, '--declare-agents']
                    absent = subprocess.run(command, env=isolated_env(root), capture_output=True, text=True, timeout=15)
                    self.assertEqual(absent.returncode, 0, absent.stderr)
                    data = json.loads(absent.stdout)
                    self.assertFalse(data['native_skill_file_observed'])
                    self.assertEqual(Path(data['native_skill_directory']), target)
                    target.mkdir(parents=True)
                    (target / 'SKILL.md').write_text('---\nname: sbar-checkpoint\ndescription: fixture\n---\n')
                    present = subprocess.run(command, env=isolated_env(root), capture_output=True, text=True, timeout=15)
                    self.assertEqual(present.returncode, 0, present.stderr)
                    data = json.loads(present.stdout)
                    self.assertTrue(data['native_skill_file_observed'])
                    self.assertFalse(data['host_discovery_verified'])
                    self.assertFalse(data['agent_review_verified'])
                    self.assertTrue(data['host_capabilities_declared_not_verified']['independent_agents'])
                    self.assertFalse(data['network_or_services_started'])
                    self.assertFalse(data['global_hooks_installed'])


class ReviewPacketTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / 'project'
        self.project.mkdir()
        (self.project / 'app.py').write_text('result = 1\n')
        self.run = self.root / 'run'
        self.plan_path = self.root / 'plan.json'
        self.plan_path.write_bytes((SOURCE / 'references' / 'example-plan.json').read_bytes())
        self.engine('init', '--run', self.run, '--project', self.project, '--plan', self.plan_path)
        self.engine('start', '--run', self.run, '--checkpoint', 'core', '--actor', 'implementer')

    def engine(self, *args):
        proc = subprocess.run([sys.executable, str(SCRIPTS / 'workflow.py'), *map(str, args)], env=isolated_env(self.root), capture_output=True, text=True, timeout=15)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return json.loads(proc.stdout)

    def packet_cli(self, output, checkpoint='core', reviewer='fresh-reviewer', axis='specification'):
        return subprocess.run([sys.executable, str(SCRIPTS / 'hosts.py'), 'review-packet', '--run', str(self.run), '--checkpoint', checkpoint, '--reviewer', reviewer, '--axis', axis, '--output', str(output)], env=isolated_env(self.root), capture_output=True, text=True, timeout=15)

    def bytes_in_run(self):
        return {str(path.relative_to(self.run)): path.read_bytes() for path in self.run.rglob('*') if path.is_file()}

    def test_packet_has_real_contract_and_no_actual_verdict(self):
        status = self.engine('status', '--run', self.run)
        output = self.root / 'packet.json'
        proc = self.packet_cli(output)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        packet = json.loads(output.read_text())
        self.assertEqual(packet['purpose'], 'independent-review-input')
        self.assertEqual(packet['project'], str(self.project))
        self.assertEqual(packet['plan_hash'], status['plan_hash'])
        self.assertEqual(packet['source_hash'], status['checkpoints']['core']['source_hash'])
        self.assertEqual(packet['checkpoint'], status['plan']['checkpoints'][0])
        self.assertEqual(packet['requirements'], status['plan']['requirements'])
        self.assertEqual(packet['reviewer'], 'fresh-reviewer')
        self.assertEqual(packet['axis'], 'specification')
        self.assertEqual(packet['output_contract']['verdict'], 'REPLACE_WITH_ACTUAL_VERDICT')
        self.assertEqual(packet['output_contract']['findings'], [])
        self.assertNotIn('checkpoints', packet)
        self.assertNotIn('run_status', packet)
        self.assertNotIn('reviews', packet)

    def test_prior_review_results_and_implementer_defense_are_not_in_packet(self):
        status = self.engine('status', '--run', self.run)
        review = self.root / 'earlier-review.json'
        review.write_text(json.dumps({'reviewer': 'prior-reviewer-secret', 'axis': 'specification', 'source_hash': status['checkpoints']['core']['source_hash'], 'plan_hash': status['plan_hash'], 'verdict': 'pass', 'findings': []}))
        self.engine('review', '--run', self.run, '--checkpoint', 'core', '--report', review)
        (self.run / 'implementer-defense.txt').write_text('SECRET_IMPLEMENTER_ARGUMENT_481')
        packet = hosts_module().review_packet(self.run, 'core', 'fresh-reviewer', 'specification')
        raw = json.dumps(packet)
        self.assertNotIn('prior-reviewer-secret', raw)
        self.assertNotIn('SECRET_IMPLEMENTER_ARGUMENT_481', raw)
        self.assertNotIn('"verdict": "pass"', raw)

    def test_packet_creation_does_not_mutate_engine_run(self):
        before = self.bytes_in_run()
        hosts_module().review_packet(self.run, 'core', 'fresh-reviewer', 'specification')
        self.assertEqual(before, self.bytes_in_run())

    def test_review_state_refreshes_hashes_without_exposing_prior_verdicts(self):
        status = self.engine('status', '--run', self.run)
        review = self.root / 'earlier-failed-review.json'
        review.write_text(json.dumps({
            'reviewer': 'PRIOR_REVIEWER_MARKER_611', 'axis': 'specification',
            'source_hash': status['checkpoints']['core']['source_hash'],
            'plan_hash': status['plan_hash'], 'verdict': 'fail',
            'findings': [{'id': 'prior-finding', 'severity': 'major',
                          'evidence': 'PRIOR_FINDING_MARKER_611'}],
        }))
        self.engine('review', '--run', self.run, '--checkpoint', 'core', '--report', review)
        current = self.engine('status', '--run', self.run)
        self.assertEqual(current['checkpoints']['core']['gates']['review']['status'], 'fail')
        before = self.bytes_in_run()

        def refresh():
            proc = subprocess.run([
                sys.executable, str(SCRIPTS / 'hosts.py'), 'review-state',
                '--run', str(self.run), '--checkpoint', 'core',
            ], env=isolated_env(self.root), capture_output=True, text=True, timeout=15)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(proc.stderr, '')
            data = json.loads(proc.stdout)
            self.assertEqual(set(data), {'run', 'project', 'revision_at_dispatch',
                                         'plan_hash', 'source_hash'})
            self.assertNotIn('PRIOR_REVIEWER_MARKER_611', proc.stdout)
            self.assertNotIn('PRIOR_FINDING_MARKER_611', proc.stdout)
            self.assertEqual(before, self.bytes_in_run())
            return data

        first = refresh()
        self.assertEqual(first['plan_hash'], current['plan_hash'])
        self.assertEqual(first['source_hash'], current['checkpoints']['core']['source_hash'])
        (self.project / 'app.py').write_text('result = 42\n')
        second = refresh()
        self.assertNotEqual(first['source_hash'], second['source_hash'])
        self.assertEqual(first['plan_hash'], second['plan_hash'])
        self.assertEqual(first['revision_at_dispatch'], second['revision_at_dispatch'])

    def test_changed_source_is_captured_without_altering_recorded_history(self):
        first = hosts_module().review_packet(self.run, 'core', 'fresh-reviewer', 'specification')
        (self.project / 'app.py').write_text('result = 2\n')
        before = self.bytes_in_run()
        second = hosts_module().review_packet(self.run, 'core', 'fresh-reviewer', 'specification')
        self.assertNotEqual(first['source_hash'], second['source_hash'])
        self.assertEqual(first['plan_hash'], second['plan_hash'])
        self.assertEqual(first['revision_at_dispatch'], second['revision_at_dispatch'])
        self.assertEqual(before, self.bytes_in_run())

    def test_existing_packet_output_is_not_overwritten(self):
        output = self.root / 'existing.json'
        output.write_bytes(b'owner packet\x00')
        before = self.bytes_in_run()
        proc = self.packet_cli(output)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(output.read_bytes(), b'owner packet\x00')
        self.assertEqual(before, self.bytes_in_run())

    def test_existing_broken_packet_symlink_is_not_replaced(self):
        output = self.root / 'broken.json'
        missing = self.root / 'missing.json'
        output.symlink_to(missing)
        proc = self.packet_cli(output)
        self.assertNotEqual(proc.returncode, 0)
        self.assertTrue(output.is_symlink())
        self.assertEqual(os.readlink(output), str(missing))
        self.assertFalse(missing.exists())

    def test_packet_rejects_output_in_project_or_run(self):
        for output in (self.project / 'packet.json', self.run / 'packet.json'):
            with self.subTest(output=output):
                proc = self.packet_cli(output)
                self.assertNotEqual(proc.returncode, 0)
                self.assertFalse(output.exists())

    def test_packet_rejects_symlinked_parent_into_project(self):
        alias = self.root / 'alias'
        alias.symlink_to(self.project, target_is_directory=True)
        proc = self.packet_cli(alias / 'packet.json')
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse((self.project / 'packet.json').exists())

    def test_unknown_checkpoint_and_empty_actor_fail_without_output(self):
        for kwargs in ({'checkpoint': 'unknown'}, {'reviewer': ' '}, {'axis': ' '}):
            with self.subTest(kwargs=kwargs):
                output = self.root / 'invalid.json'
                proc = self.packet_cli(output, **kwargs)
                self.assertNotEqual(proc.returncode, 0)
                self.assertFalse(output.exists())
                self.assertNotIn('Traceback', proc.stdout + proc.stderr)


if __name__ == '__main__':
    unittest.main()
