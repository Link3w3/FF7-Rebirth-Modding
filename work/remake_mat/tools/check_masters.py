"""Every check of the rebuilt masters (pixel: base pass and coverage; vertex: base pass and depth-only), one master after
another, each master's results in checks/<master>.txt and a summary line per master.
    check_masters.py [-n cases] <master>..."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), 'checks')


def main():
    args = sys.argv[1:]
    n = '200'
    if '-n' in args:
        i = args.index('-n'); n = args[i + 1]; del args[i:i + 2]
    os.makedirs(OUT, exist_ok=True)
    for master in args:
        lines = []
        for tool in ('remake_check.py', 'remake_check_vs.py'):
            p = subprocess.run([sys.executable, os.path.join(HERE, tool), master, '-n', n], capture_output=True, text=True)
            lines.extend(p.stdout.splitlines())
            if p.returncode:
                lines.append('%s FAILED: %s' % (tool, p.stderr.strip().splitlines()[-1] if p.stderr.strip() else p.returncode))
        open(os.path.join(OUT, master + '.txt'), 'w').write('\n'.join(lines) + '\n')
        checks = [l for l in lines if 'cases' in l or 'ERROR' in l or 'FAILED' in l]

        def ok(l):
            if 'worst' not in l:
                return False
            if 'discard_mismatch' in l and 'discard_mismatch 0 ' not in l:
                return False
            return float(l.rsplit('worst', 1)[1].split()[0]) <= 1e-4
        bad = [l for l in checks if not ok(l)]
        print('%-34s %3d checks, %d not matching' % (master, len(checks), len(bad)), flush=True)


if __name__ == '__main__':
    main()
