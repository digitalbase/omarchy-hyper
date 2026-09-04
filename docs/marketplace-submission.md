# Marketplace submission draft

Title: `[Plugin]: Hyper`

Repository: `https://github.com/digitalbase/omarchy-hyper`.
The owner approved public publication under MIT and the submission checklist.
The issue body below is prepared for the marketplace.

---

### Repository URL

https://github.com/digitalbase/omarchy-hyper

### Category

Productivity

### Tags

bar, hyprland, launcher

### Suggest a missing tag

_No response_

### Maintainer notes

Hyper adds a native ✦ bar panel for Caps Lock app shortcuts. It lists existing
Hyper bindings, uses Omarchy's launcher app catalog, and supports named conflict
confirmation before overwriting a shortcut.

Requires Omarchy's Lua-based Hyprland configuration, its Quickshell shell,
Python 3, hyprctl, uwsm-app, and gtk-launch. No root privileges or additional
keyboard daemon are needed.

Explicit user actions write a separate generated Hyprland Lua file and a marked
include in the user's main config. Existing bindings are suppressed with
hl.unbind rather than editing their original declarations. Configuration
changes are backed up, validated, and rolled back on failure. Removal restores
the original user configuration; the README documents the cleanup command that
must run before removing the plugin checkout.

Eleven automated tests pass. Live checks confirmed named conflicts, overwrite,
removal, and switching between caps:hyper and caps:capslock without Hyprland
configuration errors. New shortcuts use the standard desktop launcher;
application-specific focus behavior is not guaranteed.

### Submission checklist

- [x] The repository is public and contains installation and removal instructions.
- [x] I have documented the plugin license and any external dependencies.
- [x] I confirm that I own or have permission to submit this plugin and its preview assets.
- [x] The plugin does not overwrite user configuration without explicit consent.
- [x] I understand that approval is for listing and is not a security review.
