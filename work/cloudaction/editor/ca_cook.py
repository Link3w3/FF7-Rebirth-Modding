# step 4: cook Sora's new animations of jobs K for the game (Cook For Game: compressed anew with the game's ACL settings)
pk = []
for k in K:
    pk += [s.rsplit('.', 1)[0] for c, s in pairs(k)]
r = LIB.cook_packages_for_game(pk, os.path.join(BASE, 'cook', 'End', 'Content'))
result = json.dumps(dict(packages=len(pk), report=r.strip().splitlines()[-3:] if r.strip() else []), indent=1)
