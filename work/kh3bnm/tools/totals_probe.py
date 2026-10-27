"""Probe which formulas reproduce the stored Bonamik 2.4 totals (KH3 p_ex011 and Rebirth PC0010_10)."""
import json, sys, collections
sys.path.insert(0, '/work/cs'); sys.path.insert(0, '/work/bnm/tools')
NO_ID = 0xFFFFFFFF

def fixed(d, name, n):
    return [d.get(name if i == 0 else '%s[%d]' % (name, i), 0) for i in range(n)]

def norm_enum(s):
    return s.replace('_v2', '') if isinstance(s, str) else s

def probe(tag, v):
    B, Lk, P = v['m_Bodies'], v['m_Links'], v.get('m_Planes', [])
    sc = v['m_SceneManager']
    for l in Lk: l['m_LinkType'] = norm_enum(l['m_LinkType'])
    for b in B: b['m_AddiConstType'] = norm_enum(b['m_AddiConstType']); b['m_ColShape'] = norm_enum(b['m_ColShape'])
    by = {b['m_Index']: b for b in B}
    selfl = [l for l in Lk if l['m_IsSelfCollision']]
    nons = [l for l in Lk if not l['m_IsSelfCollision']]
    stored = {k: v.get(k, 0) for k in ['m_TotalKinematics','m_TotalConstraints','m_TotalCones','m_TotalLinks','m_TotalCollisions','m_TotalSelfCollisions','m_TotalChainRootParticles','m_TotalPCLinkCones','m_TotalLateralLinkCones']}
    print('==', tag, 'bodies', len(B), 'links', len(Lk), 'planes', len(P), 'self', len(selfl))
    print('stored', stored)
    roots = set()
    for l in Lk:
        a, c = by[l['m_ParentId']], by[l['m_ChildId']]
        if a['m_IsKinematic'] and not c['m_IsKinematic']: roots.add(a['m_Index'])
        if c['m_IsKinematic'] and not a['m_IsKinematic']: roots.add(c['m_Index'])
    lat = sum(1 for l in Lk if l['m_LinkType'] in ('ESQEX_Bonamik_LinkType_Lateral', 'ESQEX_Bonamik_LinkType_Bending'))
    calc = dict(m_TotalKinematics=sum(b['m_IsKinematic'] for b in B),
                m_TotalConstraints=sum(b['m_AddiConstType'] != 'ESQEX_Bonamik_ConstraintType_None' for b in B),
                m_TotalCones=sum(l['m_EnableCone'] for l in Lk),
                m_TotalLinks=len(nons), m_TotalSelfCollisions=len(selfl),
                m_TotalChainRootParticles=len(roots), m_TotalLateralLinkCones=lat - len(selfl))
    print('calc  ', calc)
    # collision candidates
    cands = {
        'links receiver': [l for l in Lk if l['m_IsCollisionReceiver']],
        'links receiver nonself': [l for l in nons if l['m_IsCollisionReceiver']],
        'links repulsor': [l for l in Lk if l['m_IsCollisionRepulsor']],
        'bodies collision kin': [b for b in B if b['m_IsCollision']],
        'bodies colid any': [b for b in B if any(c != -1 for c in fixed(b, 'm_ColId', 8))],
        'bodies dyn colid any': [b for b in B if not b['m_IsKinematic'] and any(c != -1 for c in fixed(b, 'm_ColId', 8))],
        'planes collision': [p for p in P if p['m_IsCollision']],
    }
    for k, items in cands.items():
        print('  %-26s %d' % (k, len(items)))
    rec = [l for l in Lk if l['m_IsCollisionReceiver']]
    dyn = [b for b in B if not b['m_IsKinematic'] and any(c != -1 for c in fixed(b, 'm_ColId', 8))]
    print('  receiver+dyn colid', len(rec) + len(dyn), 'receiver+planes', len(rec) + sum(p['m_IsCollision'] for p in P))
    # batch counts
    def counts(nums):
        c = [0] * 15
        for n in nums:
            if n != NO_ID and n < 15: c[n] += 1
        return c
    print('scene links ', fixed(sc, 'm_TotalLinksInBatch', 15), sc.get('m_TotalLinkBatches'))
    print('calc links  ', counts([l['m_LinkBatchNo'] for l in nons]))
    print('scene cones ', fixed(sc, 'm_TotalConesInBatch', 15), sc.get('m_TotalConeBatches'))
    print('calc cones  ', counts([l['m_ConeBatchNo'] for l in Lk if l['m_EnableCone']]))
    print('scene coll  ', fixed(sc, 'm_TotalCollisionsInBatch', 15), sc.get('m_TotalCollisionBatches'))
    print('calc coll rec   ', counts([l['m_CollisionBatchNo'] for l in rec]))
    print('calc coll rec nonself', counts([l['m_CollisionBatchNo'] for l in nons if l['m_IsCollisionReceiver']]))
    print('calc coll dynbody', counts([b['m_CollisionBatchNo'] for b in dyn]))
    print('scene self  ', fixed(sc, 'm_TotalSelfCollisionsInBatch', 15), sc.get('m_TotalSelfCollisionBatches'))
    print('calc self lbn ', counts([l['m_LinkBatchNo'] for l in selfl]))
    print('calc self cbn ', counts([l['m_CollisionBatchNo'] for l in selfl]))
    print('calc self conebn ', counts([l['m_ConeBatchNo'] for l in selfl]))
    return calc, stored

kh3 = json.load(open('/work/kh3bnm/test/p_ex011_raw.json'))
probe('KH3 p_ex011', kh3)
from load import load
L, objs = load('PC0010_10_Sephiroth_Transform/Model/PC0010_10_BNM')
probe('Rebirth PC0010_10', objs[1])
