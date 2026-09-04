# ✦ Hyper for Omarchy

A native Omarchy shell plugin for Caps Lock app shortcuts. Click ✦ in the bar to set up Hyper, browse launcher apps, and manage shortcuts.

Hyper uses XKB's dedicated Mod3 modifier. Holding Caps Lock and pressing a mapped key launches the app. Caps Lock no longer toggles capitalization. This follows Raycast's interaction, using Linux's native Hyper modifier instead of emulating macOS modifiers.

Requires Omarchy's Lua-based Hyprland configuration, Quickshell shell, Python 3, `hyprctl`, `uwsm-app`, and `gtk-launch`.

## Development

The panel uses the shell's app library, so its picker matches the Apps launcher. A Python helper owns shortcut storage and a separate generated Hyprland Lua file. Existing user bindings are displayed and reserved, never overwritten.

Implementation is split into focused commits: project, configuration backend, panel, and installation with verification.
