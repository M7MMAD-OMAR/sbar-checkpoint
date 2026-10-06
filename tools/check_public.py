"""Validate distributable content without reading user settings or secrets."""
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {'.git', '__pycache__', 'dist', '.venv', 'node_modules'}


def main():
    failures = []
    files = [p for p in ROOT.rglob('*') if p.is_file() and not IGNORED.intersection(p.relative_to(ROOT).parts)]
    skill_files = [p for p in files if p.name == 'SKILL.md']
    expected = ROOT / 'skills/sbar-checkpoint/SKILL.md'
    if skill_files != [expected]:
        failures.append('Expected exactly one skill at skills/sbar-checkpoint/SKILL.md')
    for path in files:
        relative = str(path.relative_to(ROOT))
        if path.is_symlink():
            failures.append(relative + ': symlink is not part of the public bundle')
        if path.suffix in ('.zip', '.skill', '.log', '.jsonl') or path.name.startswith('.env'):
            failures.append(relative + ': generated or sensitive file type')
        if path.suffix == '.png':
            continue
        try:
            content = path.read_text(encoding='utf-8')
        except (UnicodeError, OSError):
            failures.append(relative + ': unexpected binary file')
            continue
        if chr(0x2013) in content or chr(0x2014) in content:
            failures.append(relative + ': long dash')
        if re.search(r'(?:/home/|/Users/)[A-Za-z0-9._-]+/', content):
            failures.append(relative + ': personal absolute path')
        if re.search(r'(?:gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9_-]{30,}|BEGIN [A-Z ]*PRIVATE KEY)', content):
            failures.append(relative + ': possible secret')
        if path.suffix == '.md':
            for link in re.findall(r'\]\(([^)]+)\)', content):
                link = unquote(link.split('#', 1)[0].strip('<>'))
                if not link or re.match(r'[a-zA-Z]+:', link):
                    continue
                if not (path.parent / link).resolve().is_file():
                    failures.append(relative + ': broken relative link ' + link)
    frontmatter = expected.read_text().split('---', 2)[1]
    if 'name: sbar-checkpoint' not in frontmatter or 'license: MIT' not in frontmatter:
        failures.append('Skill metadata must declare public name and MIT license')
    print(json.dumps({'passed': not failures, 'public_files': len(files), 'failures': failures}, indent=2))
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
