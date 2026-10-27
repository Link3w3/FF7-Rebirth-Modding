import unreal
lib = getattr(unreal, 'RebirthFxLinkLibrary', None) or getattr(unreal, 'RebirthFxLibrary')
result = {}
names = lib.find_game_packages_matching('/Game/Effect', 200000)
result['count'] = len(names)
import collections, re
tops = collections.Counter('/'.join(n.split('/')[:4]) for n in names)
result['tops'] = tops.most_common(40)
pref = collections.Counter(re.sub(r'[^A-Za-z].*$', '', n.rsplit('/', 1)[-1]) for n in names)
result['prefixes'] = pref.most_common(40)
result['ps_like'] = [n for n in names if re.search(r'/(PS|P|Ps)_[^/]*$', n)][:60]
result['sample'] = names[:40]
