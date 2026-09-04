#!/usr/bin/env python3
"""Transactional, user-owned Hyper configuration. No privileged changes."""
import copy
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

CONFIG = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
STATE = CONFIG / 'omarchy-hyper/state.json'
MAIN = CONFIG / 'hypr/hyprland.lua'
GENERATED = CONFIG / 'hypr/omarchy-hyper.lua'
MARKER = '-- Managed by digitalbase.hyper\n'
PREFIX = '✦ Hyper: '


def run(*args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=15)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f'{args[0]} failed')
    return result.stdout.strip()


def lua(value):
    # JSON strings use Lua-compatible escapes for the validated text we accept.
    return json.dumps(value, ensure_ascii=False)


def clean(value):
    if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
        raise ValueError('Expected nonempty text without control characters')
    return value


def key(value):
    value = clean(value).upper().strip()
    if not re.fullmatch(r'(SHIFT\+)?([A-Z0-9]|F([1-9]|1[0-2])|RETURN|SPACE|TAB|BACKSPACE|UP|DOWN|LEFT|RIGHT)', value):
        raise ValueError('Use a letter, digit, F1–F12, Return, Space, Tab, Backspace or arrow, optionally with Shift+')
    return value


def load():
    if not STATE.exists():
        return {'version': 1, 'options': None, 'shortcuts': {}}
    data = json.loads(STATE.read_text())
    if data.get('version') != 1:
        raise ValueError('Unsupported Hyper state version')
    return data


def options():
    return json.loads(run('hyprctl', 'getoption', 'input:kb_options', '-j'))['str']


def external_bindings():
    rows = []
    for binding in json.loads(run('hyprctl', 'binds', '-j')):
        mask = binding.get('modmask', 0)
        if mask & 32 and not binding.get('description', '').startswith(PREFIX):
            rows.append({'key': ('SHIFT+' if mask & 1 else '') + binding.get('key', '').upper(),
                         'name': binding.get('description') or binding.get('arg') or 'Existing binding',
                         'modmask': mask, 'external': True})
    return rows


def status():
    data = load()
    return {**data, 'active': 'caps:hyper' in options().split(','), 'external': external_bindings()}


def render(data):
    lines = [MARKER.rstrip()]
    if data['options'] is not None:
        lines.append('hl.config({ input = { kb_options = ' + lua(data['options']) + ' } })')
    for shortcut, app in sorted(data['shortcuts'].items()):
        combo = 'MOD3 + ' + key(shortcut).replace('+', ' + ')
        desktop = clean(app['id']) + '.desktop'
        command = 'uwsm-app -- gtk-launch ' + shlex.quote(desktop)
        lines.append(f'o.bind({lua(combo)}, {lua(PREFIX + clean(app["name"]))}, {lua(command)})')
    return '\n'.join(lines) + '\n'


def atomic(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(content)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def apply(data):
    if not MAIN.exists():
        raise RuntimeError('This plugin requires Omarchy with hypr/hyprland.lua')
    baseline = run('hyprctl', 'configerrors')
    if baseline:
        raise RuntimeError('Fix existing Hyprland configuration errors first: ' + baseline)
    hook = MARKER + 'dofile(' + lua(str(GENERATED)) + ')\n'
    before = {p: p.read_text() if p.exists() else None for p in (MAIN, GENERATED, STATE)}
    main = before[MAIN]
    if MARKER in main and hook not in main:
        raise RuntimeError('The Hyper include was edited manually. Restore it before continuing.')
    main = main.replace(hook, '')
    if data['options'] is not None or data['shortcuts']:
        main = main.rstrip() + '\n\n' + hook
    # Keep a first-use backup independent of subsequent transactions.
    backup = MAIN.with_name('hyprland.lua.before-hyper')
    if not backup.exists():
        atomic(backup, before[MAIN])
    try:
        atomic(GENERATED, render(data))
        atomic(MAIN, main)
        run('hyprctl', 'reload')
        errors = run('hyprctl', 'configerrors')
        if errors:
            raise RuntimeError(errors)
        if data['options'] is not None and options() != data['options']:
            raise RuntimeError('Another keyboard setting overrides Hyper')
        atomic(STATE, json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    except Exception:
        for path, content in before.items():
            if content is None:
                path.unlink(missing_ok=True)
            else:
                atomic(path, content)
        run('hyprctl', 'reload')
        raise


def mutate(action, args):
    data = copy.deepcopy(load())
    if action == 'enable':
        current = options()
        if 'caps:hyper' not in current.split(','):
            conflicting = [p for p in current.split(',') if 'caps' in p]
            kept = [p for p in current.split(',') if p and p not in conflicting]
            data['options'] = ','.join(kept + ['caps:hyper'])
    elif action == 'restore':
        # Removing the override reveals the user's original input.lua settings.
        data['options'] = None
    elif action == 'assign':
        shortcut, desktop, name = key(args[0]), clean(args[1]), clean(args[2])
        if desktop.startswith('-') or '/' in desktop:
            raise ValueError('Invalid desktop entry ID')
        if any(b['key'] == shortcut and b['modmask'] in (32, 33) for b in external_bindings()):
            raise ValueError('That Hyper shortcut is already assigned in your Hyprland config')
        data['shortcuts'][shortcut] = {'id': desktop, 'name': name}
    elif action == 'remove':
        data['shortcuts'].pop(key(args[0]), None)
    elif action == 'uninstall':
        data = {'version': 1, 'options': None, 'shortcuts': {}}
    else:
        raise ValueError('Unknown action')
    apply(data)
    return status()


def main():
    STATE.parent.mkdir(parents=True, exist_ok=True)
    with (STATE.parent / '.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            action = sys.argv[1] if len(sys.argv) > 1 else 'status'
            result = status() if action == 'status' else mutate(action, sys.argv[2:])
            print(json.dumps({'ok': True, **result}))
        except Exception as error:
            print(json.dumps({'ok': False, 'error': str(error)}))
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
