"""Observable contracts for the portable skill's non-engine helpers."""
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from contextlib import redirect_stdout

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills' / 'sbar-checkpoint' / 'scripts'


def module(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


class ToolTests(unittest.TestCase):
    def test_english_viewer_preserves_and_escapes_multilingual_user_content(self):
        report = module('viewer').render({'plan_hash': '<script>bad()</script>',
            'run_status': 'paused', 'plan': {'requirements': [{'id': 'R1',
            'text': 'دليل قديم <img src=x onerror=alert(1)>'}], 'checkpoints': []},
            'checkpoints': {}})
        self.assertIn('lang="en" dir="ltr"', report)
        self.assertIn('دليل قديم', report)
        self.assertIn('Checkpoint evidence report', report)
        self.assertNotIn('<script>', report)
        self.assertNotIn('<img src=x', report)
        self.assertIn('&lt;img', report)

    def test_viewer_escapes_untrusted_status(self):
        result = module('viewer').render({'plan_hash': '<script>x</script>', 'run_status': 'paused', 'plan': {'requirements': [{'id': 'R1', 'text': '<img src=x onerror=alert(1)>'}], 'checkpoints': [{'id': 'a', 'title': '<script>bad()</script>'}]}, 'checkpoints': {'a': {'status': 'verifying', 'gates': {'review': {'status': 'stale'}}}}}, language='ar')
        self.assertNotIn('<script>', result)
        self.assertNotIn('<img src=x', result)
        self.assertIn('&lt;script&gt;', result)
        self.assertIn('دليل قديم', result)
        self.assertIn('dir="rtl"', result)
        self.assertNotIn('http://', result)
        self.assertNotIn('https://', result)

    def test_doctor_marks_declared_capabilities_not_verified(self):
        proc = subprocess.run([sys.executable, str(SCRIPTS / 'doctor.py'), '--host', 'test', '--declare-agents'], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        report = json.loads(proc.stdout)
        self.assertTrue(report['host_capabilities_declared_not_verified']['independent_agents'])
        self.assertFalse(report['network_or_services_started'])
        self.assertFalse(report['global_hooks_installed'])

    def make_skill(self, path):
        (path / 'scripts').mkdir(parents=True)
        (path / 'SKILL.md').write_text('original skill')
        (path / 'scripts' / 'workflow.py').write_text('print("test fixture")\n')
        return path

    def test_install_preserves_every_byte_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_skill(root / 'source')
            destination = root / 'installed'
            installer = module('install')
            result = installer.install(source, destination)
            self.assertEqual(installer.manifest(source), installer.manifest(destination))
            self.assertEqual(result['files'], 2)
            (destination / 'owner-note.txt').write_text('keep me')
            before = installer.manifest(destination)
            with self.assertRaises(ValueError):
                installer.install(source, destination)
            self.assertEqual(before, installer.manifest(destination))

    def test_install_rejects_broken_destination_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_skill(root / 'source')
            destination = root / 'installed'
            destination.symlink_to(root / 'missing')
            with self.assertRaises(ValueError):
                module('install').install(source, destination)
            self.assertTrue(destination.is_symlink())

    def test_install_rejects_source_symlink_before_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_skill(root / 'source')
            (source / 'alias').symlink_to(source / 'SKILL.md')
            destination = root / 'installed'
            with self.assertRaises(ValueError):
                module('install').install(source, destination)
            self.assertFalse(destination.exists())

    def test_install_rejects_destination_inside_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = self.make_skill(Path(directory) / 'source')
            with self.assertRaises(ValueError):
                module('install').install(source, source / 'nested')
            self.assertFalse((source / 'nested').exists())

    def test_install_rejects_symlinked_parent_into_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_skill(root / 'source')
            alias = root / 'alias'
            alias.symlink_to(source, target_is_directory=True)
            installer = module('install')
            # Avoid a recursive copy when exercising the old broken containment guard.
            with mock.patch.object(installer.shutil, 'copytree', side_effect=AssertionError('copy reached before containment rejection')) as copy:
                with self.assertRaises(ValueError):
                    installer.install(source, alias / 'nested')
                copy.assert_not_called()
            self.assertFalse((source / 'nested').exists())

    def test_receipt_collision_stops_before_installation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_skill(root / 'source')
            receipt = root / 'receipt.json'
            receipt.write_text('keep')
            proc = subprocess.run([sys.executable, str(SCRIPTS / 'install.py'), '--source', str(source), '--destination', str(root / 'installed'), '--receipt', str(receipt)], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertEqual(receipt.read_text(), 'keep')
            self.assertFalse((root / 'installed').exists())

    def test_receipt_equal_destination_rejects_before_installation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_skill(root / 'source')
            destination = root / 'installed'
            proc = subprocess.run([sys.executable, str(SCRIPTS / 'install.py'), '--source', str(source), '--destination', str(destination), '--receipt', str(destination)], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertNotIn('Traceback', proc.stderr)
            self.assertFalse(destination.exists())

    def test_install_success_produces_valid_matching_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_skill(root / 'source')
            destination = root / 'installed'
            receipt = root / 'receipt.json'
            proc = subprocess.run([sys.executable, str(SCRIPTS / 'install.py'), '--source', str(source), '--destination', str(destination), '--receipt', str(receipt)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads(receipt.read_text())
            self.assertEqual(data['sha256_manifest'], module('install').manifest(destination))

    def test_install_failure_removes_own_reserved_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_skill(root / 'source')
            destination = root / 'already-exists'
            destination.mkdir()
            receipt = root / 'receipt.json'
            proc = subprocess.run([sys.executable, str(SCRIPTS / 'install.py'), '--source', str(source), '--destination', str(destination), '--receipt', str(receipt)], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(receipt.exists())
            self.assertEqual(list(destination.iterdir()), [])

    def receipt_fault(self, failure, destination_exists=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_skill(root / 'source')
            destination = root / 'installed'
            if destination_exists:
                destination.mkdir()
            receipt = root / 'receipt.json'
            original_open = Path.open

            class FaultingReceipt:
                def __init__(self, stream):
                    self.stream = stream

                def write(self, text):
                    if failure == 'write':
                        raise OSError('injected receipt write error')
                    return self.stream.write(text)

                def flush(self):
                    return self.stream.flush()

                def fileno(self):
                    return self.stream.fileno()

                def close(self):
                    self.stream.close()
                    if failure == 'close':
                        raise OSError('injected receipt close error')

            def fault_open(path, mode='r', *args, **kwargs):
                stream = original_open(path, mode, *args, **kwargs)
                return FaultingReceipt(stream) if path == receipt and mode == 'x' else stream

            installer = module('install')
            argv = ['install.py', '--source', str(source), '--destination', str(destination), '--receipt', str(receipt)]
            output = io.StringIO()
            with mock.patch.object(sys, 'argv', argv), mock.patch.object(Path, 'open', fault_open), redirect_stdout(output):
                code = installer.main()
            data = json.loads(output.getvalue())
            self.assertFalse(receipt.exists(), 'incomplete receipt must not survive')
            if destination_exists:
                self.assertEqual(code, 1)
                self.assertIn('error', data)
                self.assertEqual(list(destination.iterdir()), [])
            else:
                self.assertEqual(code, 0)
                self.assertEqual(data['installed'], str(destination))
                self.assertIn('receipt_error', data)
                self.assertEqual(module('install').manifest(source), module('install').manifest(destination))

    def test_receipt_write_failure_reports_successful_install(self):
        self.receipt_fault('write')

    def test_receipt_close_failure_reports_successful_install(self):
        self.receipt_fault('close')

    def test_receipt_cleanup_error_preserves_primary_install_failure(self):
        self.receipt_fault('close', destination_exists=True)


if __name__ == '__main__':
    unittest.main()
