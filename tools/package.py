"""Build deterministic runtime archives, excluding tests and local evidence."""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/sbar-checkpoint'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=str(ROOT / 'dist'))
    args = parser.parse_args()
    subprocess.run([sys.executable, str(ROOT / 'tools/check_public.py')], check=True)
    match = re.search(r'(?m)^  version: ([0-9]+\.[0-9]+\.[0-9]+)$', (SKILL / 'SKILL.md').read_text())
    if not match:
        parser.error('Skill metadata needs a numeric semantic version')
    version = match.group(1)
    output = Path(args.output).resolve()
    if output.is_relative_to(SKILL):
        parser.error('package output must be outside the skill directory')
    output.mkdir(parents=True, exist_ok=True)
    archive_path = output / f'sbar-checkpoint-v{version}.zip'
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(SKILL.rglob('*')):
            if not file.is_file() or '__pycache__' in file.parts or file.suffix == '.pyc':
                continue
            info = zipfile.ZipInfo(str(file.relative_to(SKILL.parent)), (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, file.read_bytes())
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        for name in archive.namelist():
            assert archive.read(name) == (SKILL.parent / name).read_bytes()
    skill_path = output / 'sbar-checkpoint.skill'
    skill_path.write_bytes(archive_path.read_bytes())
    checksums = ''.join(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name + '\n'
                        for path in (archive_path, skill_path))
    (output / 'SHA256SUMS').write_text(checksums)
    print(f'Built {archive_path.name}, sbar-checkpoint.skill and SHA256SUMS')


if __name__ == '__main__':
    main()
