"""A small fake of the End editor's `unreal` module for testing rebirth_fx outside the editor."""
import os, shutil, struct
ROOT = os.path.dirname(os.path.abspath(__file__))
SAVED = os.path.join(ROOT, 'Saved')
GAME = {}      # package name -> bytes (the 'game')
HEADERS = {}
ASSETS = {}    # asset path -> object
LOG = []

def log(t): LOG.append(t); print('LOG', t)
def log_warning(t): LOG.append('W ' + t); print('WARN', t)

class Paths:
    @staticmethod
    def project_saved_dir(): return SAVED
    @staticmethod
    def convert_relative_path_to_full(p): return p

class AppMsgType: OK = 0
class EditorDialog:
    messages = []
    @staticmethod
    def show_message(title, text, kind): EditorDialog.messages.append((title, text)); print('DIALOG', title, '|', text.replace('\n', ' / ')[:400])

class LinearColor:
    def __init__(self, r=0, g=0, b=0, a=1): self.r, self.g, self.b, self.a = r, g, b, a

class Obj:
    def __init__(self, path): self.path = path
    def get_path_name(self): return self.path

class MaterialInstanceConstant(Obj):
    def __init__(self, path):
        super().__init__(path); self.parent = None; self.scalars = {}; self.vectors = {}; self.textures = {}

class Material(Obj):
    def __init__(self, path, scalars=(), vectors=(), textures=()):
        super().__init__(path); self.s, self.v, self.t = list(scalars), list(vectors), list(textures)

class MaterialInstanceConstantFactoryNew: pass

class _Tools:
    def create_asset(self, name, folder, cls, factory):
        p = folder + '/' + name + '.' + name
        a = cls(p); ASSETS[folder + '/' + name] = a; return a
class AssetToolsHelpers:
    @staticmethod
    def get_asset_tools(): return _Tools()

def load_asset(path):
    return ASSETS.get(path.split('.')[0])

class EditorAssetLibrary:
    @staticmethod
    def does_asset_exist(p): return p.split('.')[0] in ASSETS
    @staticmethod
    def save_asset(p, only_if_is_dirty=True): return True
    @staticmethod
    def sync_browser_to_objects(l): pass
    @staticmethod
    def does_directory_exist(p): return True

def _root_names(mi, kind):
    m = mi
    while isinstance(m, MaterialInstanceConstant): m = m.parent
    if m is None: return []
    return {'s': m.s, 'v': m.v, 't': m.t}[kind]

class MaterialEditingLibrary:
    @staticmethod
    def set_material_instance_parent(mic, p): mic.parent = p
    @staticmethod
    def set_material_instance_scalar_parameter_value(mic, n, v): mic.scalars[n] = v; return True
    @staticmethod
    def set_material_instance_vector_parameter_value(mic, n, v): mic.vectors[n] = v; return True
    @staticmethod
    def set_material_instance_texture_parameter_value(mic, n, t): mic.textures[n] = t; return True
    @staticmethod
    def get_material_instance_scalar_parameter_value(mic, n): return mic.scalars.get(n, 0.0)
    @staticmethod
    def get_material_instance_vector_parameter_value(mic, n):
        return mic.vectors.get(n, LinearColor(0, 0, 0, 0))
    @staticmethod
    def get_material_instance_texture_parameter_value(mic, n): return mic.textures.get(n)
    @staticmethod
    def update_material_instance(mic): pass
    @staticmethod
    def get_scalar_parameter_names(m): return _root_names(m, 's')
    @staticmethod
    def get_vector_parameter_names(m): return _root_names(m, 'v')
    @staticmethod
    def get_texture_parameter_names(m): return _root_names(m, 't')

class RebirthFxLibrary:
    paks = os.path.join(ROOT, 'Game', 'End', 'Content', 'Paks')
    @staticmethod
    def get_game_paks_directory(): return RebirthFxLibrary.paks
    @staticmethod
    def save_game_package_to_file(name, fn):
        if name not in GAME: return 'no package ' + name
        os.makedirs(os.path.dirname(fn), exist_ok=True); open(fn, 'wb').write(GAME[name]); return ''
    @staticmethod
    def save_game_container_header_to_file(name, fn):
        os.makedirs(os.path.dirname(fn), exist_ok=True); open(fn, 'wb').write(HEADERS[name]); return ('', 'pakchunk4-WindowsNoEditor')
    @staticmethod
    def find_game_packages_matching(f, n): return sorted(GAME)
    @staticmethod
    def pick_from_list(title, prompt, items, initial): return items[0] if items else ''

def register_slate_post_tick_callback(fn): return 1
class ToolMenus: pass
