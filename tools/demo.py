"""Run a disposable engine demonstration; this is not an independent review."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ENGINE = Path(__file__).resolve().parents[1] / 'skills/sbar-checkpoint/scripts/workflow.py'


def main():
    with tempfile.TemporaryDirectory(prefix='sbar-demo-') as directory:
        root = Path(directory)
        project = root / 'project'
        (project / 'tests').mkdir(parents=True)
        implementation = project / 'total.py'
        implementation.write_text('def total_cents(subtotal, fee):\n    return subtotal - fee\n')
        (project / 'tests/test_total.py').write_text('import unittest\nfrom total import total_cents\nclass TotalTests(unittest.TestCase):\n    def test_fee(self):\n        self.assertEqual(total_cents(1200, 75), 1275)\n    def test_zero_fee(self):\n        self.assertEqual(total_cents(1200, 0), 1200)\n')
        no_review = {'kind': 'not_applicable', 'reason': 'Engine demonstration only. Real task review must come from an independent host context.'}
        plan = {'schema_version': 1, 'mode': 'repair', 'approval': 'delegated', 'environment': 'local-isolated',
                'requirements': [{'id': 'R1', 'text': 'Add a fee to the subtotal'}],
                'checkpoints': [{'id': 'core', 'title': 'Repair fee calculation', 'covers': ['R1'],
                                 'depends_on': [], 'scope': ['total.py', 'tests/test_total.py'],
                                 'gates': {'behavior': {'kind': 'command', 'checks': [{
                                     'id': 'unit', 'argv': [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                                     'parser': 'unittest', 'min_tests': 2, 'timeout_seconds': 15, 'max_attempts': 2}]},
                                     'review': no_review, 'ui': {'kind': 'not_applicable', 'reason': 'No UI'}}}]}
        plan_file = root / 'plan.json'
        plan_file.write_text(json.dumps(plan))
        run = root / 'run'

        def cli(*args, success=True):
            proc = subprocess.run([sys.executable, '-B', str(ENGINE), *args, '--run', str(run)],
                                  capture_output=True, text=True, timeout=20)
            if (proc.returncode == 0) != success:
                raise RuntimeError(proc.stderr or proc.stdout)
            return json.loads(proc.stdout or proc.stderr)

        cli('init', '--project', str(project), '--plan', str(plan_file))
        cli('start', '--checkpoint', 'core', '--actor', 'demo-builder')
        cli('check', '--checkpoint', 'core', '--check', 'unit', success=False)
        assert cli('status')['checkpoints']['core']['gates']['behavior']['status'] == 'fail'
        implementation.write_text('def total_cents(subtotal, fee):\n    return subtotal + fee\n')
        cli('check', '--checkpoint', 'core', '--check', 'unit')
        cli('prove', '--checkpoint', 'core')
        cli('accept', '--checkpoint', 'core')
        assert cli('status')['checkpoints']['core']['status'] == 'accepted'
        print(json.dumps({'demo': 'passed', 'failure_reproduced': True, 'tests_executed': 2,
                          'final_checkpoint': 'accepted', 'independent_review_performed': False,
                          'scope': 'Engine mechanics in a disposable fixture, not production or agent certification'}, indent=2))


if __name__ == '__main__':
    main()
