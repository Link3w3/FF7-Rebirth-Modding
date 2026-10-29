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

ZACK_STANDARD = "PC0009_00_Zack_Standard_ZACK"
ZACK_AERITH_RIBBON = "PC0009_01_Zack_AerithRibbon_ZACK"
ZACK_DIRTY = "PC0009_02_Zack_Dirty_ZACK"
ZACK_WET = "PC0009_03_Zack_StandardWet_ZACK"
ZACK_NO_BATTLE = "PC0009_00_Zack_NoBattle_ZACK"
ZACK_RESERVE = "PC0009_00_Zack_Reserve_ZACK"
BUSTER = "WE0000_00_Cloud_BusterSword"
ZACK_BUSTER = "WE0000_00_Cloud_BusterSword_ZACK"


def zack_row(cloud_row: str) -> str:
    if cloud_row.endswith("_NoBattle"):
        return ZACK_NO_BATTLE
    if cloud_row.endswith("_Reserve"):
        return ZACK_RESERVE
    if "Dirty" in cloud_row:
        return ZACK_DIRTY
    if "Wet" in cloud_row:
        return ZACK_WET
    if "ZackCostume" in cloud_row and "Age21" not in cloud_row:
        return ZACK_AERITH_RIBBON
    return ZACK_STANDARD


def main() -> dict:
    document = json.loads(BASE_CONFIG.read_text(encoding="utf-8-sig"))
    sora = next(c for c in document["characters"] if c["name"] == "SORA")
    mappings = {}
    for source in sora["charaspecs"]:
        if source.startswith("PC0000_"):
            mappings[source] = zack_row(source)
        elif source.startswith("WE0000_") and source != BUSTER:
            mappings[source] = ZACK_BUSTER

    # The base Buster Sword also resolves to Zack's dedicated copy. This keeps
    # every Cloud weapon choice on one Zack-owned weapon row.
    mappings[BUSTER] = ZACK_BUSTER

    if not mappings or any(source == target for source, target in mappings.items()):
        raise RuntimeError("Zack's CharaSpec mapping did not pass preflight")

    character = {
        "name": "ZACK",
        "slot": "Cloud",
        "player": "pt_Cloud",
        "note": "Zack Fair: uses Zack's editor CharaSpec rows and pt_Zack combat data in Cloud's place. Every Cloud weapon choice resolves to Zack's Buster Sword CharaSpec row.",
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
        "comment": "Zack Fair in Cloud's place. The Zack costume and Buster Sword CharaSpec rows are in the extracted editor table and must be included in the cooked CACS data pak.",
        "characters": [character],
    }
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "output": str(OUTPUT),
        "character": character["name"],
        "slot": character["slot"],
        "charspec_mappings": len(mappings),
        "cloud_weapon_rows_to_buster": sum(1 for k, v in mappings.items() if k.startswith("WE0000_") and v == ZACK_BUSTER),
        "native_zack_rows": sorted(set(v for k, v in mappings.items() if k.startswith("PC0000_"))),
        "player_row_swap": character["rows"][0],
        "requires_paks": character["requires_paks"],
    }


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
