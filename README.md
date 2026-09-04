# ✦ Hyper for Omarchy

A native Omarchy shell plugin for Caps Lock app shortcuts. Click ✦ in the bar to set up Hyper, browse launcher apps, and manage shortcuts.

Hyper uses XKB's dedicated Mod3 modifier. Holding Caps Lock and pressing a mapped key launches the app. Caps Lock no longer toggles capitalization. This follows Raycast's interaction, using Linux's native Hyper modifier instead of emulating macOS modifiers.

Requires Omarchy's Lua-based Hyprland configuration, Quickshell shell, Python 3, `hyprctl`, `uwsm-app`, and `gtk-launch`.

## Development

The panel uses the shell's app library, so its picker matches the Apps launcher. A Python helper owns shortcut storage and a separate generated Hyprland Lua file. Existing user bindings are displayed and reserved, never overwritten.

Implementation is split into focused commits: project, configuration backend, panel, and installation with verification.

## Install from this checkout

```sh
python3 install.py
```

This links the checkout to `~/.config/omarchy/plugins/digitalbase.hyper` and enables the ✦ bar widget. Keep the checkout in place. No root access or additional keyboard daemon is needed. If developing through the symlink, run `omarchy restart shell` after QML changes, because the shell may retain cached components.

After publishing this repository, it can also be installed with Omarchy's normal `omarchy plugin add <repository-url> --enable --yes` command.

## Use

1. Click ✦ on the right of the bar. The panel opens on assigned shortcuts; the full app catalog appears only after choosing Add shortcut. Turn on **Use Caps Lock as Hyper**. The toggle reflects the current keyboard configuration.
2. Choose **Add shortcut**, search for an app, and choose it.
3. Enter a key such as `A`, `Shift+A`, `Return`, or `F12`, then save.
4. Hold Caps Lock and press that key to launch the app.

Assigned shortcuts show the app icon and launcher name first, with the key combination on the right. The picker uses the same app library and hidden-app filters as Omarchy's Apps menu. Custom bindings that cannot be matched to a launcher entry retain their binding label and use a generic app icon. Click ✦ again, click outside the panel, or press Escape to close it. Launching uses `uwsm-app -- gtk-launch`, matching Omarchy's launcher, including terminal apps and web apps with desktop entries. It does not assign arbitrary system-menu actions. Launching an already-running app follows that app's usual launcher behavior; it does not guarantee window focusing.

**Config** rows show existing Hyper bindings from Hyprland. Edit those in your existing configuration. Hyper reserves their key combinations and will not replace them. Shortcuts added in this panel can be removed here. To change an assignment, remove it and add its replacement.

The **Use Caps Lock as Hyper** toggle is on when Caps Lock is mapped to Hyper, including mappings in your existing Hyprland configuration. Turning it off explicitly restores normal Caps Lock. Turning it on maps Caps Lock to Hyper again. Both choices persist across restarts and preserve your saved shortcuts and unrelated keyboard options.

The plugin writes its override after your existing input configuration. It does not rewrite your personal `input.lua`. Uninstalling removes the override and restores the configuration you had before using the plugin.

```sh
omarchy-shell digitalbase.hyper toggle
omarchy-shell digitalbase.hyper add
omarchy-shell digitalbase.hyper info
```

## Storage and removal

Settings live in `$XDG_CONFIG_HOME/omarchy-hyper/state.json`, defaulting to `~/.config`. The helper generates `hypr/omarchy-hyper.lua` and appends a marked `dofile` to `hypr/hyprland.lua`. It backs up the original main file to `hyprland.lua.before-hyper`, checks configuration errors, and restores the previous files if applying a change fails. Writes are serialized with a file lock.

Restore keyboard settings and remove this local installation:

```sh
python3 install.py --remove
```

For an installation made through `omarchy plugin add`, first run `python3 ~/.config/omarchy/plugins/digitalbase.hyper/hyper.py uninstall`, then `omarchy plugin remove digitalbase.hyper`. Disabling a bar widget alone does not remove persistent Hyprland shortcuts.

## Verification

```sh
python3 -m unittest discover -s tests -v
python3 hyper.py status
hyprctl configerrors
```

Tests cover conflicting assignments, safe quoting, setup option preservation, repeated installation of the config include, removal, and rollback. On the development machine the panel was loaded in the live shell, the picker returned 63 launcher entries, and a temporary F12 assignment was registered through Hyprland and then removed. Physical keyboard behavior on a fresh Caps Lock setup still needs a manual check on a machine without a pre-existing Hyper mapping.

Inspired by [Raycast Hyper Key](https://manual.raycast.com/hyper-key).
