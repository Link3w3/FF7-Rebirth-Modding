# Sora's versions of Cloud's area actions and event animations (cloudaction): what every step shares.
import unreal, json, os
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
BASE = os.path.join(SAVED, 'ModExtract', 'cloudaction')
KEYS = os.path.join(BASE, 'keys')
JOBS = json.load(open(os.path.join(KEYS, 'jobs.json')))
SKEL = '/Game/Character/Player/PC0000_00_Sora_KH2/Model/PC0000_00_S_Skeleton.PC0000_00_S_Skeleton'
LIB = unreal.EndSkeletonCompatDataObject
SORA, CLOUD = 'PC0000_00_Sora_KH2', 'PC0000_Cloud'


def sora_of(cloud):
    """Cloud's object path (or package path) -> Sora's"""
    parts = cloud.split('/')
    return '/'.join(SORA if x == CLOUD else x for x in parts)


def obj(path):
    return path if '.' in path.rsplit('/', 1)[-1] else path + '.' + path.rsplit('/', 1)[-1]


def pairs(k):
    folder, dest, n, clouds = JOBS[k]
    return [(obj(c), obj(sora_of(c))) for c in clouds]
