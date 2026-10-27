"""A Cloud skin (skins\\<name>\\skin.json, Create a Character System 3.15.1+) with "weapon_field_socket": "Attach_Weapon01"
after its "weapon": outside battle the Buster Sword sits on his back (that socket of his model), in battle it goes back to
his hand (the game's AttachWeapon). Written as the skins are (one-space indent, UTF-8, a newline at the end).
    patch_cloud_skin_json.py <in skin.json> <out skin.json>"""
import json
import sys

SOCKET = 'Attach_Weapon01'

if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    raw = open(src, 'rb').read()
    doc = json.loads(raw.decode('utf-8'))
    assert (json.dumps(doc, indent=1, ensure_ascii=False) + '\n').encode('utf-8') == raw, 'not written the way this script writes'
    assert 'weapon_field_socket' not in doc, 'has a weapon_field_socket already'
    assert 'BusterSword' in doc.get('weapon', ''), 'not a skin with the Buster Sword'
    out = {}
    for key, value in doc.items():
        out[key] = value
        if key == 'weapon':
            out['weapon_field_socket'] = SOCKET
    with open(dst, 'wb') as f:
        f.write((json.dumps(out, indent=1, ensure_ascii=False) + '\n').encode('utf-8'))
    print('%s: "weapon_field_socket": "%s"' % (doc.get('name'), SOCKET))
