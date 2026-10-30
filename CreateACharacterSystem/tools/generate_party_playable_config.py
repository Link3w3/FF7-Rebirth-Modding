"""Regenerate full-cast CACS menu entries from the reviewed party plan."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PLAN=ROOT/'CreateACharacterSystem'/'build'/'party_playable_plan_20261030.json'
CONFIG=ROOT/'GameMods'/'ue4ss'/'Mods'/'RebirthSkelCompat'/'compat'/'FullyPlayableCreateACharacterSystemExperience.json'
plan=json.loads(PLAN.read_text(encoding='utf-8'))
data=json.loads(CONFIG.read_text(encoding='utf-8'))
new_names={p['config']['name'] for p in plan['party']}
data['characters']=[c for c in data.get('characters',[]) if c.get('name') not in new_names]
data['characters'].extend(p['config'] for p in plan['party'])
if len({c.get('name') for c in data['characters']})!=len(data['characters']):
 raise SystemExit('Duplicate character menu name; config was not written.')
for p in plan['party']:
 c=next(x for x in data['characters'] if x['name']==p['config']['name'])
 expected=26 if p['token']=='CID' else 34
 if c.get('slot')!='Cloud' or c.get('player')!='pt_Cloud' or len(c.get('charaspecs',{}))!=expected:
  raise SystemExit('Invalid playtable mapping for '+c['name']+'; config was not written.')
CONFIG.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({'ok':True,'entries':len(data['characters']),'added':sorted(new_names)},ensure_ascii=False))
