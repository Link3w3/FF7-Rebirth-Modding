"""The wing's KineDriver: the part of the transformed Sephiroth's PC0010_10_KDI that drives his wing (every operator
that writes a wing bone and everything upstream of it through the connections: kdi_wing_closure.py's), as a KDI of its
own, in the same order, its bodies, connections and work slots renumbered. It reads and writes only wing bones
(R_Feather*), in their parents' spaces.
SCALE (the wing's size against Sephiroth's) goes into the lengths it holds: the neutral translations and the
constraint offsets, and the curves of the effectors that turn a bend into a translation (their outputs) or a
translation into a scale (their inputs). Angles and scales stay.
    make_wing_kdi.py <PC0010_10_KDI.json> <out spec.json> [SCALE]"""
import json, sys, collections
BODY = {
    'SOURCE_ROTATE': 'SourceRotateBody', 'SOURCE_TRANSLATE': 'SourceTranslateBody', 'TARGET_TRANSLATE': 'TargetTranslateBody',
    'TARGET_SCALE': 'TargetScaleBody', 'TARGET_ROTATE': 'TargetRotateBody', 'TARGET_BEND_ROLL': 'TargetBendRollBody',
    'TARGET_BEND_ST_ROLL': 'TargetBendSTRollBody', 'TARGET_POSCNS': 'TargetPoscnsBody', 'TARGET_ORICNS': 'TargetOricnsBody',
    'EFFECTOR_EZ_PARAM_LINK': 'EffectorEZParamLinkBody', 'EFFECTOR_EZ_PARAM_LINK_LINEAR': 'EffectorEZParamLinkLinearBody',
    'CONNECTION': 'ConnectionBody'}
LENGTH_PORTS = {'TRANSLATE_X', 'TRANSLATE_Y', 'TRANSLATE_Z'}
ALL_LISTS = ['ComputeSpaceBasesBody', 'SourceBody', 'SourceTranslateBody', 'SourceRotateBody', 'SourceOtherBody', 'TargetTranslateBody',
             'TargetScaleBody', 'TargetRotateBody', 'TargetBendRollBody', 'TargetBendSTRollBody', 'TargetExpmapBody', 'TargetPoscnsBody',
             'TargetOricnsBody', 'TargetDircnsBody', 'TargetOtherBody', 'EffectorInverseBody', 'EffectorLinkWithBody',
             'EffectorEZParamLinkBody', 'EffectorEZParamLinkLinearBody', 'EffectorRBFInterpBody', 'EffectorExprBody', 'ConnectionBody']


def kind(op):
    return op['OpType'].replace('ESQEX_KD_OPERATOR_TYPE_', '')


def port(p):
    return p['ParameterType'].replace('ESQEX_KD_PARAMETER_TYPE_', '')


def main(src, out, scale=1.0):
    d = json.load(open(src))
    ops = d['Operators']

    def body(i):
        return d[BODY[kind(ops[i])]][ops[i]['OperatorBody']]
    into = collections.defaultdict(list)
    for i, o in enumerate(ops):
        if kind(o) == 'CONNECTION':
            into[body(i)['OutPortInfo']['OperatorIndex']].append(i)
    targets = [i for i, o in enumerate(ops) if kind(o).startswith('TARGET') and 'Feather' in body(i).get('TargetObjectBoneName', '')]
    keep, stack = set(), list(targets)
    while stack:
        i = stack.pop()
        if i in keep:
            continue
        keep.add(i)
        if kind(ops[i]) == 'CONNECTION':
            stack.append(body(i)['InPortInfo']['OperatorIndex'])
        stack.extend(into.get(i, []))
    keep = sorted(keep)
    new_index = {old: k for k, old in enumerate(keep)}
    # what each effector reads and feeds (for the lengths)
    eff_in, eff_out = {}, collections.defaultdict(set)
    for i in keep:
        if kind(ops[i]) == 'CONNECTION':
            c = body(i)
            a, b = c['InPortInfo'], c['OutPortInfo']
            if kind(ops[b['OperatorIndex']]).startswith('EFFECTOR'):
                eff_in[b['OperatorIndex']] = port(a)
            if kind(ops[a['OperatorIndex']]).startswith('EFFECTOR'):
                eff_out[a['OperatorIndex']].add(port(b))
    spec = {k: [] for k in ALL_LISTS}
    spec.update(WorkNum=0, PreComputeObjects=[], PreComputeObjectBoneNameArray=[], ComputedObjectBoneNameArray=[], Operators=[])
    work = {}
    scaled = collections.Counter()
    for i in keep:
        o = ops[i]
        k = kind(o)
        b = json.loads(json.dumps(body(i)))
        if k == 'CONNECTION':
            b['InPortInfo']['OperatorIndex'] = new_index[b['InPortInfo']['OperatorIndex']]
            b['OutPortInfo']['OperatorIndex'] = new_index[b['OutPortInfo']['OperatorIndex']]
        if scale != 1.0:
            if k in ('SOURCE_TRANSLATE', 'TARGET_TRANSLATE'):
                b['NeutralTranslate'] = [x * scale for x in b['NeutralTranslate']]
                scaled['neutral translations'] += 1
            if k == 'TARGET_TRANSLATE':
                for ax in ('TranslateX', 'TranslateY', 'TranslateZ'):
                    b[ax] *= scale
            if k == 'TARGET_POSCNS':
                b['OffsetTranslate'] = [x * scale for x in b['OffsetTranslate']]
                b['OffsetArray'] = [[x * scale for x in v] for v in b['OffsetArray']]
                scaled['position constraints'] += 1
            if k.startswith('EFFECTOR'):
                out_len = bool(eff_out[i] & LENGTH_PORTS)
                in_len = eff_in.get(i) in LENGTH_PORTS
                assert not (eff_out[i] & LENGTH_PORTS and eff_out[i] - LENGTH_PORTS), ('mixed outputs', i, eff_out[i])
                if k == 'EFFECTOR_EZ_PARAM_LINK':
                    assert not b['ByCoef'] or not (in_len or out_len), ('a coefficient curve on a length', i)
                    if out_len:
                        for f in ('PY0', 'PY0A', 'PY0B', 'PY1', 'PY1A', 'PY1B', 'PY2', 'Grad0', 'Grad1'):
                            b[f] *= scale
                        scaled['curves to a translation'] += 1
                    if in_len:
                        for f in ('PX0', 'VX1_0', 'VX2_1'):
                            b[f] *= scale
                        for f in ('Grad0', 'Grad1'):
                            b[f] /= scale
                        scaled['curves from a translation'] += 1
                elif k == 'EFFECTOR_EZ_PARAM_LINK_LINEAR':
                    if out_len and not in_len:
                        b['Scale'] *= scale; b['Offset'] *= scale; b['ClampMin'] *= scale; b['ClampMax'] *= scale
                        scaled['lines to a translation'] += 1
                    elif in_len and not out_len:
                        b['Scale'] /= scale
                        scaled['lines from a translation'] += 1
                    elif in_len and out_len:
                        b['Offset'] *= scale; b['ClampMin'] *= scale; b['ClampMax'] *= scale
        lst = BODY[k]
        spec[lst].append(b)
        wi = o['WorkIndex']
        if wi >= 0:
            assert wi not in work, 'two operators share a work slot'
            work[wi] = len(work)
        spec['Operators'].append(dict(WorkIndex=work[wi] if wi >= 0 else -1, OpType=o['OpType'], OperatorBody=len(spec[lst]) - 1, Label=o['Label']))
    spec['WorkNum'] = len(work)
    bones_read = sorted({n for i in keep for n in (body(i).get('SourceBoneNameArray') or [])})
    bones_written = sorted({body(i)['TargetObjectBoneName'] for i in keep if 'TargetObjectBoneName' in body(i)})
    assert all('Feather' in n for n in bones_read + bones_written)
    spec['_about'] = dict(source=src.rsplit('/', 1)[-1], scale=scale, operators=len(keep), kinds=dict(collections.Counter(kind(ops[i]) for i in keep)),
                          reads=bones_read, writes=bones_written, scaled=dict(scaled))
    json.dump(spec, open(out, 'w'), indent=0)
    print('%s: %d operators (%s), %d work slots; reads %d bones, writes %d; scale %.3f: %s' % (
        out.rsplit('/', 1)[-1], len(keep), dict(collections.Counter(kind(ops[i]) for i in keep)), len(work), len(bones_read),
        len(bones_written), scale, dict(scaled)))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], *(float(x) for x in sys.argv[3:4]))
