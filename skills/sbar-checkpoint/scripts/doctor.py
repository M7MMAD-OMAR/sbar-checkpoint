#!/usr/bin/env python3
"""Report observable local prerequisites without running project services."""
import argparse
import json
import os
import platform
import shutil
import sys
from pathlib import Path
from hosts import PROFILES, resolve_destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='unspecified')
    parser.add_argument('--declare-agents', action='store_true')
    parser.add_argument('--declare-browser', action='store_true')
    parser.add_argument('--declare-images', action='store_true')
    args = parser.parse_args()
    supported = os.name == 'posix' and sys.version_info >= (3, 10)
    result = {
        'platform': platform.system(), 'python_version': platform.python_version(),
        'engine_prerequisites_observed': supported, 'host': args.host,
        'executables': {name: shutil.which(name) for name in ('git', 'python3', 'codex', 'claude', 'hermes')},
        'engine_found': Path(__file__).with_name('workflow.py').is_file(),
        'host_capabilities_declared_not_verified': {
            'independent_agents': args.declare_agents, 'browser': args.declare_browser,
            'image_review': args.declare_images,
        },
        'network_or_services_started': False, 'global_hooks_installed': False,
    }
    if args.host in PROFILES:
        result['host_profile'] = PROFILES[args.host]
        try:
            destination = resolve_destination(args.host)
            result['native_skill_directory'] = str(destination)
            result['native_skill_file_observed'] = (destination / 'SKILL.md').is_file()
        except ValueError as exc:
            result['host_path_error'] = str(exc)
        result['host_discovery_verified'] = False
        result['agent_review_verified'] = False
        result['note'] = 'Executable and file presence do not verify host discovery or model access.'
    print(json.dumps(result, indent=2))
    return 0 if supported and result['engine_found'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
