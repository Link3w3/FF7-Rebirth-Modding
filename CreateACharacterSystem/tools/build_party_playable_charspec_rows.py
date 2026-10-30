"""Add BARRET/TIFA/AERITH/REDXIII/YUFFIE/CAITSITH/CID variants by cloning Cloud rows."""
import json, os, traceback
import unreal
ROOT=unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
PLAN=os.path.join(ROOT,'Saved','RebirthSkelCompat','PartyPlayableBuild','party_playable_plan.json')
REPORT=os.path.join(ROOT,'Saved','RebirthSkelCompat','PartyPlayableBuild','party_playable_build.json')
TABLE='/Game/DataObject/Resident/CharaSpec'
try:
 plan=json.load(open(PLAN,encoding='utf-8'))
 lib=unreal.RebirthDataObjectLibrary
 names={str(n) for n in lib.get_data_object_row_names(TABLE)}
 all_targets=[]; all_sources=set(); rows=[]
 for person in plan['party']:
  token=person['token']; targets={};
  for src,meta in person['costumes'].items():
   all_sources.add(src); targets[meta['target']]=(src,meta['model'])
  for weapon in person.get('weapons',[]):
   all_sources.add(weapon['source']); targets[weapon['target']]=(weapon['source'],weapon['model'])
  rows.append({'token':token,'targets':targets,'person':person})
  all_targets.extend(targets)
 missing=sorted(all_sources-names)
 conflicts=sorted(set(all_targets)&names)
 duplicates=sorted({x for x in all_targets if all_targets.count(x)>1})
 if missing or conflicts or duplicates:
  result={'ok':False,'phase':'preflight','missing_sources':missing,'existing_target_conflicts':conflicts,'duplicate_targets':duplicates,'existing_count':len(names)}
 else:
  made=[]; failures=[]
  for group in rows:
   token=group['token']; person=group['person']; created=[]
   for target,(source,model) in group['targets'].items():
    msg=lib.duplicate_data_object_row(TABLE,source,target)
    if not msg:
     failures.append({'token':token,'source':source,'target':target,'error':'duplicate failed'}); break
    created.append(target)
    if model and not lib.set_data_object_row_field(TABLE,target,'ContentsModel',model):
     failures.append({'token':token,'target':target,'error':'ContentsModel failed'}); break
   if failures: break
   # Base row links: self-reserve (no new reserve row) and matching no-battle variant.
   for src,meta in person['costumes'].items():
    if src.endswith('_NoBattle'): continue
    target=meta['target']
    if target+'_NoBattle' in group['targets']:
     for field,value in [('ReserveCharaSpec',target),('NoBattleCharaSpec',target+'_NoBattle')]:
      if not lib.set_data_object_row_field(TABLE,target,field,value):
       failures.append({'token':token,'target':target,'field':field,'error':'link failed'}); break
    if failures: break
   if failures: break
   made.extend(created)
  if failures:
   result={'ok':False,'phase':'mutation','failures':failures,'created_before_failure':made,'instruction':'Restore backed up CharaSpec table before retry.'}
  else:
   save=lib.save_data_object(TABLE)
   after={str(n) for n in lib.get_data_object_row_names(TABLE)}
   checks={}
   for group in rows:
    for target,(src,model) in group['targets'].items():
     if src.startswith('PC0000_') and not src.endswith('_NoBattle'):
      checks[target]=[str(x) for x in lib.check_chara_spec_rows(TABLE,[target])]
   result={'ok':len(after)==len(names)+len(all_targets),'table':TABLE,'created_row_count':len(made),'created_rows':made,'counts':{'before':len(names),'after':len(after),'targets_expected':len(all_targets)},'checks':checks,'save_message':str(save) if save else '', 'policy':'Cloned exact Cloud source rows; retained CharaID and other Cloud row data; replaced only ContentsModel, NoBattleCharaSpec and self ReserveCharaSpec. No reserve rows created.'}
except Exception:
 result={'ok':False,'phase':'exception','error':traceback.format_exc()}
os.makedirs(os.path.dirname(REPORT),exist_ok=True)
with open(REPORT,'w',encoding='utf-8') as f: json.dump(result,f,indent=2)
print(json.dumps(result,ensure_ascii=False))
