"""Replace only Resident CharaSpec in the installed CACS IoStore container.

The output is a merged copy of the existing main CACS container plus the
cooked Resident CharaSpec package. It preserves the original .pak and every
other IoStore chunk byte-for-byte. The output is staged only; install it with
CreateACharacterSystem/install_data_tail.py after reviewing the report.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import types


ROOT = Path(__file__).resolve().parents[2]
for rel in ("work/iostore", "work/cs", "work/swap1012/tools", "work/vincentfix", "work/charaspecmod"):
    sys.path.insert(0, str(ROOT / rel))

# charaspec_patch.decode is used only to verify the cooked table rows. Its
# writer dependency is not needed by this script.
stub = types.ModuleType("build_charaspec")
stub.build_package = lambda *args: None
sys.modules.setdefault("build_charaspec", stub)

from iostore import Toc  # noqa: E402
import iostore_write as W  # noqa: E402
from hdr import parse_header  # noqa: E402
import charaspec_patch as csp  # noqa: E402


GAME_ROOT = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH")
BASE_UTOC = GAME_ROOT / "End/Content/Paks/~mods/FullyPlayableCreateACharacterSystemExperience/FullyPlayableCreateACharacterSystemExperience_P.utoc"
COOKED_UTOC = Path(r"C:\FF7R2UProj\Saved\RebirthSkelCompat\ZackCACS_20261029\SingleTable4\ZackCharaSpecCook_P4.utoc")
DEFAULT_OUTPUT = Path(r"C:\FF7R2UProj\Saved\RebirthSkelCompat\ZackCACS_20261029\Merged")
PROFILE = ROOT / "GameMods/ue4ss/Mods/RebirthSkelCompat/compat/PlayableZack.json"
TABLE_SUFFIX = "/DataObject/Resident/CharaSpec.uasset"
EXPECTED_ROWS = {
    "PC0009_00_Zack_Standard_ZACK",
    "PC0009_00_Zack_NoBattle_ZACK",
    "PC0009_00_Zack_Reserve_ZACK",
    "PC0009_01_Zack_AerithRibbon_ZACK",
    "PC0009_02_Zack_Dirty_ZACK",
    "PC0009_03_Zack_StandardWet_ZACK",
    "WE0000_00_Cloud_BusterSword_ZACK",
}


def digest(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 24), b""):
            h.update(block)
    return h.hexdigest()


def decode_row_names(data: bytes) -> set[str]:
    _zen, _export, _asset, table = csp.decode(data)
    return {item[0][0] for item in table.keys}


def append_changes(old: Toc, base_ucas: Path, changes: dict[int, bytes], utoc_path: Path, tail_path: Path, mount: str) -> bytes:
    """Write a new TOC and append-only UCAS tail for existing chunk indices."""
    b = old.b
    size = base_ucas.stat().st_size
    block_size = old.blocksz
    last = old.blocks[-1]
    if size % 16 or last[0] + ((last[1] + 15) & ~15) != size:
        raise RuntimeError("The source UCAS does not end at an aligned final block.")
    if old.nmethods != 0 or old.flags & 0x4 or not old.flags & 0x8 or old.partcount != 1:
        raise RuntimeError("The source container is not the expected uncompressed indexed Rebirth container.")

    blocks = list(old.blocks)
    offlen = list(old.offlen)
    metas = bytearray(b[old.metas_off:])
    if len(metas) != 33 * old.entries:
        raise RuntimeError("Unexpected source TOC metadata size.")
    tail = bytearray()

    def put(data: bytes) -> tuple[int, int]:
        start = len(blocks) * block_size
        for offset in range(0, len(data), block_size):
            piece = data[offset:offset + block_size]
            blocks.append((size + len(tail), len(piece), len(piece), 0))
            tail.extend(piece)
            while len(tail) % 16:
                tail.append(0)
        return start, len(data)

    for index, data in sorted(changes.items()):
        offlen[index] = put(data)
        metas[33 * index:33 * index + 20] = hashlib.sha1(data).digest()

    files = dict(old.files)
    if any(not path.startswith(mount) for path in files.values()):
        raise RuntimeError("The source TOC has a path outside the game Content mount.")
    directory = W.directory_index(mount, [(files[i][len(mount):], i) for i in sorted(files)])
    header = bytearray(b[:old.hdrsize])
    struct.pack_into("<I", header, 24, old.entries)
    struct.pack_into("<I", header, 28, len(blocks))
    struct.pack_into("<I", header, 48, len(directory))

    toc = bytearray(header)
    for chunk_id in old.chunk_ids:
        toc += chunk_id
    for offset, length in offlen:
        toc += offset.to_bytes(5, "big") + length.to_bytes(5, "big")
    for position, compressed, uncompressed, method in blocks:
        toc += position.to_bytes(5, "little") + compressed.to_bytes(3, "little") + uncompressed.to_bytes(3, "little") + bytes([method])
    toc += directory + metas
    utoc_path.write_bytes(toc)
    tail_path.write_bytes(tail)
    return bytes(toc)


def main(base_utoc: Path, cooked_utoc: Path, output: Path) -> dict:
    if output.exists():
        raise RuntimeError(f"Output folder already exists; refusing to overwrite: {output}")
    base_ucas = base_utoc.with_suffix(".ucas")
    base_pak = base_utoc.with_suffix(".pak")
    if not all(p.is_file() for p in (base_utoc, base_ucas, base_pak, cooked_utoc)):
        raise FileNotFoundError("A source container file is missing.")

    old = Toc(str(base_utoc))
    new_source = Toc(str(cooked_utoc))
    table_indices = [i for i, path in old.files.items() if path.endswith(TABLE_SUFFIX)]
    source_indices = [i for i, path in new_source.files.items() if path.endswith(TABLE_SUFFIX)]
    if len(table_indices) != 1 or len(source_indices) != 1:
        raise RuntimeError(f"Expected one CharaSpec package in each container; found {table_indices} and {source_indices}.")
    table_index, source_index = table_indices[0], source_indices[0]
    if old.chunk_type(table_index) != 2 or new_source.chunk_type(source_index) != 2:
        raise RuntimeError("CharaSpec is not a package chunk.")
    table_id = old.chunk_id64(table_index)
    if new_source.chunk_id64(source_index) != table_id:
        raise RuntimeError("Cooked CharaSpec package ID does not match the CACS table package ID.")
    table_data = new_source.read(source_index)
    row_names = decode_row_names(table_data)
    missing = sorted(EXPECTED_ROWS - row_names)
    if missing:
        raise RuntimeError(f"Cooked CharaSpec is missing Zack rows: {missing}")

    profile = json.loads(PROFILE.read_text(encoding="utf-8-sig"))
    mappings = profile["characters"][0]["charaspecs"]
    absent_sources = sorted(set(mappings) - row_names)
    absent_targets = sorted(set(mappings.values()) - row_names)
    if absent_sources or absent_targets:
        raise RuntimeError(f"Profile row references are missing from the cooked table: sources={absent_sources}, targets={absent_targets}")

    old_header = old.read(0)
    container_id, store = parse_header(old_header)
    if container_id != old.container_id or old.chunk_type(0) != 10:
        raise RuntimeError("The source CACS container header is invalid.")
    package_ids = [old.chunk_id64(i) for i in range(old.entries) if old.chunk_type(i) == 2]
    entries = [
        {
            "id": package_id,
            "size": store[package_id]["size"],
            "export_count": store[package_id]["export_count"],
            "export_bundle_count": store[package_id]["export_bundle_count"],
            "load_order": store[package_id]["load_order"],
            "imports": store[package_id]["imports"],
        }
        for package_id in package_ids
    ]
    if W.container_header(container_id, entries) != old_header:
        raise RuntimeError("The existing CACS package header cannot be round-tripped safely.")
    target_entry = next(e for e in entries if e["id"] == table_id)
    target_entry["size"] = (target_entry["size"] & (3 << 62)) | len(table_data)
    new_header = W.container_header(container_id, entries)
    mount = next(v[:v.index("DataObject/")] for v in old.files.values() if v.endswith(TABLE_SUFFIX))

    output.mkdir(parents=True)
    name = base_utoc.stem
    out_utoc = output / (name + ".utoc")
    out_ucas = output / (name + ".ucas")
    out_tail = output / (name + ".ucas.tail")
    out_pak = output / (name + ".pak")
    append_changes(old, base_ucas, {0: new_header, table_index: table_data}, out_utoc, out_tail, mount)
    with out_ucas.open("wb") as dest, base_ucas.open("rb") as source:
        shutil.copyfileobj(source, dest, 1 << 24)
        with out_tail.open("rb") as tail:
            shutil.copyfileobj(tail, dest, 1 << 24)
    shutil.copy2(base_pak, out_pak)

    merged = Toc(str(out_utoc), str(out_ucas))
    if merged.container_id != old.container_id or merged.entries != old.entries:
        raise RuntimeError("Merged TOC container identity or chunk count changed unexpectedly.")
    unchanged = 0
    for i in range(old.entries):
        if merged.chunk_id64(i) != old.chunk_id64(i) or merged.chunk_type(i) != old.chunk_type(i) or merged.files.get(i) != old.files.get(i):
            raise RuntimeError(f"Chunk identity/path changed unexpectedly at index {i}.")
        actual = merged.read(i)
        expected = new_header if i == 0 else table_data if i == table_index else old.read(i)
        if actual != expected:
            raise RuntimeError(f"Chunk verification failed at index {i}.")
        if i not in (0, table_index):
            unchanged += 1
    _cid, new_store = parse_header(merged.read(0))
    if new_store[table_id]["size"] & ((1 << 62) - 1) != len(table_data):
        raise RuntimeError("Merged header has the wrong CharaSpec size.")
    if out_ucas.stat().st_size != base_ucas.stat().st_size + out_tail.stat().st_size:
        raise RuntimeError("Merged UCAS size does not equal original plus append tail.")

    report = {
        "ok": True,
        "container": name,
        "table_package": old.files[table_index],
        "table_rows": len(row_names),
        "zack_rows": sorted(EXPECTED_ROWS),
        "profile_mappings": len(mappings),
        "source_chunks": old.entries,
        "unchanged_chunks": unchanged,
        "changed_chunks": [0, table_index],
        "table_chunk_bytes": len(table_data),
        "original_ucas_bytes": base_ucas.stat().st_size,
        "append_tail_bytes": out_tail.stat().st_size,
        "merged_ucas_bytes": out_ucas.stat().st_size,
        "original_utoc_md5": digest(base_utoc),
        "original_ucas_md5": digest(base_ucas),
        "merged_utoc_md5": digest(out_utoc),
        "merged_ucas_md5": digest(out_ucas),
        "merged_utoc": str(out_utoc),
        "merged_ucas": str(out_ucas),
        "merged_ucas_tail": str(out_tail),
        "copied_pak": str(out_pak),
    }
    (output / "merge_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-utoc", type=Path, default=BASE_UTOC)
    parser.add_argument("--cooked-utoc", type=Path, default=COOKED_UTOC)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(main(args.base_utoc, args.cooked_utoc, args.output), indent=2))
