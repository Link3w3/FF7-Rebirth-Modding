"""The part of PC0010_10_KDI that drives the wing: every operator that writes a wing bone (R_Feather*), and everything
upstream of it through the connections. Prints what it reads and writes.
    kdi_wing_closure.py <PC0010_10_KDI.json>"""
import json, sys, collections
d = json.load(open(sys.argv[1]))
ops = d['Operators']
C = d['ConnectionBody']
BODY = {
    'ESQEX_KD_OPERATOR_TYPE_SOURCE_ROTATE': 'SourceRotateBody', 'ESQEX_KD_OPERATOR_TYPE_SOURCE_TRANSLATE': 'SourceTranslateBody',
    'ESQEX_KD_OPERATOR_TYPE_TARGET_TRANSLATE': 'TargetTranslateBody', 'ESQEX_KD_OPERATOR_TYPE_TARGET_SCALE': 'TargetScaleBody',
    'ESQEX_KD_OPERATOR_TYPE_TARGET_ROTATE': 'TargetRotateBody', 'ESQEX_KD_OPERATOR_TYPE_TARGET_BEND_ROLL': 'TargetBendRollBody',
    'ESQEX_KD_OPERATOR_TYPE_TARGET_BEND_ST_ROLL': 'TargetBendSTRollBody', 'ESQEX_KD_OPERATOR_TYPE_TARGET_POSCNS': 'TargetPoscnsBody',
    'ESQEX_KD_OPERATOR_TYPE_TARGET_ORICNS': 'TargetOricnsBody', 'ESQEX_KD_OPERATOR_TYPE_EFFECTOR_EZ_PARAM_LINK': 'EffectorEZParamLinkBody',
    'ESQEX_KD_OPERATOR_TYPE_EFFECTOR_EZ_PARAM_LINK_LINEAR': 'EffectorEZParamLinkLinearBody', 'ESQEX_KD_OPERATOR_TYPE_CONNECTION': 'ConnectionBody'}
def body(i):
    o = ops[i]
    return d[BODY[o['OpType']]][o['OperatorBody']]
into = collections.defaultdict(list)    # op index -> connection op indices feeding it
for i, o in enumerate(ops):
    if o['OpType'].endswith('CONNECTION'):
        c = body(i)
        into[c['OutPortInfo']['OperatorIndex']].append(i)
wing_targets = [i for i, o in enumerate(ops) if 'TARGET' in o['OpType'] and 'Feather' in body(i).get('TargetObjectBoneName', '')]
keep = set()
stack = list(wing_targets)
while stack:
    i = stack.pop()
    if i in keep:
        continue
    keep.add(i)
    o = ops[i]
    if o['OpType'].endswith('CONNECTION'):
        stack.append(body(i)['InPortInfo']['OperatorIndex'])
    for ci in into.get(i, []):
        stack.append(ci)
    # bone-name sources of constraints (read bones directly)
keep = sorted(keep)
print('wing target ops', len(wing_targets), 'closure', len(keep), collections.Counter(ops[i]['OpType'].replace('ESQEX_KD_OPERATOR_TYPE_', '') for i in keep))
reads, writes, spaces = set(), set(), set()
for i in keep:
    b = body(i)
    for n in b.get('SourceBoneNameArray', []) or []:
        reads.add(n)
    if 'TargetObjectBoneName' in b:
        writes.add(b['TargetObjectBoneName'])
    bs = b.get('BaseSpaceInfo')
    if bs:
        spaces.add(json.dumps(bs, sort_keys=True))
print('reads', sorted(reads))
print('writes', len(writes), sorted(writes))
print('base spaces', sorted(spaces)[:20])
non_wing = [n for n in reads | writes if 'Feather' not in n]
print('non-wing bones touched:', non_wing)
json.dump(dict(keep=keep, wing_targets=wing_targets), open('/work/fpys/wing/kdi_wing_closure.json', 'w'))
