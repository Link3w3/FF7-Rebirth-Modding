import os, sys, json, time
sys.path[:0] = ['/work/custmat', '/work/custmat/gamesh', '/work/fx1018/editor/Python']
import carrier_build as cb
import material
SEPH = '/work/custmat/seph/'
ANIME = '/data/uploads/FF7R2UProj/Saved/ModExtract/shlib/anime/'
BUNDLES = {
    'RMI_Surface_Standard_Wide_Detail': SEPH + 'RMI_Surface_Standard_Wide_Detail.bundle',
    'RMI_Surface_Fabric_Coverage_Wide_Detail': SEPH + 'RMI_Surface_Fabric_Coverage_Wide_Detail.bundle',
    'RMI_Surface_Standard_Emissive_Wide': SEPH + 'RMI_Surface_Standard_Emissive_Wide.bundle',
    'RMI_Surface_Eye_Migration': SEPH + 'RMI_Surface_Eye_Migration.bundle',
    'RMI_Surface_Standard_Wide': ANIME + 'RMI_Surface_Standard_Wide.bundle',
    'RMI_Surface_Standard_Coverage_Wide': ANIME + 'RMI_Surface_Standard_Coverage_Wide.bundle',
    'RMI_Surface_Hair_Wide': ANIME + 'RMI_Surface_Hair_Wide.bundle',
    'RMI_Surface_Skin_Wide_Detail': ANIME + 'RMI_Surface_Skin_Wide_Detail.bundle',
    'RMI_Surface_Fabric_Wide': ANIME + 'RMI_Surface_Fabric_Wide.bundle',
}
def run(export, carrier, ignore_mask=False):
    cs = cb.CarrierShaders(carrier, BUNDLES[carrier])
    ex = material.Exported(os.path.join('/work/custmat/export/RebirthMatExport/KH3', export))
    t = time.time()
    try:
        built, plan = cb.build_blobs(ex, cs, '/tmp/scratch/gamesh_work/sora_%s_%s' % (export, carrier), ignore_mask=ignore_mask)
    except Exception as e:
        return {'error': str(e)[:400]}
    return {'variants': {res: dict(types=r['types'], problems=r['problems'][:3], size=len(r['blob']) if r['blob'] else 0) for res, r in built.items()},
            'plan': {k: dict(cs.named)[j] for k, j in plan.items()}, 'secs': round(time.time() - t, 1)}
if __name__ == '__main__':
    print(json.dumps(run(sys.argv[1], sys.argv[2], len(sys.argv) > 3), indent=1)[:3000])
