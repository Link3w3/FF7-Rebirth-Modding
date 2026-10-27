"""Cloud's area actions (Motion/Action/<area>/PC0000_Cloud) and event animations (Motion/Player/PC0000_Cloud/Event00) onto
Sora's skeleton as key animations (.cacanim), with soraanim1018's retarget (the skeleton as it was before Flatten Root:
the editor's Flatten Root pass then puts each import under the flat root, as it did every earlier import of his).
Jobs of at most 30 files per destination folder (import/<job>/<name>.cacanim), listed in jobs.json as
[job folder, destination, count, [cloud paths]]. Each clip is written as soon as it is made (890 clips of Sora's 400-odd
bones do not fit in memory at once); the jobs run in PROCS processes (default 2).
    retarget_actions.py <pkgs dir> <out dir>"""
import json, os, sys, glob, multiprocessing
sys.path[:0] = ['/work/soraanim1018/tools']
import retarget as R

SORA = 'PC0000_00_Sora_KH2'


def dest_of(cloud_path):
    parts = cloud_path.split('/')
    assert parts.count('PC0000_Cloud') == 1, cloud_path
    return '/'.join(SORA if x == 'PC0000_Cloud' else x for x in parts[:-1]), parts[-1]


def run_job(arg):
    job, dest, items, out = arg
    d = os.path.join(out, 'import', job)
    os.makedirs(d, exist_ok=True)
    done, report = [], {}
    for name, cloud, f in items:
        try:
            fps, S, LQc, LTc = R.decode(open(f, 'rb').read())
        except Exception as e:
            report[cloud] = 'ERROR %s' % e
            continue
        LQ, LT, LS, GT = R.retarget(LQc, LTc)
        loop = name.endswith('Lp') or 'Loop' in name or name.endswith('_1')
        R.write_cacanim(os.path.join(d, name + '.cacanim'), fps, LQ, LT, LS, loop)
        fl = min(GT[:, R.SORA.index['L_ashi1'], 2].min(), GT[:, R.SORA.index['R_ashi1'], 2].min())
        report[cloud] = dict(fps=fps, frames=S, sora_ankle_min_z=round(float(fl), 2), job=job)
        done.append(cloud)
        del LQ, LT, LS, GT, LQc, LTc
    return job, dest, done, report


def main(pkgs, out):
    groups = {}
    for f in sorted(glob.glob(os.path.join(pkgs, '*.uasset'))):
        cloud = '/Game/' + os.path.basename(f)[:-7].replace('__', '/')
        dest, name = dest_of(cloud)
        groups.setdefault(dest, []).append((name, cloud, f))
    work = []
    for dest, items in sorted(groups.items()):
        parts = dest.split('/')
        tag = parts[3] + '_' + (parts[4] if parts[3] == 'Action' else parts[-1])
        for k in range(0, len(items), 30):
            work.append(('%s_%02d' % (tag, k // 30), dest, items[k:k + 30], out))
    with multiprocessing.Pool(int(os.environ.get('PROCS', '2'))) as pool:
        results = pool.map(run_job, work, chunksize=1)
    jobs, report = [], {}
    for job, dest, done, rep in results:
        jobs.append(['import\\' + job, dest, len(done), done])
        report.update(rep)
    json.dump(jobs, open(os.path.join(out, 'jobs.json'), 'w'), indent=0)
    json.dump(report, open(os.path.join(out, 'report.json'), 'w'), indent=1)
    errs = {k: v for k, v in report.items() if isinstance(v, str)}
    print(len(report), 'clips,', len(errs), 'errors,', len(jobs), 'jobs')
    for k, v in list(errs.items())[:10]:
        print(' ', k, v)


if __name__ == '__main__':
    main(*sys.argv[1:3])
