"""The rebuild's HLSL (the RM_Surface Custom node code, UE flavour) -> C++ for the checker.

    hlsl2cpp.py <in.ush> <out.cpp>

The HLSL is written in a subset both compilers take: no swizzle writes, no implicit scalar->vector promotion, no casts.
This only rewrites what C++ can't say: swizzle reads (.xyz -> .xyz(), .rgb -> .xyz(), .r -> .x), out/inout parameters
(-> references), and [branch]-style attributes."""
import re, sys

SWZ = re.compile(r'(?<=[\w\)\]])\.([xyzw]{2,4}|[rgba]{1,4})\b(?!\s*\()')
RGBA = str.maketrans('rgba', 'xyzw')


def translate(src):
    # comments out (keep line structure)
    src = re.sub(r'//[^\n]*', '', src)
    src = re.sub(r'/\*.*?\*/', lambda m: '\n' * m.group(0).count('\n'), src, flags=re.S)
    bad = re.search(r'\.([xyzw]{2,4}|[rgba]{2,4})\s*([-+*/]?=)(?!=)', src)
    if bad:
        line = src[:bad.start()].count('\n') + 1
        raise SystemExit('line %d: swizzle write ".%s %s" (not in the shared subset)' % (line, bad.group(1), bad.group(2)))
    src = re.sub(r'\[(branch|flatten|unroll|loop)(\(\d+\))?\]', '', src)

    def swz(m):
        s = m.group(1).translate(RGBA)
        return '.' + s + ('()' if len(s) > 1 else '')
    src = SWZ.sub(swz, src)
    src = re.sub(r'\binout\s+(\w+)\s+(\w+)', r'\1& \2', src)
    src = re.sub(r'\bout\s+(\w+)\s+(\w+)', r'\1& \2', src)
    src = re.sub(r'\bin\s+(\w+)\s+(\w+)(?=\s*[,)])', r'\1 \2', src)
    src = re.sub(r'\bstatic\s+const\b', 'const', src)
    src = re.sub(r'\b(float|half|MaterialFloat)\b', 'D', src)
    return src


MARK = '// ==== body ===='


if __name__ == '__main__':
    # <in.ush> <out dir>: the library (before the marker) -> RMS_Lib.cpp, the node body -> RMS_Surface.cpp
    import os
    src = open(sys.argv[1]).read()
    lib, body = src.split(MARK, 1)
    open(os.path.join(sys.argv[2], 'RMS_Lib.cpp'), 'w').write(translate(lib))
    open(os.path.join(sys.argv[2], 'RMS_Surface.cpp'), 'w').write('#line %d "RMS_Surface.ush"\n' % (lib.count('\n') + 1) + translate(body))
