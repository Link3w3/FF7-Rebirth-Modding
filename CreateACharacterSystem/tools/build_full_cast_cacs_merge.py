"""Merge the full-cast Resident CharaSpec table and matching row DataAssets.

The existing CACS IoStore is copied as-is, with new uncompressed blocks appended.
All original chunk IDs and original UCAS bytes are preserved; only its package
store header and Resident CharaSpec chunk are replaced, and CharaSpec aliases
for the seven new party characters are appended.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
for rel in ("work/iostore", "work/cs", "work/swap1012/tools", "work/vincentfix", "work/charaspecmod"):
    sys.path.insert(0, str(ROOT / rel))

stub = types.ModuleType("build_charaspec")
def rebuild_package(data, package, export):
    header = bytearray(data[:package.header_end])
    struct.pack_into("<Q", header, package.exp_off + 8, len(export))
    return bytes(header) + export
stub.build_package = rebuild_package
sys.modules.setdefault("build_charaspec", stub)

import iostore
from iostore import Toc
import iostore_write as W
from hdr import parse_header
from zen import Zen
import zenrename
import charaspec_patch as csp

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH")
PAKS = GAME / "End/Content/Paks"
MAIN = GAME / "End/Content/Paks/~mods/FullyPlayableCreateACharacterSystemExperience/FullyPlayableCreateACharacterSystemExperience_P.utoc"
FIXES = ROOT.parent / "fixes" / "full_cast_charspec_20261030"
CANDIDATE_TABLE = FIXES / "container" / "CACSFullCastResidentCharaSpec_P.utoc"
CONFIG = FIXES / "FullyPlayableCreateACharacterSystemExperience.json"
PLAN = FIXES / "party_playable_plan.json"
OUTPUT = FIXES / "merged_candidate_all_weapons_v2"
OODLE_DLL = Path(r"C:\FF7R2UProj\Tools\RemakeImporter\ooz.dll")
MOUNT = "../../../End/Content/"
TABLE_PATH = MOUNT + "DataObject/Resident/CharaSpec.uasset"
PARTY_TOKENS = ("BARRET", "TIFA", "AERITH", "RED XIII", "YUFFIE", "CAIT SITH", "CID")
WEAPON_PREFIXES = {
    "BARRET": "WE0001_", "TIFA": "WE0002_", "AERITH": "WE0003_",
    "RED XIII": "WE0004_", "YUFFIE": "WE0005_", "CAIT SITH": "WE0007_",
}
CLOUD_WEAPON_ROWS = (
    "WE0000_00_Cloud_BusterSword",
    "WE0000_11_Cloud_END2Weapon1", "WE0000_12_Cloud_END2Weapon2",
    "WE0000_13_Cloud_END2Weapon3", "WE0000_14_Cloud_END2Weapon4",
    "WE0000_15_Cloud_END2Weapon5", "WE0000_16_Cloud_END2Weapon6",
    "WE0000_17_Cloud_Umbrella",
)


def token_key(value: str) -> str:
    return "".join(ch for ch in value.casefold() if ch.isalnum())


def install_oodle() -> None:
    lib = ctypes.CDLL(str(OODLE_DLL))
    lib.Ooz_Decompress.restype = ctypes.c_int
    lib.Ooz_Decompress.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_size_t,
                                  ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.c_int]

    def decompress(data: bytes, size: int) -> bytes:
        buf = ctypes.create_string_buffer(size + 64)
        result = lib.Ooz_Decompress(data, len(data), buf, size, 0, 0, 0, None, 0, None, None, None, 0, 0)
        if result != size:
            raise RuntimeError(f"Oodle decompressor returned {result}; expected {size}")
        return buf.raw[:size]
    iostore.oodle = decompress


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def fullname(value):
    if isinstance(value, tuple):
        value = value[0]
    if isinstance(value, bytes):
        return value.decode("utf-16-le", "ignore").strip("\0")
    return str(value)


def find_package(tocs: list[Toc], path: str) -> tuple[Toc, int]:
    folded = path.casefold()
    cache_key = tuple(id(toc) for toc in tocs)
    if getattr(find_package, "_cache_key", None) != cache_key:
        lookup = {}
        for toc in tocs:
            for i, package_path in toc.files.items():
                lookup.setdefault(package_path.casefold(), []).append((toc, i))
        find_package._lookup = lookup
        find_package._cache_key = cache_key
    hits = find_package._lookup.get(folded, [])
    if len(hits) != 1:
        raise RuntimeError(f"Expected one source package {path}; found {len(hits)}")
    return hits[0]


def append_name_map_entries(data: bytes, extra: list[str]) -> bytes:
    """Add FNames to a cooked Zen package without changing its exports."""
    z = Zen(data)
    names = list(z.names)
    for name in extra:
        if name not in names:
            names.append(name)
    if len(names) == len(z.names):
        return data
    name_batch = bytearray()
    for name in names:
        header, encoded, wide = zenrename.encode_name(name)
        name_batch += header
        if wide and (64 + len(name_batch)) & 1:
            name_batch.append(0)
        name_batch += encoded
    nm_off, nm_size = 64, len(name_batch)
    after_names = nm_off + nm_size
    pad = (8 - after_names % 8) % 8
    nh_off = after_names + pad
    hashes = struct.pack("<Q", z.hash_version) + b"".join(struct.pack("<Q", zenrename.name_hash(n)) for n in names)
    nh_size = len(hashes)
    imports = data[z.imp_off:z.exp_off]
    exports = data[z.exp_off:z.eb_off]
    bundles = data[z.eb_off:z.graph_off]
    graph = data[z.graph_off:z.graph_off + z.graph_size]
    imp_off = nh_off + nh_size
    exp_off = imp_off + len(imports)
    eb_off = exp_off + len(exports)
    graph_off = eb_off + len(bundles)
    header_end = graph_off + len(graph)
    summary = struct.pack("<QQIIiiiiiiiiii", z.name_mapped, z.srcname_mapped, z.flags,
                          z.cooked_header_size, nm_off, nm_size, nh_off, nh_size,
                          imp_off, exp_off, eb_off, graph_off, len(graph), z.pad)
    out = bytearray(summary)
    out += name_batch + b"\0" * pad + hashes + imports + exports + bundles + graph
    if len(out) != header_end:
        raise RuntimeError("Zen package name-map expansion produced an invalid header size")
    out += data[z.header_end:]
    return bytes(out)


def write_toc_with_appends(old: Toc, base_ucas: Path, new_header: bytes, table_data: bytes,
                           additions: list[dict], out_utoc: Path, out_ucas: Path) -> None:
    if old.flags & 0x4 or not old.flags & 0x8 or old.partcount != 1:
        raise RuntimeError("Expected an unencrypted indexed single-part CACS container")
    size, block_size = base_ucas.stat().st_size, old.blocksz
    if old.blocks[-1][0] + ((old.blocks[-1][1] + 15) & ~15) != size:
        raise RuntimeError("The original CACS UCAS does not end at its final indexed block")

    paths = dict(old.files)
    existing = {p.casefold() for p in paths.values()}
    for addition in additions:
        if addition["path"].casefold() in existing:
            raise RuntimeError("Asset package path already exists: " + addition["path"])
        existing.add(addition["path"].casefold())

    chunk_ids = list(old.chunk_ids)
    offlen = list(old.offlen)
    blocks = list(old.blocks)
    metas = bytearray(old.b[old.metas_off:old.metas_off + 33 * old.entries])
    if len(metas) != 33 * old.entries:
        raise RuntimeError("Unexpected existing IoStore metadata size")
    tail = bytearray(b"\0" * ((-size) % 16))

    def append(data: bytes) -> tuple[int, int]:
        logical = len(blocks) * block_size
        first = logical
        for offset in range(0, len(data), block_size):
            piece = data[offset:offset + block_size]
            blocks.append((size + len(tail), len(piece), len(piece), 0))
            tail.extend(piece)
            while len(tail) % 16:
                tail.append(0)
        return first, len(data)

    header_index = next(i for i in range(old.entries) if old.chunk_type(i) == 10)
    table_index = next(i for i, p in old.files.items() if p.casefold() == TABLE_PATH.casefold())
    changed = {header_index: new_header, table_index: table_data}
    for index, data in changed.items():
        offlen[index] = append(data)
        metas[33 * index:33 * index + 20] = hashlib.sha1(data).digest()

    for addition in additions:
        data = addition["data"]
        idx = len(chunk_ids)
        chunk_ids.append(struct.pack("<QHBB", addition["id"], 0, 0, 2))
        offlen.append(append(data))
        paths[idx] = addition["path"]
        metas.extend(hashlib.sha1(data).digest() + b"\0" * 12 + b"\0")

    directory = W.directory_index(MOUNT, [(p[len(MOUNT):], i) for i, p in sorted(paths.items())])
    header = bytearray(old.b[:old.hdrsize])
    struct.pack_into("<I", header, 24, len(chunk_ids))
    struct.pack_into("<I", header, 28, len(blocks))
    struct.pack_into("<I", header, 48, len(directory))
    toc = bytearray(header)
    toc.extend(b"".join(chunk_ids))
    for offset, length in offlen:
        toc.extend(offset.to_bytes(5, "big") + length.to_bytes(5, "big"))
    for position, compressed, uncompressed, method in blocks:
        toc.extend(position.to_bytes(5, "little") + compressed.to_bytes(3, "little") +
                   uncompressed.to_bytes(3, "little") + bytes([method]))
    method_start = old.hdrsize + old.entries * 12 + old.entries * 10 + old.ncblocks * 12
    methods = old.b[method_start:method_start + old.methodlen * old.nmethods]
    if len(methods) != old.methodlen * old.nmethods:
        raise RuntimeError("Existing compression-method table is truncated")
    toc.extend(methods)
    toc.extend(directory)
    toc.extend(metas)
    out_utoc.write_bytes(toc)
    with out_ucas.open("wb") as dst, base_ucas.open("rb") as src:
        shutil.copyfileobj(src, dst, 1 << 24)
        dst.write(tail)


def build() -> dict:
    if OUTPUT.exists():
        raise RuntimeError(f"Refusing to overwrite existing output folder: {OUTPUT}")
    if not all(p.is_file() for p in (MAIN, MAIN.with_suffix(".ucas"), MAIN.with_suffix(".pak"),
                                     CANDIDATE_TABLE, CONFIG, PLAN, OODLE_DLL)):
        raise FileNotFoundError("A required main CACS file, cooked table, config, plan, or Oodle DLL is missing")
    install_oodle()
    old = Toc(str(MAIN))
    candidate = Toc(str(CANDIDATE_TABLE))
    old_tables = [i for i, p in old.files.items() if p.casefold() == TABLE_PATH.casefold()]
    candidate_tables = [i for i, p in candidate.files.items() if p.casefold() == TABLE_PATH.casefold()]
    header_indices = [i for i in range(old.entries) if old.chunk_type(i) == 10]
    if len(old_tables) != 1 or len(candidate_tables) != 1 or len(header_indices) != 1:
        raise RuntimeError(f"Bad table/header count: old={old_tables}, candidate={candidate_tables}, header={header_indices}")
    table_index, source_table_index, header_index = old_tables[0], candidate_tables[0], header_indices[0]
    new_table = candidate.read(source_table_index)
    table_zen, table_export, table_map, decoded = csp.decode(new_table)
    if len(decoded.keys) != 3838:
        raise RuntimeError(f"Expected 3,838 Resident CharaSpec rows after merge, got {len(decoded.keys)}")
    key_names = {key[0][0].casefold() for key in decoded.keys}
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    configured = {token_key(c["name"]): c for c in config["characters"]}
    planned = {token_key(p["token"]): p for p in plan["party"]}
    party_keys = {token_key(t) for t in PARTY_TOKENS}
    if not party_keys.issubset(configured) or not party_keys.issubset(planned):
        raise RuntimeError("The seven party characters are not all present in the config and asset plan")
    extra_row_names = []
    for token in PARTY_TOKENS:
        if token == "CID":
            continue
        slug = "".join(ch for ch in token if ch.isalnum()).upper()
        extra_row_names.extend(source + "_" + slug for source in CLOUD_WEAPON_ROWS[1:])
    new_table = append_name_map_entries(new_table, extra_row_names)
    table_zen, table_export, table_map, decoded = csp.decode(new_table)
    fields = {f[0][0]: i for i, f in enumerate(decoded.fields)}
    if "ContentsModel" not in fields:
        raise RuntimeError("Resident CharaSpec table is missing ContentsModel")
    rows_by_name = {key[0][0].casefold(): decoded.rows[i] for i, key in enumerate(decoded.keys)}
    row_names = [key[0][0] for key in decoded.keys]
    rows = [list(row) for row in decoded.rows]
    key_entries = [key[0] for key in decoded.keys]
    row_index = {name.casefold(): i for i, name in enumerate(row_names)}
    weapon_model_report = {}
    for token, prefix in WEAPON_PREFIXES.items():
        character = configured[token_key(token)]
        weapon_source_rows = [source for source in character["charaspecs"] if source.startswith("WE")]
        if set(weapon_source_rows) != set(CLOUD_WEAPON_ROWS):
            raise RuntimeError(f"Expected all eight Cloud weapon rows for {token}; found {weapon_source_rows}")
        available_models = [fullname(rows[i][fields["ContentsModel"]]) for i, name in enumerate(row_names)
                            if name.startswith(prefix) and "AVATAR" not in name.upper()
                            and "RESERVE" not in name.upper() and "NOBATTLE" not in name.upper()]
        if not available_models:
            raise RuntimeError(f"No native weapon CharaSpec rows found for {token} ({prefix})")
        selected_models = available_models[:len(CLOUD_WEAPON_ROWS)]
        while len(selected_models) < len(CLOUD_WEAPON_ROWS):
            selected_models.append(selected_models[-1])
        slug = "".join(ch for ch in token if ch.isalnum()).upper()
        weapon_model_report[token] = dict(zip(CLOUD_WEAPON_ROWS, selected_models))
        for cloud_source, model in zip(CLOUD_WEAPON_ROWS, selected_models):
            target = cloud_source + "_" + slug
            character["charaspecs"][cloud_source] = target
            if target.casefold() in row_index:
                idx = row_index[target.casefold()]
                rows[idx][fields["ContentsModel"]] = (model, 0)
            else:
                source_idx = row_index.get(cloud_source.casefold())
                if source_idx is None:
                    raise RuntimeError(f"Missing Cloud weapon source row {cloud_source}")
                row_index[target.casefold()] = len(row_names)
                row_names.append(target)
                key_entries.append((target, 0))
                cloned = list(rows[source_idx])
                cloned[fields["ContentsModel"]] = (model, 0)
                rows.append(cloned)
    cid = configured[token_key("CID")]
    cid["charaspecs"] = {source: target for source, target in cid["charaspecs"].items() if not source.startswith("WE")}
    if len(cid["charaspecs"]) != 26:
        raise RuntimeError(f"Expected 26 nonweapon mappings for Cid, got {len(cid['charaspecs'])}")
    cid_weapon_row = "WE0000_00_Cloud_BusterSword_CID".casefold()
    if cid_weapon_row in row_index:
        idx = row_index[cid_weapon_row]
        del row_names[idx]
        del rows[idx]
        del key_entries[idx]
        row_index = {name.casefold(): i for i, name in enumerate(row_names)}
    new_table = csp.encode(new_table, table_zen, table_export, table_map,
                           key_entries, decoded.fields, rows)
    _zcheck, _echeck, _mcheck, decoded = csp.decode(new_table)
    if len(decoded.keys) != 3879:
        raise RuntimeError(f"Expected 3,879 rows after full weapon duplication and Cid cleanup, got {len(decoded.keys)}")
    rows_by_name = {key[0][0].casefold(): decoded.rows[i] for i, key in enumerate(decoded.keys)}
    model_by_row = {name: fullname(row[fields["ContentsModel"]]) for name, row in rows_by_name.items()}
    model_by_row = {name: fullname(row[fields["ContentsModel"]]) for name, row in rows_by_name.items()}

    targets: dict[str, str] = {}
    for token in PARTY_TOKENS:
        key = token_key(token)
        character = configured[key]
        names = set(character["charaspecs"].values())
        expected = 26 if token == "CID" else 34
        if len(names) != expected:
            raise RuntimeError(f"Expected {expected} unique Cloud costume/weapon CharaSpec aliases for {token}, found {len(names)}")
        for row_name in names:
            if row_name.casefold() not in rows_by_name:
                raise RuntimeError(f"Planned alias row is missing from the cooked Resident table: {row_name}")
            if row_name.casefold() not in targets:
                targets[row_name.casefold()] = row_name

    mount_path_by_fold = {p.casefold(): (i, p) for i, p in old.files.items()}
    main_header = old.read(header_index)
    container_id, store = parse_header(main_header)
    if container_id != old.container_id:
        raise RuntimeError("Existing CACS package-store header has the wrong container ID")
    if set(store) != {old.chunk_id64(i) for i in range(old.entries) if old.chunk_type(i) == 2}:
        raise RuntimeError("Existing CACS package store does not match its package chunks")

    vanilla_tocs = []
    for utoc in PAKS.glob("pakchunk*-WindowsNoEditor.utoc"):
        vanilla_tocs.append(Toc(str(utoc)))
    sources = [old] + vanilla_tocs
    additions: list[dict] = []
    new_store_entries = []
    source_reports = []
    source_bytes: dict[tuple[int, int], bytes] = {}
    source_stores: dict[int, dict] = {}

    def get_source_data(toc: Toc, index: int) -> bytes:
        key = (id(toc), index)
        if key not in source_bytes:
            source_bytes[key] = toc.read(index)
        return source_bytes[key]

    def get_source_store(toc: Toc) -> dict:
        key = id(toc)
        if key not in source_stores:
            header_index = next(i for i in range(toc.entries) if toc.chunk_type(i) == 10)
            cid, parsed = parse_header(toc.read(header_index))
            if cid != toc.container_id:
                raise RuntimeError("Source package-store header has a mismatched container ID")
            source_stores[key] = parsed
        return source_stores[key]

    # First add a canonical CharaSpec package for every model selected by the new rows.
    models = sorted({model_by_row[name] for name in targets})
    for model in models:
        stem = "CharaSpec_" + model
        path = MOUNT + f"DataAsset/Game/CharaSpec/{stem}.uasset"
        if path.casefold() in mount_path_by_fold:
            continue
        source_toc, source_index = find_package(sources, path)
        data = get_source_data(source_toc, source_index)
        z = Zen(data)
        if len(z.exports) != 1 or z.exports[0]["name"].casefold() != stem.casefold():
            raise RuntimeError(f"Model CharaSpec package export mismatch at {path}")
        package_id = W.package_id("/Game/DataAsset/Game/CharaSpec/" + stem)
        if package_id != source_toc.chunk_id64(source_index) or package_id in store:
            raise RuntimeError(f"Model CharaSpec package ID collision or mismatch for {path}")
        source_store = get_source_store(source_toc)
        entry = dict(source_store[package_id])
        additions.append({"id": package_id, "path": path, "data": data, "kind": "canonical_model", "row": stem})
        new_store_entries.append(entry)
        mount_path_by_fold[path.casefold()] = (-1, path)
        source_reports.append({"kind": "canonical_model", "path": path, "source_container": Path(source_toc.ucas).name})

    # Build one duplicate DataAsset for each configured Cloud costume/weapon alias.
    for folded, row_name in sorted(targets.items()):
        target_stem = "CharaSpec_" + row_name
        target_path = MOUNT + f"DataAsset/Game/CharaSpec/{target_stem}.uasset"
        if target_path.casefold() in mount_path_by_fold:
            raise RuntimeError(f"Alias package already exists: {target_path}")
        model = model_by_row[folded]
        source_stem = "CharaSpec_" + model
        source_path = MOUNT + f"DataAsset/Game/CharaSpec/{source_stem}.uasset"
        source_toc, source_index = find_package(sources, source_path)
        source_data = get_source_data(source_toc, source_index)
        source_zen = Zen(source_data)
        if len(source_zen.exports) != 1 or source_zen.exports[0]["name"].casefold() != source_stem.casefold():
            raise RuntimeError(f"Matching model DataAsset export mismatch at {source_path}")
        renames = {source_stem: target_stem,
                   "/Game/DataAsset/Game/CharaSpec/" + source_stem:
                   "/Game/DataAsset/Game/CharaSpec/" + target_stem}
        alias_data = zenrename.rebuild(source_data, renames)
        alias_zen = Zen(alias_data)
        if len(alias_zen.exports) != 1 or alias_zen.exports[0]["name"].casefold() != target_stem.casefold():
            raise RuntimeError(f"CharaSpec alias rename failed for {target_path}")
        package_id = W.package_id("/Game/DataAsset/Game/CharaSpec/" + target_stem)
        if package_id in store or any(x["id"] == package_id for x in additions):
            raise RuntimeError(f"CharaSpec alias package ID collision: {target_path}")
        source_store = get_source_store(source_toc)
        source_id = source_toc.chunk_id64(source_index)
        entry = dict(source_store[source_id])
        entry["id"] = package_id
        entry["size"] = (entry["size"] & (3 << 62)) | len(alias_data)
        additions.append({"id": package_id, "path": target_path, "data": alias_data,
                          "kind": "row_alias", "row": row_name, "model": model})
        new_store_entries.append(entry)
        mount_path_by_fold[target_path.casefold()] = (-1, target_path)
        source_reports.append({"kind": "row_alias", "row": row_name, "model": model,
                               "path": target_path, "source": source_path,
                               "source_container": Path(source_toc.ucas).name})

    if len([x for x in additions if x["kind"] == "row_alias"]) != len(targets):
        raise RuntimeError("Not all planned row aliases were generated")
    old_store_entries = [dict(store[pid]) for pid in store]
    full_store_entries = old_store_entries + new_store_entries
    new_header = W.container_header(container_id, full_store_entries)
    _cid, checked_store = parse_header(new_header)
    if len(checked_store) != len(full_store_entries):
        raise RuntimeError("Expanded CACS package-store header did not round-trip")
    for addition, entry in zip(additions, new_store_entries):
        if checked_store[addition["id"]]["imports"] != entry["imports"]:
            raise RuntimeError(f"Package-store dependency list changed for {addition['path']}")
    table_entry = checked_store[old.chunk_id64(table_index)]
    table_entry["size"] = (table_entry["size"] & (3 << 62)) | len(new_table)
    full_store_entries = [dict(checked_store[pid]) for pid in checked_store]
    new_header = W.container_header(container_id, full_store_entries)

    OUTPUT.mkdir(parents=True)
    out_utoc, out_ucas, out_pak = OUTPUT / MAIN.name, OUTPUT / MAIN.with_suffix(".ucas").name, OUTPUT / MAIN.with_suffix(".pak").name
    write_toc_with_appends(old, MAIN.with_suffix(".ucas"), new_header, new_table, additions, out_utoc, out_ucas)
    shutil.copy2(MAIN.with_suffix(".pak"), out_pak)

    merged = Toc(str(out_utoc), str(out_ucas))
    if merged.container_id != old.container_id or merged.entries != old.entries + len(additions):
        raise RuntimeError("Merged CACS identity or chunk count failed structural validation")
    if merged.chunk_ids[:old.entries] != old.chunk_ids:
        raise RuntimeError("An existing CACS chunk ID changed")
    if merged.read(header_index) != new_header or merged.read(table_index) != new_table:
        raise RuntimeError("Merged package-store header or Resident table read-back failed")
    _z2, _e2, _m2, merged_rows = csp.decode(merged.read(table_index))
    if len(merged_rows.keys) != 3879:
        raise RuntimeError("Merged Resident CharaSpec table failed row-count read-back")
    for i in range(old.entries):
        if i in (header_index, table_index):
            continue
        if merged.offlen[i] != old.offlen[i] or merged.chunk_ids[i] != old.chunk_ids[i]:
            raise RuntimeError(f"An untouched CACS chunk changed at index {i}")
    for idx, addition in enumerate(additions, start=old.entries):
        if merged.files.get(idx) != addition["path"] or merged.chunk_id64(idx) != addition["id"]:
            raise RuntimeError(f"New package directory entry failed for {addition['path']}")
        raw = merged.read(idx)
        if raw != addition["data"] or Zen(raw).exports[0]["name"] != Path(addition["path"]).stem:
            raise RuntimeError(f"New CharaSpec package failed read-back: {addition['path']}")

    report = {
        "ok": True,
        "main_container": MAIN.name,
        "resident_table": old.files[table_index],
        "resident_rows": len(merged_rows.keys),
        "party_characters": list(PARTY_TOKENS),
        "weapon_models": weapon_model_report,
        "cid_weapon_mappings_removed": True,
        "row_aliases_added": len(targets),
        "canonical_model_assets_added": len([x for x in additions if x["kind"] == "canonical_model"]),
        "new_package_chunks": len(additions),
        "existing_chunks_preserved": old.entries - 2,
        "existing_ucas_bytes_preserved": MAIN.with_suffix(".ucas").stat().st_size,
        "source_assets": source_reports,
        "candidate_files": {"utoc": str(out_utoc), "ucas": str(out_ucas), "pak": str(out_pak)},
        "source_sha256": {ext: sha256_file(MAIN.with_suffix("." + ext)) for ext in ("pak", "ucas", "utoc")},
        "candidate_sha256": {ext: sha256_file(OUTPUT / (MAIN.with_suffix("." + ext).name)) for ext in ("pak", "ucas", "utoc")},
    }
    (OUTPUT / "merge_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (OUTPUT / "FullyPlayableCreateACharacterSystemExperience.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
