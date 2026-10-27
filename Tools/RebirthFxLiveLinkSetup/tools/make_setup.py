#!/usr/bin/env python3
"""Packs the Rebirth FX Live Link Setup exe.

Setup.exe = the stub (built from src/Setup.cpp) + the files of the two parts + an index + a footer:

  game    -> <game>\\End\\Binaries\\Win64\\ue4ss\\Mods\\RebirthLiveLink\\   (the UE4SS mod: Scripts\\main.lua)
  plugin  -> <End project>\\Plugins\\RebirthFxLiveLink\\                  (the editor plugin: the Rebirth FX menu)

Usage (Windows or Linux, Python 3.8+, standard library only):

  make_setup.py --stub Setup.stub.exe --game <mod folder> --plugin <plugin folder> --out-dir <folder>

<mod folder> holds Scripts\\main.lua and README.txt (enabled.txt is optional); <plugin folder> holds
RebirthFxLiveLink.uplugin, README.txt, Binaries\\Win64\\UE4Editor-RebirthFxLiveLink.dll, Binaries\\Win64\\UE4Editor.modules,
Source\\ and Content\\Python\\. The version comes from main.lua (local VERSION = "1.5").
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import struct
import sys
import zlib

FOOTER_MAGIC = b"RFLLPAY1"
FOOTER = struct.Struct("<8sQQQII")
assert FOOTER.size == 40

PRODUCT = "Rebirth FX Live Link"
FILE_STEM = "RebirthFxLiveLink-Setup"
MODULE = "RebirthFxLiveLink"
PLUGIN_FILE = "RebirthFxLiveLink.uplugin"
PLUGIN_DLL = "Binaries/Win64/UE4Editor-RebirthFxLiveLink.dll"
PLUGIN_MODULES = "Binaries/Win64/UE4Editor.modules"
UE4SS_TAG = "c0a8d4c"
SKIP_SUFFIXES = (".pdb", ".pyc", ".bak", ".orig", ".rej", "~", ".tmp")

RESERVED = {"con", "prn", "aux", "nul", "conin$", "conout$"} | {"com%d" % i for i in range(10)} | {"lpt%d" % i for i in range(10)}


def safe_relative_path(path):
    """The rules Setup.exe checks (SetupCore::SafeRelativePath): a Setup with any other name refuses to start."""
    if not path or len(path.encode("utf-8")) > 200 or path[0] == "/" or path[-1] == "/":
        return False
    for part in path.split("/"):
        if part in ("", ".", "..") or part[-1] in ". ":
            return False
        if any(ord(c) < 32 or c in ':*?"<>|\\' for c in part):
            return False
        if part.split(".")[0].rstrip(" ").lower() in RESERVED:
            return False
    return True


def fail(message):
    print("make_setup: " + message, file=sys.stderr)
    sys.exit(1)


def read(path):
    with open(path, "rb") as f:
        return f.read()


def rel_files(root, sub=""):
    """Relative '/' paths of the files under root/sub, sorted, skipping build leftovers and Python caches."""
    base = os.path.join(root, sub) if sub else root
    out = []
    for folder, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in ("Intermediate", "Saved", "Backups", "__pycache__"))
        for name in sorted(files):
            if name.lower().endswith(SKIP_SUFFIXES) or ".bak-" in name.lower():
                continue
            out.append(os.path.relpath(os.path.join(folder, name), root).replace(os.sep, "/"))
    return out


def lua_version(text):
    """SetupCore::LuaVersion: the line  local VERSION = "1.5"  of main.lua."""
    m = re.search(r'(?m)^local VERSION\s*=\s*"([0-9.]+)"', text)
    return m.group(1) if m else None


def main():
    parser = argparse.ArgumentParser(description="Packs the Rebirth FX Live Link Setup exe.")
    parser.add_argument("--stub", required=True, help="Setup.stub.exe (built from src/Setup.cpp)")
    parser.add_argument("--game", required=True, help="the UE4SS mod folder (Scripts\\main.lua, README.txt, enabled.txt)")
    parser.add_argument("--plugin", required=True, help="the editor plugin folder (RebirthFxLiveLink.uplugin, Binaries, Source, Content)")
    parser.add_argument("--out", help="the Setup exe to write")
    parser.add_argument("--out-dir", help="write RebirthFxLiveLink-Setup-<version>.exe (and its file list) here instead")
    parser.add_argument("--list", help="also write a list of the packed files with their MD5s here")
    parser.add_argument("--strict", action="store_true", help="fail (not warn) when the plugin DLL is older than its sources")
    args = parser.parse_args()

    def warn(message):
        if args.strict:
            fail(message)
        print("make_setup: WARNING: " + message, file=sys.stderr)

    if bool(args.out) == bool(args.out_dir):
        fail("give one of --out and --out-dir")
    stub = read(args.stub)
    if stub[:2] != b"MZ":
        fail(args.stub + " is not an exe")
    if stub[-FOOTER.size:][:8] == FOOTER_MAGIC:
        fail(args.stub + " already has a payload; pack from the stub")

    entries = []  # (component, flags, rel, data)

    # ---- game part (the UE4SS mod) ----
    game = args.game
    script_path = os.path.join(game, "Scripts", "main.lua")
    if not os.path.isfile(script_path):
        fail("no " + script_path)
    script = read(script_path)
    version = lua_version(script.decode("utf-8", errors="replace"))
    if not version:
        fail(script_path + " has no  local VERSION = \"x.y\"  line")
    if b"RebirthLiveLink" not in script:
        fail(script_path + " is not the RebirthLiveLink mod")
    entries.append(("game", "", "Scripts/main.lua", script))
    readme_game = os.path.join(game, "README.txt")
    if not os.path.isfile(readme_game):
        fail("no " + readme_game)
    entries.append(("game", "", "README.txt", read(readme_game)))
    enabled = os.path.join(game, "enabled.txt")
    entries.append(("game", "keep", "enabled.txt", read(enabled) if os.path.isfile(enabled) else b""))

    # ---- plugin part (the editor plugin) ----
    plugin = args.plugin
    for need in (PLUGIN_FILE, PLUGIN_DLL, PLUGIN_MODULES, "README.txt", "Content/Python/init_unreal.py"):
        if not os.path.isfile(os.path.join(plugin, *need.split("/"))):
            fail("missing " + os.path.join(plugin, need))
    try:
        uplugin = json.loads(read(os.path.join(plugin, PLUGIN_FILE)).decode("utf-8-sig"))
        modules = json.loads(read(os.path.join(plugin, *PLUGIN_MODULES.split("/"))).decode("utf-8-sig"))
    except ValueError as e:
        fail("bad plugin JSON: %s" % e)
    plugin_version = str(uplugin.get("VersionName", "?"))
    build_id = str(modules.get("BuildId", ""))
    if MODULE not in modules.get("Modules", {}):
        fail(PLUGIN_MODULES + " doesn't list " + MODULE)
    if read(os.path.join(plugin, *PLUGIN_DLL.split("/")))[:2] != b"MZ":
        fail(PLUGIN_DLL + " is not a DLL")
    sources = rel_files(plugin, "Source")
    if not any(s.endswith(".Build.cs") for s in sources):
        fail("no Source\\...\\*.Build.cs under " + plugin)
    newest_source = max(os.path.getmtime(os.path.join(plugin, *s.split("/"))) for s in sources)
    if os.path.getmtime(os.path.join(plugin, *PLUGIN_DLL.split("/"))) + 1 < newest_source:
        warn("the editor plugin DLL is older than its sources: rebuild it first (Tools\\EndEditorPlugins\\run_build_fxlink.cmd)")
    python = rel_files(plugin, "Content")
    if not any(p.endswith("/editor.py") for p in python):
        fail("no Content\\Python\\...\\editor.py under " + plugin)
    for rel in [PLUGIN_FILE, "README.txt", PLUGIN_DLL, PLUGIN_MODULES] + sources + python:
        entries.append(("plugin", "", rel, read(os.path.join(plugin, *rel.split("/")))))

    for component, flags, rel, data in entries:
        if not safe_relative_path(rel):
            fail("Setup can't install a file named %r (Windows doesn't allow that name or path)" % rel)
    seen = set()
    for component, flags, rel, data in entries:
        key = (component, rel.lower())
        if key in seen:
            fail("packed twice: " + rel)
        seen.add(key)

    # ---- write ----
    out = bytearray(stub)
    payload_offset = len(out)
    lines = ["RFLL1",
             "product\t" + PRODUCT,
             "version\t" + version,
             "plugin_version\t" + plugin_version,
             "ue4ss_tag\t" + UE4SS_TAG,
             "engine_build\t" + build_id,
             "built\t" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "readme\tplugin/README.txt"]
    listing = []
    for component, flags, rel, data in entries:
        packer = zlib.compressobj(9, zlib.DEFLATED, -15, 9)
        packed = packer.compress(data) + packer.flush()
        method = "deflate"
        if len(packed) >= len(data):
            packed, method = data, "store"
        offset = len(out) - payload_offset
        out += packed
        lines.append("\t".join(["file", component, flags or "-", str(offset), str(len(packed)), str(len(data)),
                                "%08x" % (zlib.crc32(data) & 0xFFFFFFFF), method, rel]))
        listing.append("%s  %-6s %9d  %s" % (hashlib.md5(data).hexdigest(), component, len(data), rel))
    lines.append("end")
    index = ("\n".join(lines) + "\n").encode("utf-8")
    index_offset = len(out)
    out += index
    out += FOOTER.pack(FOOTER_MAGIC, payload_offset, index_offset, len(index), zlib.crc32(index) & 0xFFFFFFFF, 1)

    if args.out_dir:
        args.out = os.path.join(args.out_dir, "%s-%s.exe" % (FILE_STEM, version))
        if not args.list:
            args.list = os.path.join(args.out_dir, "%s-%s.files.txt" % (FILE_STEM, version))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    temp = args.out + ".tmp"
    with open(temp, "wb") as f:
        f.write(out)
    os.replace(temp, args.out)
    if args.list:
        with open(args.list, "w", encoding="utf-8", newline="\n") as f:
            f.write("%s %s (editor plugin %s, UE4SS %s, engine build %s)\n" % (PRODUCT, version, plugin_version, UE4SS_TAG, build_id))
            f.write("%s  %s\n" % (hashlib.md5(out).hexdigest(), os.path.basename(args.out)))
            f.write("\n".join(listing) + "\n")
    print("%s %s (editor plugin %s): %d files, %d bytes -> %s" % (PRODUCT, version, plugin_version, len(entries), len(out), args.out))
    print("md5 " + hashlib.md5(out).hexdigest())


if __name__ == "__main__":
    main()
