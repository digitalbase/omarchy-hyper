# ✦ Hyper for Omarchy

A native Omarchy shell plugin for Caps Lock app shortcuts. Click ✦ in the bar to set up Hyper, browse launcher apps, and manage shortcuts.

Hyper uses XKB's dedicated Mod3 modifier. Holding Caps Lock and pressing a mapped key launches the app. Caps Lock no longer toggles capitalization. This follows Raycast's interaction, using Linux's native Hyper modifier instead of emulating macOS modifiers.

Requires Omarchy's Lua-based Hyprland configuration, Quickshell shell, Python 3, `hyprctl`, `uwsm-app`, and `gtk-launch`.

## Development

The panel uses the shell's app library, so its picker matches the Apps launcher. A Python helper owns shortcut storage and a separate generated Hyprland Lua file. Existing user bindings are displayed alongside panel assignments and can be removed or overwritten through generated overrides. Their original Lua files remain intact.

## Install from this checkout

```sh
python3 install.py
```

This links the checkout to `~/.config/omarchy/plugins/digitalbase.hyper` and enables the ✦ bar widget. Keep the checkout in place. No root access or additional keyboard daemon is needed. If developing through the symlink, run `omarchy restart shell` after QML changes, because the shell may retain cached components.

After publishing this repository, it can also be installed with Omarchy's normal `omarchy plugin add <repository-url> --enable --yes` command.

## Use

1. Click ✦ on the right of the bar. The panel opens on assigned shortcuts; the full app catalog appears only after choosing Add shortcut. Use the toggle in the header to turn Hyper on. The subtitle shows the current on/off state.
2. Choose **Add shortcut**, search for an app, and click its row.
3. Enter a key such as `A`, `Shift+A`, `Return`, or `F12`, then save.
4. Hold Caps Lock and press that key to launch the app.

Assigned shortcuts show the app icon and launcher name first, with the key combination on the right. The picker uses the same app library and hidden-app filters as Omarchy's Apps menu. Custom bindings that cannot be matched to a launcher entry retain their binding label and use a generic app icon. Click ✦ again, click outside the panel, or press Escape to close it. Launching uses `uwsm-app -- gtk-launch`, matching Omarchy's launcher, including terminal apps and web apps with desktop entries. It does not assign arbitrary system-menu actions. Launching an already-running app follows that app's usual launcher behavior; it does not guarantee window focusing.

Every assigned shortcut has a **Remove** action. If a key is already in use, saving names the conflicting app and offers **Overwrite**. The backend rechecks the conflict before replacing it, so a changed assignment requires a fresh confirmation.

Removing or overwriting a binding from your existing Hyprland config adds an `hl.unbind` to the generated file. These overrides survive reloads without editing the original binding declarations. Removing a replacement keeps the original shortcut disabled. Uninstalling removes all overrides and brings back the original bindings. Bindings inside named Hyprland submaps must still be edited in their source configuration.

The header toggle is on when Caps Lock is mapped to Hyper, including mappings in your existing Hyprland configuration. Turning it off explicitly restores normal Caps Lock. Turning it on maps Caps Lock to Hyper again. Both choices persist across restarts and preserve your saved shortcuts and unrelated keyboard options.

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

Tests cover named conflicts, overwrite confirmation, physical-key removal, safe quoting, setup option preservation, repeated installation of the config include, removal, and rollback. On the development machine the panel was loaded in the live shell, the picker returned 63 launcher entries, and a temporary F12 assignment was registered through Hyprland and then removed. Physical keyboard behavior on a fresh Caps Lock setup still needs a manual check on a machine without a pre-existing Hyper mapping.

Inspired by [Raycast Hyper Key](https://manual.raycast.com/hyper-key).

## License

[MIT](LICENSE), copyright Digitalbase.

## Configuration access

Hyper reads desktop entries through Omarchy's app library, current keyboard options and bindings through `hyprctl`, and literal binding declarations from `~/.config/hypr/*.lua` when Hyprland omits a physical key label. It runs a local Python helper for settings changes and launches apps through their desktop entries. It makes no network requests of its own and requires no root privileges.

Enabling or disabling Hyper, saving, overwriting, and removing shortcuts changes the generated Lua file and its marked include in the main Hyprland config. Each change comes from a user action in the panel. The plugin creates a backup before its first configuration change and rolls back failed changes. Installation enables the bar widget but does not remap Caps Lock until the header toggle is used.
