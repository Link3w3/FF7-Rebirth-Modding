import json, sys
d = json.load(open(sys.argv[1]))
BODY = {'SOURCE_ROTATE': 'SourceRotateBody', 'SOURCE_TRANSLATE': 'SourceTranslateBody', 'TARGET_TRANSLATE': 'TargetTranslateBody',
        'TARGET_SCALE': 'TargetScaleBody', 'TARGET_ROTATE': 'TargetRotateBody', 'TARGET_BEND_ROLL': 'TargetBendRollBody',
        'TARGET_BEND_ST_ROLL': 'TargetBendSTRollBody', 'TARGET_POSCNS': 'TargetPoscnsBody', 'TARGET_ORICNS': 'TargetOricnsBody',
        'EFFECTOR_EZ_PARAM_LINK': 'EffectorEZParamLinkBody', 'EFFECTOR_EZ_PARAM_LINK_LINEAR': 'EffectorEZParamLinkLinearBody', 'CONNECTION': 'ConnectionBody'}
ops = d['Operators']
def kind(i): return ops[i]['OpType'].replace('ESQEX_KD_OPERATOR_TYPE_', '')
def body(i): return d[BODY[kind(i)]][ops[i]['OperatorBody']]
into = {}
for i in range(len(ops)):
    if kind(i) == 'CONNECTION':
        c = body(i)
        into.setdefault(c['OutPortInfo']['OperatorIndex'], []).append(c)
def name(i):
    b = body(i)
    return b.get('TargetObjectBoneName') or ','.join(b.get('SourceBoneNameArray') or []) or ''
def show(i, depth=0, port=''):
    k = kind(i); b = body(i)
    pad = '  ' * depth
    extra = ''
    if k.startswith('EFFECTOR'):
        extra = ' ' + json.dumps({x: (round(v, 5) if isinstance(v, float) else v) for x, v in b.items()})
    print('%s%s[%d] %s %s%s' % (pad, port, i, k, name(i), extra))
    if depth > 6: return
    for c in into.get(i, []):
        src = c['InPortInfo']['OperatorIndex']
        show(src, depth + 1, '%s<-%s(coef %.3g) ' % (c['OutPortInfo']['ParameterType'].replace('ESQEX_KD_PARAMETER_TYPE_', ''), c['InPortInfo']['ParameterType'].replace('ESQEX_KD_PARAMETER_TYPE_', ''), c['Coef']))
want = sys.argv[2:]
for i in range(len(ops)):
    if kind(i).startswith('TARGET') and name(i) in want:
        show(i)
        print()
