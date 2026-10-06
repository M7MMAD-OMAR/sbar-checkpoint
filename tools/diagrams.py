"""Generate the editable workflow and evidence SVGs used in the public guide."""
from pathlib import Path
from html import escape

ROOT = Path(__file__).resolve().parents[1] / 'docs/diagrams'
INK, MUTED, BLUE, LINE = '#142338', '#526176', '#245ce3', '#cbd5e2'


def frame(title, description, height):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10Z" fill="#718096"/></marker></defs>',
            f'<rect width="1200" height="{height}" rx="24" fill="#f6f8fc"/>',
            '<g font-family="Arial,Helvetica,sans-serif">',
            f'<text x="52" y="55" font-size="13" font-weight="700" letter-spacing="2" fill="{BLUE}">SBAR CHECKPOINT</text>',
            f'<text x="52" y="103" font-size="32" font-weight="700" fill="{INK}">{escape(title)}</text>']


def text(x, y, content, size=16, color=MUTED, weight='400'):
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color}">{escape(content)}</text>'


def box(x, y, width, height, title, lines, badge=None, focal=False):
    items = [f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="14" fill="{BLUE if focal else "white"}" stroke="{BLUE if focal else LINE}"/>']
    color = 'white' if focal else INK
    if badge:
        items.append(text(x + 20, y + 32, badge, 13, '#dbe8ff' if focal else BLUE, '700'))
    heading_y = y + (66 if badge else 36)
    items.append(text(x + 20, heading_y, title, 21, color, '700'))
    for i, line in enumerate(lines):
        items.append(text(x + 20, heading_y + 31 + i * 24, line, 15, '#e1eaff' if focal else MUTED))
    return items


def arrow(path, dashed=False):
    dash = ' stroke-dasharray="6 5"' if dashed else ''
    return f'<path d="{path}" fill="none" stroke="#718096" stroke-width="2" marker-end="url(#arrow)"{dash}/>'


def workflow():
    out = frame('From request to accepted outcome',
                'Contract, plan, implement, verify and accept. Failed or stale evidence returns to implementation and verification. Pause preserves the run.', 550)
    out.append(text(52, 137, 'Small outcomes. Planned checks. Fresh review. Explicit acceptance.', 17))
    data = [('Contract', ['Requirements', 'Scope and authority']),
            ('Plan', ['Dependencies', 'Checks and gates']),
            ('Implement', ['One ready stage', 'Preserve existing work']),
            ('Verify', ['Run real checks', 'Fresh reviewer']),
            ('Accept', ['All gates current', 'Unlock dependents'])]
    for index, (title, lines) in enumerate(data):
        x = 52 + index * 220
        out += box(x, 192, 202, 172, title, lines, f'0{index + 1}', index == 3)
        if index < 4:
            out.append(arrow(f'M{x+204} 278 H{x+216}'))
    out.append(arrow('M813 366 V420 H593 V367', True))
    out.append(text(623, 409, 'Repair or refresh', 14, MUTED, '700'))
    out.append('<path d="M52 465 H1148" stroke="#dbe2ec"/>')
    out.append(text(52, 502, 'Pause / resume preserves the plan, journal and evidence.', 16))
    out.append(text(697, 502, 'Accepted locally does not mean deployed.', 16, BLUE, '700'))
    out.extend(['</g>', '</svg>'])
    return '\n'.join(out) + '\n'


def evidence():
    out = frame('Evidence belongs to a specific version',
                'Plan, source and artifact identities bind behavior, review and UI reports. Source or artifact changes invalidate proof. Actor labels are not authentication.', 642)
    out.append(text(52, 137, 'A passing result is useful only while its inputs remain current.', 17))
    for x, title, lines in [(52, 'Plan identity', ['Requirements, scopes', 'Gate configuration']),
                            (423, 'Source identity', ['Declared files and tests', 'Ancestor scopes']),
                            (794, 'Artifact identity', ['Captured logs and reports', 'Reference and UI captures'])]:
        out += box(x, 184, 354, 126, title, lines)
    for x in (229, 600, 971):
        out.append(arrow(f'M{x} 312 V338 H600 V355'))
    out += box(352, 357, 496, 111, 'Proof gate', ['Behavior passes. Independent review is current.', 'Required UI evidence matches. Findings are resolved.'], focal=True)
    out.append(arrow('M600 470 V490'))
    out.append(text(470, 520, 'Accept the checkpoint', 22, INK, '700'))
    out.append('<path d="M52 555 H1148" stroke="#dbe2ec"/>')
    out.append(text(52, 589, 'Changed inputs: refresh affected checks and reviews.', 16, BLUE, '700'))
    out.append(text(52, 615, 'Hashes check consistency. Reviewer identity and permissions remain host responsibilities.', 15))
    out.extend(['</g>', '</svg>'])
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / 'workflow.svg').write_text(workflow())
    (ROOT / 'evidence.svg').write_text(evidence())
    print('Generated workflow.svg and evidence.svg')
