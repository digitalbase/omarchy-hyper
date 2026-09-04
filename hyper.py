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
    value = re.sub(r'\s+', '', clean(value)).upper()
    parts = value.split('+')
    modifiers, symbol = parts[:-1], parts[-1]
    if (len(set(modifiers)) != len(modifiers)
            or any(m not in ('SUPER', 'CTRL', 'ALT', 'SHIFT') for m in modifiers)
            or not re.fullmatch(r'[A-Z0-9_]+|CODE:[0-9]{1,3}', symbol)):
        raise ValueError('Use a key name, optionally with Shift, Ctrl, Alt or Super')
    return '+'.join([m for m in ('SUPER', 'CTRL', 'ALT', 'SHIFT') if m in modifiers] + [symbol])


def combo(shortcut):
    return 'MOD3 + ' + key(shortcut).replace('CODE:', 'code:').replace('+', ' + ')


class Conflict(ValueError):
    def __init__(self, shortcut, bindings):
        self.bindings = bindings
        super().__init__('✦ ' + shortcut + ' is already assigned to ' + ', '.join(b['name'] for b in bindings))



def load():
    if not STATE.exists():
        return {'version': 1, 'options': None, 'shortcuts': {}}
    data = json.loads(STATE.read_text())
    if data.get('version') != 1:
        raise ValueError('Unsupported Hyper state version')
    return data


def options():
    return json.loads(run('hyprctl', 'getoption', 'input:kb_options', '-j'))['str']


def configured_physical_key(description):
    """Recover physical key labels omitted by Hyprland's Lua bind report.

    Read literal declarations only; never execute or import user Lua files.
    Ambiguous matches stay unknown instead of guessing a key.
    """
    matches = set()
    pattern = re.compile(r'o\.bind\(\s*"([^"\n]+)"\s*,\s*"([^"\n]+)"')
    for path in (CONFIG / 'hypr').glob('*.lua'):
        source = re.sub(r'--\[\[.*?\]\]', '', path.read_text(), flags=re.S)
        source = re.sub(r'^\s*--.*$', '', source, flags=re.M)
        for combo, name in pattern.findall(source):
            if name != description or 'MOD3' not in combo.upper():
                continue
            physical = re.search(r'code:(\d+)', combo, re.I)
            if physical:
                matches.add('CODE:' + physical[1])
    return next(iter(matches)) if len(matches) == 1 else ''


def external_bindings():
    rows = []
    for binding in json.loads(run('hyprctl', 'binds', '-j')):
        mask = binding.get('modmask', 0)
        if mask & 32 and not binding.get('description', '').startswith(PREFIX):
            label = binding.get('key', '').upper()
            if not label:
                label = ('CODE:' + str(binding['keycode'])) if binding.get('keycode') else configured_physical_key(binding.get('description', ''))
            modifiers = ''.join(name + '+' for bit, name in ((64, 'SUPER'), (4, 'CTRL'), (8, 'ALT'), (1, 'SHIFT')) if mask & bit)
            rows.append({'key': modifiers + label,
                         'name': binding.get('description') or binding.get('arg') or 'Existing binding',
                         'modmask': mask, 'external': True, 'submap': binding.get('submap', '')})
    return rows


def status():
    data = load()
    return {**data, 'active': 'caps:hyper' in options().split(','), 'external': external_bindings()}


def render(data):
    lines = [MARKER.rstrip()]
    if data['options'] is not None:
        lines.append('hl.config({ input = { kb_options = ' + lua(data['options']) + ' } })')
    for shortcut in sorted(data.get('suppressed', [])):
        lines.append(f'hl.unbind({lua(combo(shortcut))})')
    for shortcut, app in sorted(data['shortcuts'].items()):
        desktop = clean(app['id']) + '.desktop'
        command = 'uwsm-app -- gtk-launch ' + shlex.quote(desktop)
        lines.append(f'o.bind({lua(combo(shortcut))}, {lua(PREFIX + clean(app["name"]))}, {lua(command)})')
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
    if data['options'] is not None or data['shortcuts'] or data.get('suppressed'):
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
    if action in ('enable', 'disable'):
        current = options()
        # An explicit override also handles Hyper set in an existing input.lua.
        # Keep layout-switching and other non-Caps options intact.
        kept = [p for p in current.split(',') if p and 'caps' not in p]
        target = 'caps:hyper' if action == 'enable' else 'caps:capslock'
        data['options'] = ','.join(kept + [target])
    elif action == 'restore':
        # Removing the override reveals the user's original input.lua settings.
        data['options'] = None
    elif action in ('assign', 'overwrite'):
        shortcut, desktop, name = key(args[0]), clean(args[1]), clean(args[2])
        if desktop.startswith('-') or '/' in desktop:
            raise ValueError('Invalid desktop entry ID')
        external = [b for b in external_bindings() if b['key'] == shortcut]
        conflicts = [{'name': b['name'], 'external': True, 'submap': b.get('submap', '')} for b in external]
        if shortcut in data['shortcuts']:
            conflicts.append({'name': data['shortcuts'][shortcut]['name'], 'external': False})
        if conflicts and (action != 'overwrite' or len(args) < 4 or json.loads(args[3]) != conflicts):
            raise Conflict(shortcut, conflicts)
        if any(b.get('submap') for b in external):
            raise ValueError('This shortcut belongs to a Hyprland submap. Edit it in that configuration.')
        if external:
            data['suppressed'] = sorted(set(data.get('suppressed', [])) | {shortcut})
        data['shortcuts'][shortcut] = {'id': desktop, 'name': name}
    elif action == 'remove':
        shortcut = key(args[0])
        external = [b for b in external_bindings() if b['key'] == shortcut]
        if any(b.get('submap') for b in external):
            raise ValueError('This shortcut belongs to a Hyprland submap. Edit it in that configuration.')
        if external:
            data['suppressed'] = sorted(set(data.get('suppressed', [])) | {shortcut})
        data['shortcuts'].pop(shortcut, None)
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
            result = {'ok': False, 'error': str(error)}
            if isinstance(error, Conflict):
                result['conflicts'] = error.bindings
            print(json.dumps(result))
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
