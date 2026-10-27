"""Vincent's gun shop: gun parts sold at the weapon vendors, and the bullet rows they switch to.

zzVincentGunShop_P (a container of its own, named to load after the other mods in ~mods):
  * Item: 12 key items, a part of each kind for each gun (Cerberus, Hydra, Griffon): Power Core (damage), Hair Trigger
    (fire rate), Extended Magazine (rounds and reload) and Long Barrel (range). Up to 5 of each (the level), bought for gil,
    not sold back; Vincent's Quicksilver as the menu model. Their UniqueIds sit in a gap among the game's key items.
  * ShopItem / ShopList: one shop entry for each part (unlimited stock: no counters, so the save's counter array is not
    touched; "sold out" once you hold 5), at the end of each of the 8 weapon vendors' lists. Built on the VR Simulator
    Overhaul's two tables as installed (it changes the Moogle and Gold Saucer shops; both changes stay).
  * Text/US/Resident_TxtRes: the parts' names and descriptions.
FullyPlayableVincentAssets_P (the installed one, its other packages as they are): the game's damage table with each gun's
bullet at every power level (0-5, +20% damage each) and range level (0-5, +20% reach each: a little faster, flying a little
longer). PC0011_Dirge_<Gun> is level 0 of both, PC0011_Dirge_<Gun>_P<p>R<r> the rest; the mod picks the row from the parts
you own (VincentDirge.json "upgrades", which this writes as upgrades.json).
    build_gunshop.py <out dir (new)>"""
import contextlib, hashlib, io, json, os, sys
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix',
                '/work/weap1012/tools', '/work/shooter1016/tools', '/work/prologue1016/tools',
                '/work/sephforms/tools', '/work/dirgegun1017/tools']
import build_atb as B
import build_dirge_paks as P
import iostore_write as W
import txtres
from iostore import Toc

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOP = 'zzVincentGunShop_P'
ASSETS = 'FullyPlayableVincentAssets_P'
BASE_ASSETS = '/work/dirgegun1017/out1'                   # installed (utoc 9e30808b...)
BASE_ASSETS_UTOC_MD5 = '9e30808b0db92ea6f94c8f4a188e13da'
GAME3 = '/work/seph1013/pakchunk3-WindowsNoEditor.utoc'     # the PC's (md5 4d6164d1...)
GAME1 = '/data/uploads/FINAL FANTASY VII REBIRTH/End/Content/Paks/pakchunk1-WindowsNoEditor.utoc'   # (md5 07f915d1...)
ITEM = 'DataObject/Resident/Item.uasset'
SHOP_ITEM = 'DataObject/Resident/ShopItem.uasset'
SHOP_LIST = 'DataObject/Resident/ShopList.uasset'
TEXT = 'Text/US/Resident_TxtRes.uasset'
DAMAGE = 'DataObject/Resident/BattleDamageSource.uasset'
SOURCES = {
    ITEM: (os.path.join(HERE, 'pkgs', 'DataObject__Resident__Item.uasset'), GAME3),
    TEXT: ('/work/text1013/pkgs/Text__US__Resident_TxtRes.uasset', GAME1),
    DAMAGE: ('/work/seph1013/tables/game_BattleDamageSource.uasset', GAME3),
}
# the VR Simulator Overhaul's shop tables (~mods\VRSimulatorOverhaul_P, 2026-10-16), each the game's with its changes
VR = {SHOP_ITEM: (os.path.join(HERE, 'vr', 'ShopItem.uasset'), 'd6a43acd0d044778729f5f7db2ea1f83'),
      SHOP_LIST: (os.path.join(HERE, 'vr', 'ShopList.uasset'), '3811bf684f7958c0aef303c3d1ac5522')}
VENDORS = ['KALMT_WEAPON_000', 'JNONV_WEAPON_000', 'JNONT_WEAPON_000', 'COSTT_WEAPON_000', 'CORLV_WEAPON_000', 'UNDRS_WEAPON_000',
           'GONGV_WEAPON_000', 'COSMA_WEAPON_000']
TEMPLATE_ITEM = 'key_ChocoboPass'      # a key item bought for gil at a shop
TEMPLATE_SHOP = 'ShopItem_it_potion'   # a shop entry without counters (unlimited stock)
TEMPLATE_SHOT = 'PC0001_NAtk_1_01'     # Barret's normal shot (build_gun_rows.py)
STRONG = 'PC0001_NAtk_1_03'
FIRST_ID = 3860                         # 3842-3899 is unused among the game's key item ids
FIRST_SORT = 2200
LEVELS = 5
POWER_STEP = 0.2                        # damage per Power Core
REACH_STEP = 0.2                        # reach per Long Barrel ...
SPEED_STEP = 0.1                        # ... of it by flying faster (the rest by flying longer)
RATE = [0.92, 0.84, 0.76, 0.68, 0.6]    # time between shots, by Hair Triggers owned
RELOAD = [0.92, 0.84, 0.76, 0.68, 0.6]  # reload time, by Extended Magazines owned
MODEL = dict(CharaSpecID='WE0011_00_Vincent_Quiksilver', MenuItemModelScale=1.0, MenuItemModelInitOffsetX=0.0,
             MenuItemModelInitOffsetY=0.0, MenuItemModelInitOffsetZ=0.0, MenuItemModelInitPitch=0.0, MenuItemModelInitYaw=90.0,
             MenuItemModelInitRoll=0.0, MenuItemModelCameraDistance=0.0)
GUNS = {
    # key: name, its bullet row, power, ATB bonus on a hit, reaction from, speed cm/s, reach cm, rounds per Extended Magazine,
    #      prices of its parts (gil each)
    'cerberus': dict(name='Cerberus', row='PC0011_Dirge_Cerberus', power=12, bonus=40, reaction=TEMPLATE_SHOT, speed=12000.0,
                     reach=3000.0, rounds=1, prices=dict(power=1500, trigger=1200, magazine=1000, barrel=800)),
    'hydra': dict(name='Hydra', row='PC0011_Dirge_Hydra', power=5, bonus=15, reaction=TEMPLATE_SHOT, speed=12000.0,
                  reach=2000.0, rounds=6, prices=dict(power=1500, trigger=1200, magazine=1000, barrel=800)),
    'griffon': dict(name='Griffon', row='PC0011_Dirge_Griffon', power=45, bonus=120, reaction=STRONG, speed=16000.0,
                    reach=4500.0, rounds=1, prices=dict(power=2000, trigger=1200, magazine=1000, barrel=800)),
}
PARTS = [
    # key, name, billboard, what it does (with the gun's name and rounds)
    ('power', 'Power Core', 'U_Com_Billboard_key_qst07_CartParts_Good',
     'A reinforced firing core for {gun}. Each one you own raises its damage by 20%. Up to 5.'),
    ('trigger', 'Hair Trigger', 'U_Com_Billboard_key_qst07_CartParts_Good',
     'A lighter trigger for {gun}. Each one you own shortens the time between shots by 8%. Up to 5.'),
    ('magazine', 'Extended Magazine', 'U_Com_Billboard_key_qst07_CartParts_Normal',
     'A larger magazine for {gun}. Each one you own adds {rounds} and speeds up reloading by 8%. Up to 5.'),
    ('barrel', 'Long Barrel', 'U_Com_Billboard_key_GONGM_WireGun',
     'A longer barrel for {gun}. Each one you own extends its range by 20%. Up to 5.'),
]


def quiet(f, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*a)


def game_bytes(path):
    """A package of the game's, checked against its container's hash."""
    f, utoc = SOURCES[path]
    data = open(f, 'rb').read()
    t = Toc(utoc)
    i = [k for k, p in t.files.items() if p.endswith('/' + path)]
    assert len(i) == 1, path
    assert t.b[t.metas_off + 33 * i[0]:t.metas_off + 33 * i[0] + 20] == hashlib.sha1(data).digest(), 'not the game\'s ' + path
    return data


def vr_bytes(path):
    f, md5 = VR[path]
    data = open(f, 'rb').read()
    assert hashlib.md5(data).hexdigest() == md5, 'not the VR Simulator Overhaul\'s ' + path
    return data


def part_key(gun, part):
    return 'key_dirge_%s_%s' % (gun, part)


def parts():
    """(item key, gun key, part key, name, billboard, help text, price, unique id, sort value) of every part."""
    out = []
    n = 0
    for gun, g in GUNS.items():
        for part, name, board, help_text in PARTS:
            rounds = '%d round%s' % (g['rounds'], '' if g['rounds'] == 1 else 's')
            out.append((part_key(gun, part), gun, part, '%s %s' % (g['name'], name), board, help_text.format(gun=g['name'], rounds=rounds),
                        g['prices'][part], FIRST_ID + n, FIRST_SORT + n))
            n += 1
    return out


def make_items(it):
    names = [f[0][0] for f in it.fields]
    base = list(it.row(TEMPLATE_ITEM))
    taken = {it.get(it.row(k), 'UniqueId') for k in it.at}
    made = []
    for key, gun, part, name, board, help_text, price, uid, sort in parts():
        assert key not in it.at and uid not in taken, key
        row = list(base)
        values = dict(ChapterID_Array=['Chapt_None'], GettableChapterID_Array=[], LargeAcquireInArea_Array=[],
                      ItemDetailLabel='$%s_help' % key, ShopShortName=None, AbilityID=None, IconName=board, TextureName=board,
                      IncreaseLabel='$level_sys_cinema_keyitem_get', DecreaseLabel='$level_sys_cinema_keyitem_lost',
                      RewardTextID='$level_sys_cinema_keyitem_get', RewardNotGetTextID='$level_sys_cinema_keyitem_lost',
                      CategoryStringArgument00=None, CategoryStringArgument01=None, CategoryStringArgument02=None,
                      CategoryStringArgument03=None, ItemNameLabel='$' + key, TreasureSpecId=None, JukeBoxID=None, ChangeFlag=None, SortValue=sort, BuyValue=price,
                      SaleValue=0, MaxCount=LEVELS, EffectiveValue=0, UniqueId=uid, CanSale=0, InvisibleFlag=0, ItemCategory=2,
                      Category=2, CategoryDetail=4, OverrideIconValue=0, ItemRarity=0, SceneLayerType=0, CanStack=1, **MODEL)
        assert set(values) == set(names), sorted(set(names) ^ set(values))
        for f, v in values.items():
            it.set(row, f, v)
        it.add(key, row)
        made.append(key)
    return made


def make_shop(si, sl):
    names = [f[0][0] for f in si.fields]
    base = list(si.row(TEMPLATE_SHOP))
    entries = []
    for key, gun, part, name, board, help_text, price, uid, sort in parts():
        shop_key = 'ShopItem_' + key
        assert shop_key not in si.at
        row = list(base)
        values = dict(ShopBuyStateTrigger_Array=[], CountersID_Array=[], OverridePrice_Array=[], UseItemID=None, ItemId=key, ViewFlag=None,
                      LocationId=None, ItemType=0, SoldOutByStockEmpty=0, SoldOutAsHasCountMax=1)
        assert set(values) == set(names), sorted(set(names) ^ set(values))
        for f, v in values.items():
            si.set(row, f, v)
        si.add(shop_key, row)
        entries.append(shop_key)
    for vendor in VENDORS:
        row = sl.row(vendor)
        listed = sl.get(row, 'ItemID_Array')
        assert not any(e in listed for e in entries), vendor
        sl.set(row, 'ItemID_Array', listed + entries)
    return entries


def bullet_rows(ds):
    """Every gun's bullet at every power and range level (in place); returns {gun: {(p, r): row key}} and a report."""
    names = [f[0][0] for f in ds.fields]
    base = list(ds.row(TEMPLATE_SHOT))
    t = {n: ds.get(base, n) for n in names}
    assert t['Flag0'] == 0 and t['EnemyHitCategoryTypeBit'] == 31 and t['ControlType'] == 3 and t['CreateBasePos'] == 1, t
    hit = ds.row('EB2020_00_AtkShot01_Bullet')
    assert ds.get(hit, 'HitEffectResourceName_Array') == ['FX_R_Common_HitGun_01'] and ds.get(hit, 'HitEffectResourceCategory_Array') == [30]
    keys, report = {}, []
    for gun, g in GUNS.items():
        keys[gun] = {}
        for p in range(LEVELS + 1):
            for r in range(LEVELS + 1):
                key = g['row'] if p == r == 0 else '%s_P%dR%d' % (g['row'], p, r)
                assert key not in ds.at, key
                row = list(base)
                # (as build_gun_rows.py: Vincent's muzzle, no cartridge or Barret's effects and sounds, the common gun hit)
                ds.set(row, 'CreatePartName', 'VFX_Muzzle01')
                for f in ('CreatePhysicsObjectCharaSpecID', 'CreatePhysicsObjectPartName', 'CreateEffectResourceName', 'CreateSoundResourceName',
                          'HitSoundResourceName', 'BindSoundResourceName'):
                    ds.set(row, f, None)
                for f in ('CreatePhysicsObjectForce', 'CreatePhysicsObjectForceRandom'):
                    ds.set(row, f, 0.0)
                for f in ('CreatePhysicsObjectBasePos', 'CreateEffectResourceCategory', 'CreateSoundResourceCategory', 'HitSoundResourceCategory',
                          'BindSoundResourceCategory'):
                    ds.set(row, f, 0)
                ds.set(row, 'HitEffectResourceName_Array', ['FX_R_Common_HitGun_01'])
                ds.set(row, 'HitEffectResourceCategory_Array', [30])
                ds.set(row, 'CollisionParameter_Array', [25.0])
                speed = g['speed'] * (1.0 + SPEED_STEP * r)
                reach = g['reach'] * (1.0 + REACH_STEP * r)
                control = ds.get(row, 'ControlParameter_Array')
                control[0] = speed
                ds.set(row, 'ControlParameter_Array', control)
                ds.set(row, 'LifeTime', reach / speed)
                ds.set(row, 'Power', int(round(g['power'] * (1.0 + POWER_STEP * p))))
                ds.set(row, 'HitBonusParameter', g['bonus'])
                if g['reaction'] != TEMPLATE_SHOT:
                    src = ds.row(g['reaction'])
                    for f in ('HitReactionType_Array', 'HitReactionParam_Array', 'AerialHitReactionParam_Array', 'BPAttack', 'BPAttackDamageCoefficient',
                              'HitForceFeedbackFileName'):
                        ds.set(row, f, ds.get(src, f))
                ds.add(key, row)
                keys[gun][(p, r)] = key
        v0 = {n: ds.get(ds.row(keys[gun][(0, 0)]), n) for n in names}
        v5 = {n: ds.get(ds.row(keys[gun][(LEVELS, LEVELS)]), n) for n in names}
        report.append('%s: %d rows; level 0: power %d, %.0f cm/s for %.3f s (%.0f m); level 5: power %d, %.0f cm/s for %.3f s (%.0f m)' % (
            g['row'], len(keys[gun]), v0['Power'], v0['ControlParameter_Array'][0], v0['LifeTime'],
            v0['ControlParameter_Array'][0] * v0['LifeTime'] / 100.0, v5['Power'], v5['ControlParameter_Array'][0], v5['LifeTime'],
            v5['ControlParameter_Array'][0] * v5['LifeTime'] / 100.0))
    return keys, report


def upgrades_config():
    """VincentDirge.json's guns' "upgrades" (and "range": the bullet's reach at level 0, which the aim assist keeps to)."""
    out = {}
    for gun, g in GUNS.items():
        ids = {part: uid for key, gk, part, name, board, help_text, price, uid, sort in parts() if gk == gun}
        out[g['name'].upper()] = dict(range=g['reach'], upgrades=[
            dict(item=part_key(gun, 'power'), id=ids['power'], row='P', levels=LEVELS),
            dict(item=part_key(gun, 'barrel'), id=ids['barrel'], row='R', range=[round(1.0 + REACH_STEP * k, 4) for k in range(1, LEVELS + 1)]),
            dict(item=part_key(gun, 'trigger'), id=ids['trigger'], interval=RATE),
            dict(item=part_key(gun, 'magazine'), id=ids['magazine'], clip=[g['rounds'] * k for k in range(1, LEVELS + 1)], reload=RELOAD),
        ])
    return out


def check_table(old, new, added_rows, changed_rows=()):
    """The new table: the old one's rows as they were (but the ones changed), then the added rows as made."""
    t2 = quiet(B.Table, new.encode() if isinstance(new, B.Table) else new)
    keys0 = list(old.at)
    assert list(t2.at)[:len(keys0)] == keys0 and len(t2.at) == len(keys0) + len(added_rows)
    for k in keys0:
        if k not in changed_rows:
            assert t2.row(k) == old.row(k), k
    return t2


def main(out):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    report = []
    # 1. the parts (Item), their shop entries (ShopItem, ShopList) and text
    item_data = game_bytes(ITEM)
    it = quiet(B.Table, item_data)
    made = make_items(it)
    item_new = quiet(it.encode)
    it2 = check_table(quiet(B.Table, item_data), item_new, made)
    for key in made:
        assert it2.row(key) == it.row(key), key
    si_data, sl_data = vr_bytes(SHOP_ITEM), vr_bytes(SHOP_LIST)
    si, sl = quiet(B.Table, si_data), quiet(B.Table, sl_data)
    entries = make_shop(si, sl)
    si_new, sl_new = quiet(si.encode), quiet(sl.encode)
    si2 = check_table(quiet(B.Table, si_data), si_new, entries)
    sl2 = check_table(quiet(B.Table, sl_data), sl_new, [], VENDORS)
    sl0 = quiet(B.Table, sl_data)
    for vendor in VENDORS:
        assert sl2.get(sl2.row(vendor), 'ItemID_Array') == sl0.get(sl0.row(vendor), 'ItemID_Array') + entries, vendor
    for k in entries:
        iid = si2.get(si2.row(k), 'ItemId')
        assert iid in it2.at and si2.get(si2.row(k), 'ItemType') == 0
    texts = []
    for key, gun, part, name, board, help_text, price, uid, sort in parts():
        texts += [('$' + key, name), ('$%s_help' % key, help_text)]
    text_data = game_bytes(TEXT)
    old_entries, lang = txtres.parse(text_data)
    have = {e[0] for e in old_entries}
    assert lang == 'US' and not any(k in have for k, _ in texts)
    text_new = txtres.add(text_data, texts)
    new_entries, lang2 = txtres.parse(text_new)
    got = {e[0]: e[1] for e in new_entries}
    assert lang2 == 'US' and len(new_entries) == len(old_entries) + len(texts) and all(got[k] == v for k, v in texts)
    assert [e[:2] for e in new_entries[:len(old_entries)]] == [e[:2] for e in old_entries]
    for key, gun, part, name, board, help_text, price, uid, sort in parts():
        report.append('%s (%s, id %d): %d gil, up to %d; %s' % (key, name, uid, price, LEVELS, help_text))
    report.append('shops: %s get %d entries each (unlimited stock, sold out at %d)' % (', '.join(VENDORS), len(entries), LEVELS))
    # 2. the bullet rows
    dmg_data = game_bytes(DAMAGE)
    ds = quiet(B.Table, dmg_data)
    keys, rep = bullet_rows(ds)
    report += rep
    dmg_new = quiet(ds.encode)
    added = [k for g in keys.values() for k in g.values()]
    ds2 = check_table(quiet(B.Table, dmg_data), dmg_new, added)
    for k in added:
        assert ds2.row(k) == ds.row(k), k
    # 3. zzVincentGunShop_P
    os.makedirs(out)
    chunks, hentries = [], []
    for path, data in ((ITEM, item_new), (SHOP_ITEM, si_new), (SHOP_LIST, sl_new), (TEXT, text_new)):
        pid = W.package_id('/Game/' + path[:-len('.uasset')])
        chunks.append(dict(id64=pid, type=2, data=data, path=path))
        hentries.append(B.store_entry(pid, data))
    stub = os.path.join(BASE_ASSETS, ASSETS + '.pak')
    cid, files = P.write(out, SHOP, chunks, hentries, stub)
    report.append('container %s: %s; %s' % (SHOP, ', '.join('%s %d bytes' % (c['path'], len(c['data'])) for c in chunks), files))
    # 4. FullyPlayableVincentAssets_P: the installed one with the new damage table
    assert hashlib.md5(open(os.path.join(BASE_ASSETS, ASSETS + '.utoc'), 'rb').read()).hexdigest() == BASE_ASSETS_UTOC_MD5
    achunks, store = P.read(os.path.join(BASE_ASSETS, ASSETS + '.utoc'))
    aentries = []
    replaced = 0
    for c in achunks:
        if c['type'] != 2:
            continue
        e = P.entry(c, store[c['id64']])
        if c['path'] == DAMAGE:
            c['data'] = dmg_new
            e['size'] = len(dmg_new)
            replaced += 1
        aentries.append(e)
    assert replaced == 1
    acid, afiles = P.write(out, ASSETS, achunks, aentries, stub)
    back = Toc(os.path.join(out, ASSETS + '.utoc'))
    old = Toc(os.path.join(BASE_ASSETS, ASSETS + '.utoc'))
    old_by = {(old.chunk_id64(k), old.chunk_type(k)): k for k in range(old.entries)}
    same = 0
    for k in range(back.entries):
        key = (back.chunk_id64(k), back.chunk_type(k))
        if key[1] == 10:
            continue
        assert key in old_by, key
        if back.files.get(k, '').endswith(DAMAGE):
            assert back.read(k) == dmg_new
        else:
            assert back.read(k) == old.read(old_by[key]), key
            same += 1
    report.append('container %s: %d packages (%d of the installed one as they were, the damage table with %d rows, %d bytes); %s' % (
        ASSETS, len(aentries), same, len(ds2.at), len(dmg_new), afiles))
    json.dump(upgrades_config(), open(os.path.join(out, 'upgrades.json'), 'w'), indent=1)
    open(os.path.join(out, 'gunshop_report.txt'), 'w').write('\n'.join(report) + '\n')
    print('\n'.join(report))


if __name__ == '__main__':
    main(sys.argv[1])
