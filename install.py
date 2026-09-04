#!/usr/bin/env python3
"""Link this checkout into the local shell and enable its bar widget."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

root = Path(__file__).resolve().parent
config = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
target = config / 'omarchy/plugins/digitalbase.hyper'


def call(*args):
    return subprocess.check_output(args, text=True).strip()


if '--remove' in sys.argv:
    subprocess.run([sys.executable, str(root / 'hyper.py'), 'uninstall'], check=True)
    call('omarchy', 'plugin', 'disable', 'digitalbase.hyper')
    if target.is_symlink() and target.resolve() == root:
        target.unlink()
    call('omarchy-shell', 'shell', 'rescanPlugins')
    print('Removed Hyper shortcuts and setup. Original keyboard settings restored.')
else:
    if target.exists() or target.is_symlink():
        if target.resolve() != root:
            sys.exit(f'Another plugin checkout already exists at {target}')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(root, target_is_directory=True)
    call('omarchy-shell', 'shell', 'rescanPlugins')
    for attempt in range(30):
        plugins = json.loads(call('omarchy-shell', 'shell', 'listPlugins'))
        if any(p['id'] == 'digitalbase.hyper' for p in plugins):
            break
        time.sleep(0.2)
    else:
        sys.exit('The shell did not discover Hyper. Check that omarchy-shell is running.')
    call('omarchy', 'plugin', 'enable', 'digitalbase.hyper')
    print('Hyper is installed. Click ✦ in the bar.')
