"""The Converter / build_mod flow of rebirth_fx.gamemat.convert, with game data and editor stand-ins from local files."""
import gzip, os, shutil, struct, sys, time
sys.path.insert(0, '/work/fxlink/src/Content/Python')
from rebirth_fx.gamemat import env
env.set_dxc('/home/user/microsoft/dxc-build/bin/dxc', dict(os.environ, LD_LIBRARY_PATH='/home/user/microsoft/dxc-build/lib'))
env.set_engine_shaders('/work/custmat/gamesh/engine/Shaders')
WORK = '/tmp/scratch/gamemat_conv'
if os.path.isdir(WORK): shutil.rmtree(WORK)
env.set_work(WORK)
from rebirth_fx.gamemat import shaderlib, convert
from rebirth_fx.hdr import parse_header
sys.path.insert(0, '/work/sorasurf')
from try_compile import BUNDLES
C = '/work/custmat'

def raw_bundle(path):
    raw = open(path, 'rb').read(); p = 0; out = []
    while p < len(raw):
        index, size, usize, freq = struct.unpack_from('<IIIB', raw, p); p += 13
        hsh = raw[p:p + 20]; p += 20
        out.append(dict(index=index, hash=hsh, code=raw[p:p + size], usize=usize, freq=freq)); p += size
    return out

class FakeGame(object):
    def __init__(self):
        self.paks_dir = WORK + '/paks'
        os.makedirs(self.paks_dir + '/~mods', exist_ok=True)
        self.names = set()
        for line in gzip.open('/work/gamelist/gamefiles.txt.gz', 'rt'):
            p = line.rstrip('\n').split('\t')[-1]
            if p.startswith('../../../End/Content/') and p.endswith('.uasset'):
                self.names.add('/Game/' + p[len('../../../End/Content/'):-7])
        self.entries = {}
        for n in (0, 3, 4):
            self.entries.update(parse_header(open(C + '/pakchunk%d_container_header.bin' % n, 'rb').read())[1])
        hdr = open('/data/uploads/FF7R2UProj/Saved/ModExtract/shlib/End_header.bin', 'rb').read()
        self.lib = shaderlib.Library(hdr, prefixed=True)
        self.code = {}
        for b in BUNDLES.values():
            for s in raw_bundle(b):
                self.code[s['index']] = s
        self.lib.shader = lambda si: self.code[si]
    def package(self, name):
        name = name.split('.')[0]
        if name.startswith('/Game/Renderer/MaterialInstance/Surface/'):
            return open('/work/anime/pkgs/Renderer__MaterialInstance__Surface__%s.uasset' % name.rsplit('/', 1)[1], 'rb').read()
        return open(C + '/seph/pkgs/' + name[len('/Game/'):].replace('/', '__') + '.uasset', 'rb').read()
    def exists(self, name):
        return name.split('.')[0] in self.names
    def entries_for(self, name):
        return self.entries
    def library(self):
        return self.lib

class FakeEditor(object):
    EXPORTS = {'/Game/KH3/Character/pc/p_ex011/mdl/mat0/p_ex011_mat01inst': 'KH3/p_ex011_mat01inst',
               '/Game/KH3/Character/pc/p_ex011/mdl/mat0/p_ex011_hair_Inst': 'KH3/p_ex011_hair_Inst'}
    def export(self, path, folder):
        src = C + '/export/RebirthMatExport/' + self.EXPORTS[path.split('.')[0]]
        for f in ('material.json', 'material.hlsl'):
            shutil.copy(os.path.join(src, f), os.path.join(folder, f))
        return ''
    def asset_exists(self, path):
        return True
    def cook(self, packages, content):
        n = 0
        for p in packages:
            short = p.rsplit('/', 1)[1]
            dst = os.path.join(content, p[len('/Game/'):])
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            for ext in ('.uasset', '.ubulk'):
                s = '/work/sorasurf/tex/' + short + ext
                if os.path.isfile(s):
                    shutil.copy(s, dst + ext)
            n += 1
        return '%d of %d package(s) cooked' % (n, len(packages))

game, editor = FakeGame(), FakeEditor()
conv = convert.Converter(game, editor)
store = convert.Store()
for path in FakeEditor.EXPORTS:
    t = time.time()
    made, info = conv.convert(path + '.' + path.rsplit('/', 1)[1])
    store.put(path, made, info)
    print(path.rsplit('/', 1)[1], '%.1fs' % (time.time() - t), info['kind'], info['carrier_copy'], 'cook', info['cook'], 'game tex', info['game_textures'])
paths, entries, notes = convert.build_mod(store, game, editor.cook)
for p in paths: print(p, os.path.getsize(p))
for e in entries: print('  %-75s exports %d load %d imports %d' % (e['name'], e['export_count'], e['load_order'], len(e['imports'])))
print(convert.install(paths, game.paks_dir))
