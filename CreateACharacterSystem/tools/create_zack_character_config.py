"""Build the CACS CHARACTER-page entry for native Zack Fair.

Zack uses the game's own CharaSpec rows and pt_Zack data. Cloud's alternative
greatsword rows resolve to Cloud's existing Buster Sword row for this first
playable pass. The CACS runtime already supports this config; no DLL patch is
needed.
"""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPAT = ROOT / "GameMods" / "ue4ss" / "Mods" / "RebirthSkelCompat" / "compat"
BASE_CONFIG = COMPAT / "FullyPlayableCreateACharacterSystemExperience.json"
OUTPUT = COMPAT / "PlayableZack.json"

ZACK_STANDARD = "PC0009_00_Zack_Standard"
ZACK_DIRTY = "PC0009_02_Zack_Dirty"
ZACK_WET = "PC0009_03_Zack_StandardWet"
ZACK_NO_BATTLE = "PC0009_00_Zack_NoBattle"
ZACK_RESERVE = "PC0009_00_Zack_Reserve"
BUSTER = "WE0000_00_Cloud_BusterSword"


def zack_row(cloud_row: str) -> str:
    if cloud_row.endswith("_NoBattle"):
        return ZACK_NO_BATTLE
    if cloud_row.endswith("_Reserve"):
        return ZACK_RESERVE
    if "Dirty" in cloud_row:
        return ZACK_DIRTY
    if "Wet" in cloud_row:
        return ZACK_WET
    return ZACK_STANDARD


def main() -> dict:
    document = json.loads(BASE_CONFIG.read_text(encoding="utf-8-sig"))
    sora = next(c for c in document["characters"] if c["name"] == "SORA")
    mappings = {}
    for source in sora["charaspecs"]:
        if source.startswith("PC0000_"):
            mappings[source] = zack_row(source)
        elif source.startswith("WE0000_") and source != BUSTER:
            mappings[source] = BUSTER

    # The base Buster Sword row already is the desired weapon and is therefore
    # deliberately left mapped to itself (the CACS parser rejects identity maps).
    if not mappings or any(source == target for source, target in mappings.items()):
        raise RuntimeError("Zack's CharaSpec mapping did not pass preflight")

    character = {
        "name": "ZACK",
        "slot": "Cloud",
        "player": "pt_Cloud",
        "note": "Zack Fair: uses the game's native Zack CharaSpecs and pt_Zack combat data in Cloud's place. All of Cloud's available greatsword choices use the Buster Sword for this first playable pass.",
        "requires_paks": ["FullyPlayableCreateACharacterSystemExperience_P"],
        "charaspecs": mappings,
        "names_in_add": sora["names_in_add"],
        "rows": [
            {"table": "BattlePlayerParameter", "row": "pt_Cloud", "from": "pt_Zack"}
        ],
        "title": {
            "weapon": "/Game/Character/Weapon/WE0000_00_Cloud_BusterSword/Model/WE0000_00",
            "tint": [0.18, 0.38, 0.9],
        },
    }
    result = {
        "schema": "RebirthSkelCompat/1",
        "comment": "Zack Fair in Cloud's place, using Zack's native game data and the Buster Sword. This separate entry appears on CACS's CHARACTER customization page when the CACS mod pak is installed.",
        "characters": [character],
    }
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "output": str(OUTPUT),
        "character": character["name"],
        "slot": character["slot"],
        "charspec_mappings": len(mappings),
        "cloud_weapon_rows_to_buster": sum(1 for k, v in mappings.items() if k.startswith("WE0000_") and v == BUSTER),
        "native_zack_rows": sorted(set(v for k, v in mappings.items() if k.startswith("PC0000_"))),
        "player_row_swap": character["rows"][0],
        "requires_paks": character["requires_paks"],
    }


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
