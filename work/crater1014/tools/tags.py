"""UE4.26 tagged properties of a zen package's exports.  tags.py <pkg>"""
import struct, sys
sys.path.insert(0, '/work/aura1014/tools')
import zx

def run(path):
    z = zx.load(path)
    names = z.names
    def fname(b, o):
        i, n = struct.unpack_from('<ii', b, o)
        s = names[i] if 0 <= i < len(names) else '?%d' % i
        return (s if n == 0 else '%s_%d' % (s, n - 1)), o + 8
    def tags(b, o, depth=0, limit=None):
        out = []
        end = limit if limit is not None else len(b)
        while o < end:
            name, o = fname(b, o)
            if name == 'None':
                break
            typ, o = fname(b, o)
            size, idx = struct.unpack_from('<ii', b, o); o += 8
            extra = ''
            if typ == 'StructProperty':
                sn, o = fname(b, o); o += 16; extra = sn
            elif typ == 'BoolProperty':
                extra = str(b[o]); o += 1
            elif typ in ('ByteProperty', 'EnumProperty'):
                en, o = fname(b, o); extra = en
            elif typ in ('ArrayProperty', 'SetProperty'):
                it, o = fname(b, o); extra = it
            elif typ == 'MapProperty':
                k, o = fname(b, o); v, o = fname(b, o); extra = k + ',' + v
            hasg = b[o]; o += 1
            if hasg: o += 16
            val = b[o:o + size]
            show = ''
            if typ == 'FloatProperty': show = '%g' % struct.unpack_from('<f', val)[0]
            elif typ == 'IntProperty': show = str(struct.unpack_from('<i', val)[0])
            elif typ in ('ObjectProperty', 'SoftObjectProperty') and size == 4:
                v = struct.unpack_from('<i', val)[0]; show = 'obj %d' % v
            elif typ in ('ByteProperty', 'EnumProperty', 'NameProperty') and size == 8:
                show = fname(val, 0)[0]
            elif typ == 'StructProperty' and extra in ('Vector', 'BoxSphereBounds', 'Box', 'Rotator', 'LinearColor', 'Vector4', 'Vector2D'):
                show = ' '.join('%g' % x for x in struct.unpack_from('<%df' % (size // 4), val))
            print('  ' * depth + '%s [%s %s] size %d idx %d %s' % (name, typ, extra, size, idx, show))
            if typ == 'StructProperty' and extra not in ('Vector', 'BoxSphereBounds', 'Box', 'Rotator', 'LinearColor', 'Vector4', 'Vector2D', 'Guid', 'Color'):
                try: tags(val, 0, depth + 1)
                except Exception as e: print('  ' * (depth + 1) + '(%s)' % e)
            if typ == 'ArrayProperty' and extra == 'StructProperty':
                n = struct.unpack_from('<i', val)[0]
                # inner tag then elements
                p = 4
                iname, p = fname(val, p); ityp, p = fname(val, p); isz, iidx = struct.unpack_from('<ii', val, p); p += 8
                sn, p = fname(val, p); p += 16; hg = val[p]; p += 1
                if hg: p += 16
                print('  ' * (depth + 1) + '%d x %s' % (n, sn))
                for k in range(n):
                    print('  ' * (depth + 1) + '[%d]' % k)
                    try: p = tags(val, p, depth + 2)
                    except Exception as e: print('(%s)' % e); break
            o += size
        return o + 0
    for i in z.order:
        e = z.exports[i]
        print('== export %d %s (%d bytes)' % (i, e['name'], e['serial_size']))
        b = z.exp(i)
        try: tags(b, 0)
        except Exception as ex: print('  (stop: %s)' % ex)
    print('imports', len(z.imports))

if __name__ == '__main__':
    run(sys.argv[1])
