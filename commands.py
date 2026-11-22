"""Discover and invoke launcher commands by ID on the current machine."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/|[,}\]]|[^\s]', re.S)
SYSTEM_CONFIRM = {"system.shutdown", "system.reboot", "system.logout", "system.firmware",
                  "system.suspend", "system.hibernate"}
OMA_KINDS = {"builtin", "script", "omarchy-action", "omarchy-menu", "omarchy-link"}


def read_menu(path):
    if not path.is_file():
        return {}
    tokens = [token for token in TOKEN.findall(path.read_text())
              if not token.startswith(("//", "/*"))]
    return json.loads("".join(token for index, token in enumerate(tokens)
                              if token != "," or tokens[index + 1:index + 2] not in (["}"], ["]"])))


def menu():
    base = Path(os.environ.get("OMARCHY_PATH") or "/usr/share/omarchy")
    config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    items = read_menu(base / "default/omarchy/omarchy-menu.jsonc")
    for key, value in read_menu(config / "omarchy/extensions/omarchy-menu.jsonc").items():
        if value is None:
            items.pop(key, None)
        elif isinstance(value, dict):
            items[key] = {**items.get(key, {}), **value}
    return items


def call_omacast(method, payload):
    result = subprocess.run(["omacast", "call", method, json.dumps(payload)],
                            capture_output=True, text=True, check=True, timeout=5)
    response = json.loads(result.stdout)
    if not response.get("ok"):
        raise ValueError(response.get("error") or "OMAcast command failed")
    return response.get("data")


def omacast_rows(query):
    if not shutil.which("omacast"):
        return []
    try:
        sections = call_omacast("rootSearch.search", {"query": query, "filter": "commands"})
    except (OSError, ValueError, subprocess.SubprocessError):
        return []
    return [row for section in sections for row in section["rows"]
            if row.get("kind") in OMA_KINDS and not row.get("disabled")]


def catalog(query):
    items = menu()
    needle = query.casefold().strip()
    rows = [{"kind": "menu", "id": key, "name": item["label"], "description": "Omarchy menu"}
            for key, item in items.items() if isinstance(item, dict) and item.get("label")
            and needle in (key + " " + item["label"]).casefold()]
    rows.extend({"kind": "omacast", "id": row["id"], "name": row["title"], "description": "OMAcast"}
                for row in omacast_rows(query))
    return sorted(rows, key=lambda row: (row["name"].casefold(), row["kind"], row["id"]))


def invoke(kind, target, name):
    if kind == "menu":
        items = menu()
        item = items.get(target)
        if not isinstance(item, dict):
            raise ValueError("This Omarchy menu entry is unavailable")
        # The route API invokes leaf actions without checking menu row guards.
        if item.get("action") and (target in SYSTEM_CONFIRM or item.get("when") or item.get("disabled")):
            target = target.rpartition(".")[0]
            if not target or items.get(target, {}).get("action") or items.get(target, {}).get("target"):
                target = "root"
        subprocess.run(["omarchy", "menu", "summon", target], check=True)
        return

    if kind != "omacast":
        raise ValueError("Unknown launcher command source")
    rows = omacast_rows(name)
    row = next((row for row in rows if row["id"] == target), None)
    if row is None:
        raise ValueError("This OMAcast command is unavailable")
    if target.startswith("omarchy:") and target.removeprefix("omarchy:") in SYSTEM_CONFIRM:
        show_omacast(name)
        return
    if any(arg.get("required") for arg in row.get("arguments") or []):
        show_omacast(name)
        return
    outcome = call_omacast("rootSearch.performAction", {"id": target, "action": "open"}) or {}
    if outcome.get("confirm"):
        show_omacast(name)
    elif outcome.get("push"):
        # The direct entry point displays the view returned by the backend.
        subprocess.run(["omacast", "run", target], check=True)


def show_omacast(query):
    subprocess.run(["omarchy-shell", "shell", "summon", "typecraft.omacast",
                    json.dumps({"query": query})], check=True)
