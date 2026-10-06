#!/usr/bin/env python3
"""Render a read-only English or Arabic snapshot from verified engine status."""
import argparse
import datetime
import html
import json
import subprocess
import sys
from pathlib import Path

LABELS = {
    'ready': 'جاهزة', 'implementing': 'قيد التنفيذ', 'verifying': 'قيد التحقق',
    'proven': 'مثبتة', 'accepted': 'معتمدة', 'pending': 'لم يثبت بعد',
    'stale': 'دليل قديم', 'pass': 'اجتاز', 'fail': 'فشل', 'invalid': 'غير صالح',
    'paused': 'موقوفة', 'cancelled': 'ملغاة', 'active': 'نشطة', 'blocked': 'متعذرة',
    'behavior': 'السلوك', 'review': 'المراجعة', 'ui': 'الواجهة',
}


def escape(value):
    return html.escape(str(value), quote=True)


def label(value):
    return escape(LABELS.get(str(value), value))


def _render_arabic(status):
    plan = status.get('plan', {})
    checkpoints = status.get('checkpoints', {})
    if isinstance(checkpoints, list):
        checkpoints = {item.get('id', str(i)): item for i, item in enumerate(checkpoints)}
    all_accepted = bool(checkpoints) and all(cp.get('status') == 'accepted' for cp in checkpoints.values())
    outcome = 'جميع المراحل معتمدة' if all_accepted else 'توجد مراحل لم تُعتمد بعد'
    planned = {cp['id']: cp for cp in plan.get('checkpoints', [])}
    rows = []
    for ident, cp in checkpoints.items():
        config = planned.get(ident, {})
        gates = cp.get('gates', cp.get('gate_summary', {}))
        gates_html = []
        if isinstance(gates, dict):
            for name, gate in gates.items():
                verdict = gate.get('status', gate.get('verdict', 'pending')) if isinstance(gate, dict) else gate
                gates_html.append(f'<li>{label(name)}: <strong>{label(verdict)}</strong><pre>{escape(json.dumps(gate, ensure_ascii=False, indent=2))}</pre></li>')
        rows.append(f'<article><h2>{escape(config.get("title", cp.get("title", ident)))}</h2><p>المرحلة <code>{escape(ident)}</code>: <strong>{label(cp.get("status", "pending"))}</strong></p><ul>{"".join(gates_html)}</ul><details><summary>تفاصيل المرحلة وهوية الدليل</summary><pre>{escape(json.dumps(cp, ensure_ascii=False, indent=2))}</pre></details></article>')
    requirements = plan.get('requirements', [])
    requirements_html = ''.join(f'<li><code>{escape(req.get("id", ""))}</code>: {escape(req.get("text", ""))}</li>' for req in requirements)
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return f'''<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>سجل المراحل والتحقق</title><style>
*{{box-sizing:border-box}} body{{margin:0;background:#f3f2ee;color:#172323;font:17px/1.8 system-ui,sans-serif}} main{{max-width:1100px;margin:auto;padding:24px}} header,article,section{{background:white;border:1px solid #d0d8d4;border-radius:12px;padding:24px;margin-bottom:20px}} h1{{margin-top:0;font-size:2rem}} h2{{font-size:1.35rem}} code,pre{{direction:ltr;text-align:left}} code{{unicode-bidi:isolate;display:inline-block;max-width:100%;overflow-wrap:anywhere}} pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f0f4f1;padding:12px;font-size:13px;max-height:500px;overflow:auto}} p,li{{overflow-wrap:anywhere}} .notice{{border-inline-start:5px solid #a9671f;padding-inline-start:16px}} details{{margin-top:16px}} @media(max-width:600px){{main{{padding:12px}}header,article,section{{padding:16px}}h1{{font-size:1.55rem}}}}
</style></head><body><main><header><h1>سجل المراحل والتحقق</h1><p>نتيجة العمل: <strong>{outcome}</strong></p><p>حالة التحكم بالتشغيل: <strong>{label(status.get('status', status.get('run_status', 'unknown')))}</strong></p><p class="notice">هذه لقطة للعرض فقط، أُنشئت في <code>{escape(timestamp)}</code>. أعد إنشاءها بعد تغيير المصدر. نجاح التحقق المحلي لا يعني النشر أو قبول بيئة لم تُختبر.</p><p>هوية الخطة: <code>{escape(status.get('plan_hash', 'غير متاحة'))}</code></p></header><section><h2>متطلبات الطلب</h2><ul>{requirements_html}</ul></section>{''.join(rows)}<section><h2>السجل الكامل</h2><details><summary>افتح التفاصيل الفنية</summary><pre>{escape(json.dumps(status, ensure_ascii=False, indent=2))}</pre></details></section></main></body></html>'''


def render(status, language='en'):
    if language == 'ar':
        return _render_arabic(status)
    if language != 'en':
        raise ValueError('language must be en or ar')
    plan = status.get('plan', {})
    checkpoints = status.get('checkpoints', {})
    if isinstance(checkpoints, list):
        checkpoints = {item.get('id', str(i)): item for i, item in enumerate(checkpoints)}
    planned = {cp['id']: cp for cp in plan.get('checkpoints', [])}
    accepted = bool(checkpoints) and all(cp.get('status') == 'accepted' for cp in checkpoints.values())
    outcome = 'All checkpoints accepted' if accepted else 'Some checkpoints are not accepted'
    rows = []
    for ident, checkpoint in checkpoints.items():
        title = escape(planned.get(ident, {}).get('title', ident))
        state = escape(checkpoint.get('status', 'pending'))
        gates = checkpoint.get('gates', {})
        items = []
        if isinstance(gates, dict):
            for name, gate in gates.items():
                verdict = gate.get('status', 'pending') if isinstance(gate, dict) else gate
                items.append(f'<li>{escape(name)}: <strong>{escape(verdict)}</strong><pre>{escape(json.dumps(gate, ensure_ascii=False, indent=2))}</pre></li>')
        rows.append(f'<article><h2>{title}</h2><p>Checkpoint <code>{escape(ident)}</code>: <strong>{state}</strong></p><ul>{"".join(items)}</ul><details><summary>Checkpoint and evidence identity</summary><pre>{escape(json.dumps(checkpoint, ensure_ascii=False, indent=2))}</pre></details></article>')
    requirements = ''.join(f'<li><code>{escape(item.get("id", ""))}</code>: {escape(item.get("text", ""))}</li>' for item in plan.get('requirements', []))
    stamp = escape(datetime.datetime.now(datetime.timezone.utc).isoformat())
    return f'''<!doctype html>
<html lang="en" dir="ltr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>Checkpoint evidence report</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#f3f5f8;color:#172333;font:17px/1.8 system-ui,sans-serif}}main{{max-width:1100px;margin:auto;padding:24px}}header,article,section{{background:white;border:1px solid #d0d8e4;border-radius:12px;padding:24px;margin-bottom:20px}}h1{{margin-top:0;font-size:2rem}}h2{{font-size:1.35rem}}code{{display:inline-block;max-width:100%;overflow-wrap:anywhere}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f0f4f8;padding:12px;font-size:13px;max-height:500px;overflow:auto}}p,li{{overflow-wrap:anywhere}}.notice{{border-inline-start:4px solid #2563eb;padding-inline-start:16px}}@media(max-width:600px){{main{{padding:12px}}header,article,section{{padding:16px}}h1{{font-size:1.55rem}}}}
</style></head><body><main><header><h1>Checkpoint evidence report</h1><p>Outcome: <strong>{outcome}</strong></p><p>Run control status: <strong>{escape(status.get('run_status', 'unknown'))}</strong></p><p class="notice">Read-only snapshot generated at <code>{stamp}</code>. Regenerate after source changes. Local acceptance does not verify deployment or untested environments.</p><p>Plan identity: <code>{escape(status.get('plan_hash', 'unavailable'))}</code></p></header><section><h2>Requirements</h2><ul>{requirements}</ul></section>{''.join(rows)}<section><h2>Full run record</h2><details><summary>Technical details</summary><pre>{escape(json.dumps(status, ensure_ascii=False, indent=2))}</pre></details></section></main></body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--lang', choices=('en', 'ar'), default='en')
    args = parser.parse_args()
    engine = Path(__file__).with_name('workflow.py')
    result = subprocess.run([sys.executable, str(engine), 'status', '--run', args.run], capture_output=True, text=True)
    if result.returncode:
        print(result.stderr or result.stdout, file=sys.stderr)
        return 1
    status = json.loads(result.stdout)
    output = Path(args.output).resolve()
    run = Path(args.run).resolve()
    # A reader must never replace the journal, plan, evidence or projection.
    if output == run or run in output.parents:
        parser.error('write the viewer outside the run directory')
    if output.suffix.lower() != '.html':
        parser.error('output must have an .html extension')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(status, args.lang), encoding='utf-8')
    print(json.dumps({'output': str(output), 'snapshot_only': True}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
