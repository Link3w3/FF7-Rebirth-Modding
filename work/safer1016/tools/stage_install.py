"""Lays out files for the PC in 25 MB parts (the copy back to the PC takes 30 MB a file, 100 MB a call): each file as
<name>.partNN under <out>/<label>/, with a manifest of parts, sizes and md5s, and the shell lines that join them on the PC.
    stage_install.py <out dir (new)> <label>=<file> [<label>=<file> ...]"""
import hashlib, json, os, sys

PART = 25 * 1024 * 1024


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main(out, items):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    os.makedirs(out)
    manifest = []
    for item in items:
        label, path = item.split('=', 1)
        name = os.path.basename(path)
        folder = os.path.join(out, label)
        os.makedirs(folder, exist_ok=True)
        size = os.path.getsize(path)
        parts = []
        with open(path, 'rb') as f:
            index = 0
            while True:
                data = f.read(PART)
                if not data and index > 0:
                    break
                part = os.path.join(folder, '%s.part%02d' % (name, index))
                open(part, 'wb').write(data)
                parts.append({'path': part, 'size': len(data), 'md5': hashlib.md5(data).hexdigest()})
                index += 1
                if len(data) < PART:
                    break
        manifest.append({'label': label, 'name': name, 'size': size, 'md5': md5(path), 'parts': parts})
    json.dump(manifest, open(os.path.join(out, 'manifest.json'), 'w'), indent=1)
    for m in manifest:
        print('%s/%s: %d bytes, md5 %s, %d part(s)' % (m['label'], m['name'], m['size'], m['md5'], len(m['parts'])))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
