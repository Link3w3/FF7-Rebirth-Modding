import os, sys, json, time
sys.path[:0] = ['/work/custmat', '/work/custmat/gamesh', '/work/fx1018/editor/Python']
import carrier_build as cb
import material
from try_compile import BUNDLES
def run(export, carrier, ignore_mask=False, depth='auto'):
    cs = cb.CarrierShaders(carrier, BUNDLES[carrier])
    ex = material.Exported(os.path.join('/work/custmat/export/RebirthMatExport/KH3', export))
    t = time.time()
    try:
        built, plan = cb.build_blobs(ex, cs, '/tmp/scratch/gamesh_work/soradepth_%s_%s' % (export, carrier), ignore_mask=ignore_mask, depth=depth)
    except Exception as e:
        import traceback
        return {'error': traceback.format_exc()[-3000:]}
    return {'variants': {res: dict(kind=r['kind'], types=r['types'][:2], problems=r['problems'][:3], size=len(r['blob']) if r['blob'] else 0) for res, r in built.items()},
            'plan': {k: dict(cs.named)[j] for k, j in plan.items()}, 'secs': round(time.time() - t, 1)}
if __name__ == '__main__':
    print(json.dumps(run(sys.argv[1], sys.argv[2], len(sys.argv) > 3 and sys.argv[3] == 'ignore'), indent=1)[:6000])
