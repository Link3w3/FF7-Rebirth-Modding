"""align_moves.py for the packages under one folder of a packaged chunk: the cooker can put other packages in a move chunk
(Sephiroth's mesh landed in pakchunk48 with the summon's moves); only the moves go into the mod's container.
    align_only.py <in.utoc> <out folder> <out name> <in .pak stub> <content folder prefix, e.g. RebirthSkelCompat/Built/BizarroSummon/>
                  [<json list of content paths to leave out, e.g. RebirthSkelCompat/Built/SephirothForms/Battle05/B_Avoid01_0.uasset>]"""
import json, os, shutil, sys
sys.path.insert(0, '/work/sephforms/tools')
import align_moves as A
from align_moves import Toc, W, hdr, realign, verify, SHIFT


def main():
    in_utoc, out_dir, out_name, pak_stub, prefix = sys.argv[1:6]
    skip = set(json.load(open(sys.argv[6]))) if len(sys.argv) > 6 else set()
    src = Toc(in_utoc)
    header_chunk = [i for i in range(src.entries) if src.chunk_type(i) == 10]
    assert len(header_chunk) == 1
    _, store = hdr.parse_header(src.read(header_chunk[0]))
    mount = '../../../End/Content/'
    chunks, entries, left = [None], [], []
    blocks = 0
    for i in range(src.entries):
        if src.chunk_type(i) == 10:
            continue
        assert src.chunk_type(i) == 2, ('unexpected chunk type', src.chunk_type(i))
        path = src.files[i]
        assert path.startswith(mount), path
        if not path[len(mount):].startswith(prefix) or path[len(mount):] in skip:
            left.append(path[len(mount):])
            continue
        pid = src.chunk_id64(i)
        new = realign(src.read(i))
        blocks += verify(new, path)
        se = store[pid]
        assert se['size'] >> 60 == 0, path
        chunks.append(dict(id64=pid, type=2, data=new, path=path[len(mount):]))
        entries.append(dict(id=pid, size=len(new) | (SHIFT << 60), export_count=se['export_count'],
                            export_bundle_count=se['export_bundle_count'], load_order=se['load_order'], imports=se['imports']))
    here = {e['id'] for e in entries}
    cid = W.container_id_from_name(out_name)
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, out_name)
    W.write_container(base, out_name, chunks, mount=mount)
    shutil.copy(pak_stub, base + '.pak')
    back = Toc(base + '.utoc')
    assert back.entries == len(chunks)
    _, ents = hdr.parse_header(back.read(0))
    for i in range(1, back.entries):
        c = chunks[i]
        data = back.read(i)
        assert data == c['data'] and back.chunk_id64(i) == c['id64'] and back.files.get(i) == mount + c['path']
        assert ents[c['id64']]['size'] == len(data) | (SHIFT << 60)
        verify(data, c['path'])
    print('%d packages under %s laid out like the game\'s (shift %d); %d ACL blocks 16-aligned; container %s (%016x); left out: %s'
          % (len(chunks) - 1, prefix, SHIFT, blocks, out_name, cid, ', '.join(left) or 'nothing'))


if __name__ == '__main__':
    main()
