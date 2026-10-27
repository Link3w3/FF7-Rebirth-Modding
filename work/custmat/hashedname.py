import sys
sys.path.insert(0, '/work/fx1018/editor/Python')
from rebirth_fx.cityhash import CityHash64, h16, M
K2 = 0x9ae16a3b2f90404f
def city_seed(b, seed):
    return h16((CityHash64(b) - K2) & M, seed)
def hashed_name(name):
    """UE 4.26 FHashedName: CityHash64WithSeed(upper-case name, FName number)."""
    base, num = name, 0
    head, _, tail = name.rpartition('_')
    # (type names carry no number suffix in practice)
    return city_seed(name.upper().encode('utf-8'), 0)
