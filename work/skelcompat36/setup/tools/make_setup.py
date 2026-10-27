#!/usr/bin/env python3
"""Packs the Create a Character System Setup exe.

Setup.exe = the stub (built from src/Setup.cpp) + the files of the two parts + an index + a footer:

  game    -> <game>\\End\\Binaries\\Win64\\ue4ss\\Mods\\RebirthSkelCompat\\  (the UE4SS mod)
  plugin  -> <End project>\\Plugins\\RebirthSkelCompat\\                     (the editor plugin)

Usage (Windows or Linux, Python 3.8+, standard library only):

  make_setup.py --stub Setup.stub.exe --game <mod folder> --plugin <plugin folder> --out <Setup.exe>

<mod folder> holds dlls\\main.dll and README.txt (compat\\example.json.txt and enabled.txt are optional);
<plugin folder> holds RebirthSkelCompat.uplugin, Binaries\\Win64\\UE4Editor-RebirthSkelCompatEditor.dll,
Binaries\\Win64\\UE4Editor.modules and Source\\. The version comes from main.dll unless --version is given.
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

FOOTER_MAGIC = b"CACSPAY1"
FOOTER = struct.Struct("<8sQQQII")
assert FOOTER.size == 40

PLUGIN_DLL = "Binaries/Win64/UE4Editor-RebirthSkelCompatEditor.dll"
PLUGIN_MODULES = "Binaries/Win64/UE4Editor.modules"
SKIP_SUFFIXES = (".pdb", ".bak", ".orig", ".rej", "~", ".tmp")


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
    """Relative '/' paths of the files under root/sub, sorted, skipping build leftovers."""
    base = os.path.join(root, sub) if sub else root
    out = []
    for folder, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in ("Intermediate", "Saved", "Backups", "__pycache__"))
        for name in sorted(files):
            if name.lower().endswith(SKIP_SUFFIXES) or ".bak-" in name.lower():
                continue
            full = os.path.join(folder, name)
            out.append(os.path.relpath(full, root).replace(os.sep, "/"))
    return out


def dll_versions(data):
    """The standalone wide-string literals of main.dll that look like a version ("3.4.1"): ModVersionText.
    The linker may put the literal right after other constant data (3.7.1's follows a float, 00 00 80 3F), so what
    comes before it only has to be no printable character ("in 3.6.3" is a sentence, not the version)."""
    found = set()
    for m in re.finditer(rb"((?:[0-9]\x00)+\.\x00(?:[0-9]\x00)+\.\x00(?:[0-9]\x00)+)\x00\x00", data):
        start = m.start(1)
        if start % 2:
            continue
        if start >= 2 and 0x20 <= (data[start - 2] | (data[start - 1] << 8)) < 0x7F:
            continue
        found.add(m.group(1).decode("utf-16-le"))
    return sorted(found)


def source_version(path):
    m = re.search(r'ModVersionText\[\]\s*=\s*L"([0-9.]+)"', read(path).decode("utf-8", errors="replace"))
    return m.group(1) if m else None


def ue4ss_tag(data):
    """The UE4SS build main.dll was built against, from its starting line ("UE4SS c0a8d4c SDK")."""
    for text in (data.decode("utf-16-le", errors="ignore"), data[1:].decode("utf-16-le", errors="ignore")):
        m = re.search(r"UE4SS ([0-9a-f]{7}) SDK", text)
        if m:
            return m.group(1)
    return None


def main():
    parser = argparse.ArgumentParser(description="Packs the Create a Character System Setup exe.")
    parser.add_argument("--stub", required=True, help="Setup.stub.exe (built from src/Setup.cpp)")
    parser.add_argument("--game", help="the UE4SS mod folder (dlls\\main.dll, README.txt, compat\\example.json.txt)")
    parser.add_argument("--main-dll", help="main.dll to pack (instead of <game>\\dlls\\main.dll)")
    parser.add_argument("--example", help="compat\\example.json.txt to pack (instead of the --game folder's)")
    parser.add_argument("--plugin", required=True, help="the editor plugin folder (RebirthSkelCompat.uplugin, Binaries, Source)")
    parser.add_argument("--out", help="the Setup exe to write")
    parser.add_argument("--out-dir", help="write CreateACharacterSystem-Setup-<version>.exe (and its file list) here instead")
    parser.add_argument("--version", help="the system version (default: the one main.dll reports)")
    parser.add_argument("--source", help="RebirthSkelCompat.cpp: main.dll must report its ModVersionText")
    parser.add_argument("--readme", help="README to show and install (default: <game>\\README.txt)")
    parser.add_argument("--list", help="also write a list of the packed files with their MD5s here")
    parser.add_argument("--strict", action="store_true", help="fail (not warn) when a DLL is older than its sources")
    args = parser.parse_args()
    warnings = []

    def warn(message):
        if args.strict:
            fail(message)
        warnings.append(message)
        print("make_setup: WARNING: " + message, file=sys.stderr)

    if not args.game and not (args.main_dll and args.readme):
        fail("give --game, or --main-dll and --readme")
    if bool(args.out) == bool(args.out_dir):
        fail("give one of --out and --out-dir")
    stub = read(args.stub)
    if stub[:2] != b"MZ":
        fail(args.stub + " is not an exe")
    if stub[-FOOTER.size:][:8] == FOOTER_MAGIC:
        fail(args.stub + " already has a payload; pack from the stub")

    entries = []  # (component, flags, rel, data)

    # ---- game part (the UE4SS mod) ----
    game = args.game or ""
    main_dll = args.main_dll or os.path.join(game, "dlls", "main.dll")
    if not os.path.isfile(main_dll):
        fail("no " + main_dll)
    main_data = read(main_dll)
    if main_data[:2] != b"MZ":
        fail(main_dll + " is not a DLL")
    reported = dll_versions(main_data)
    version = args.version
    if not version:
        if len(reported) != 1:
            fail("main.dll has %s version literals (%s); pass --version" % (len(reported) or "no", ", ".join(reported)))
        version = reported[0]
    elif version not in reported:
        fail("main.dll doesn't report %s (it has %s)" % (version, ", ".join(reported) or "no version"))
    if args.source:
        wanted = source_version(args.source)
        if wanted and wanted != version:
            fail("main.dll is %s but %s says %s: build the DLL first" % (version, args.source, wanted))
        newest = max(os.path.getmtime(os.path.join(d, n)) for d, _, ns in os.walk(os.path.dirname(os.path.abspath(args.source))) for n in ns)
        if os.path.getmtime(main_dll) + 1 < newest:
            warn("main.dll is older than its sources in " + os.path.dirname(os.path.abspath(args.source)))
    tag = ue4ss_tag(main_data) or "c0a8d4c"
    entries.append(("game", "", "dlls/main.dll", main_data))
    readme_path = args.readme or os.path.join(game, "README.txt")
    if not os.path.isfile(readme_path):
        fail("no README " + readme_path)
    readme = read(readme_path)
    entries.append(("game", "", "README.txt", readme))
    example = args.example or (os.path.join(game, "compat", "example.json.txt") if game else "")
    if example and os.path.isfile(example):
        entries.append(("game", "", "compat/example.json.txt", read(example)))
    elif args.example:
        fail("no " + args.example)
    enabled = os.path.join(game, "enabled.txt") if game else ""
    entries.append(("game", "keep", "enabled.txt", read(enabled) if enabled and os.path.isfile(enabled) else b""))

    # ---- plugin part (the editor plugin) ----
    plugin = args.plugin
    uplugin_path = os.path.join(plugin, "RebirthSkelCompat.uplugin")
    for need in (uplugin_path, os.path.join(plugin, PLUGIN_DLL), os.path.join(plugin, PLUGIN_MODULES)):
        if not os.path.isfile(need):
            fail("missing " + need)
    try:
        uplugin = json.loads(read(uplugin_path).decode("utf-8-sig"))
        modules = json.loads(read(os.path.join(plugin, PLUGIN_MODULES)).decode("utf-8-sig"))
    except ValueError as e:
        fail("bad plugin JSON: %s" % e)
    plugin_version = str(uplugin.get("VersionName", "?"))
    build_id = str(modules.get("BuildId", ""))
    if "RebirthSkelCompatEditor" not in modules.get("Modules", {}):
        fail(PLUGIN_MODULES + " doesn't list RebirthSkelCompatEditor")
    sources = rel_files(plugin, "Source")
    if not any(s.endswith(".Build.cs") for s in sources):
        fail("no Source\\...\\*.Build.cs under " + plugin)
    newest_source = max(os.path.getmtime(os.path.join(plugin, *s.split("/"))) for s in sources)
    if os.path.getmtime(os.path.join(plugin, PLUGIN_DLL)) + 1 < newest_source:
        warn("the editor plugin DLL is older than its sources: rebuild the editor plugins first")
    for rel in ["RebirthSkelCompat.uplugin", PLUGIN_DLL, PLUGIN_MODULES] + sources:
        entries.append(("plugin", "", rel, read(os.path.join(plugin, *rel.split("/")))))
    entries.append(("plugin", "", "README.txt", readme))

    for component, flags, rel, data in entries:
        if not safe_relative_path(rel):
            fail("Setup can't install a file named %r (Windows doesn't allow that name or path)" % rel)

    # ---- write ----
    out = bytearray(stub)
    payload_offset = len(out)
    lines = ["CACS1",
             "product\tCreate a Character System",
             "version\t" + version,
             "plugin_version\t" + plugin_version,
             "ue4ss_tag\t" + tag,
             "engine_build\t" + build_id,
             "built\t" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "readme\tgame/README.txt"]
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
        args.out = os.path.join(args.out_dir, "CreateACharacterSystem-Setup-%s.exe" % version)
        if not args.list:
            args.list = os.path.join(args.out_dir, "CreateACharacterSystem-Setup-%s.files.txt" % version)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    temp = args.out + ".tmp"
    with open(temp, "wb") as f:
        f.write(out)
    os.replace(temp, args.out)
    if args.list:
        with open(args.list, "w", encoding="utf-8", newline="\n") as f:
            f.write("Create a Character System %s (editor plugin %s, UE4SS %s, engine build %s)\n" % (version, plugin_version, tag, build_id))
            f.write("%s  %s\n" % (hashlib.md5(out).hexdigest(), os.path.basename(args.out)))
            f.write("\n".join(listing) + "\n")
    print("Create a Character System %s (editor plugin %s): %d files, %d bytes -> %s"
          % (version, plugin_version, len(entries), len(out), args.out))
    print("md5 " + hashlib.md5(out).hexdigest())


if __name__ == "__main__":
    main()
