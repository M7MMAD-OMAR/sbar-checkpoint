#!/usr/bin/env python3
"""Install this skill to an explicit new directory without overwriting anything."""
import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path


def manifest(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


def install(source, destination):
    source = source.resolve()
    destination = destination.absolute()
    # lexists also rejects broken symlinks, which must never be overwritten.
    if os.path.lexists(destination):
        raise ValueError('destination already exists; no files were changed')
    # Check the requested leaf first, then resolve parent aliases for containment.
    destination = destination.resolve()
    if source == destination or source in destination.parents:
        raise ValueError('destination cannot be inside the source skill')
    if not (source / 'SKILL.md').is_file() or not (source / 'scripts/workflow.py').is_file():
        raise ValueError('source is not a complete sbar-checkpoint skill')
    if any(p.is_symlink() for p in source.rglob('*')):
        raise ValueError('skill source must not contain symlinks')
    expected = manifest(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.sbar-checkpoint-install-', dir=destination.parent))
    payload = staging / 'skill'
    try:
        shutil.copytree(source, payload, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        if manifest(payload) != expected:
            raise ValueError('copy integrity check failed')
        # Reserve the new destination exclusively so another install cannot win.
        destination.mkdir()
        try:
            for child in payload.iterdir():
                os.rename(child, destination / child.name)
        except BaseException:
            # Only our newly reserved directory is removed on failure.
            shutil.rmtree(destination)
            raise
    finally:
        shutil.rmtree(staging)
    return {'installed': str(destination), 'files': len(expected), 'sha256_manifest': expected,
            'overwrote_existing_files': False, 'settings_changed': False}


def finish_receipt(handle, receipt, errors, remove=False):
    """Finalize an owned receipt without hiding the primary installation result."""
    if not handle:
        return
    try:
        handle.close()
    except OSError as exc:
        errors.append('receipt close: ' + str(exc))
    if remove or errors:
        try:
            receipt.unlink(missing_ok=True)
        except OSError as exc:
            errors.append('receipt cleanup: ' + str(exc))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default=str(Path(__file__).resolve().parents[1]))
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--destination')
    target.add_argument('--host', choices=('codex', 'claude', 'hermes'))
    parser.add_argument('--scope', choices=('user', 'project'), default='user')
    parser.add_argument('--project')
    parser.add_argument('--receipt')
    args = parser.parse_args()
    if args.host:
        from hosts import resolve_destination
        try:
            args.destination = str(resolve_destination(args.host, args.scope, args.project))
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
    elif args.scope != 'user' or args.project:
        parser.error('--scope and --project require --host')
    receipt = Path(args.receipt).resolve() if args.receipt else None
    source = Path(args.source).resolve()
    destination = Path(args.destination).resolve()
    if receipt:
        if os.path.lexists(args.receipt):
            parser.error('receipt already exists; choose a new path')
        if (receipt.is_relative_to(destination) or destination.is_relative_to(receipt)
                or receipt.is_relative_to(source)):
            parser.error('receipt must be outside source and destination trees')
    handle = None
    try:
        if receipt:
            receipt.parent.mkdir(parents=True, exist_ok=True)
            # Reserve before installing, so a collision cannot cause a partial success.
            handle = receipt.open('x', encoding='utf-8')
        result = install(Path(args.source), Path(args.destination))
    except (OSError, ValueError) as exc:
        cleanup_errors = []
        finish_receipt(handle, receipt, cleanup_errors, remove=True)
        print(json.dumps({'error': str(exc), 'receipt_cleanup_errors': cleanup_errors}))
        return 1
    if handle:
        receipt_errors = []
        try:
            json.dump(result, handle, indent=2)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        except OSError as exc:
            receipt_errors.append('receipt write: ' + str(exc))
        finally:
            finish_receipt(handle, receipt, receipt_errors)
        if receipt_errors:
            # Installation succeeded; report the ancillary failure without inviting retries.
            result['receipt_error'] = '; '.join(receipt_errors)
    print(json.dumps({k: v for k, v in result.items() if k != 'sha256_manifest'}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
