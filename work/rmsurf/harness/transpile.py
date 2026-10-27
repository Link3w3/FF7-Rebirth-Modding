"""dxil-spirv's GLSL of a game shader -> a C++ namespace for the CPU checker (glsl_cpu.hpp).
    transpile.py <in.glsl> <namespace> <out.cpp> [<texture map json: {"Material_Texture2D_0": "Color", ...}>]"""
import json, re, sys


def transpile(src, ns, texnames=None):
    texnames = texnames or {}
    lines = src.split('\n')
    out = []
    decls = []      # declarations of the shader's globals
    inputs, outputs = [], []
    i = 0
    body = []
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if s.startswith('#version') or s.startswith('#extension') or s.startswith('spirv_instruction'):
            i += 1
            continue
        m = re.match(r'layout\(([^)]*)\) uniform (\w+)\s*$', s)
        if m and i + 1 < len(lines) and lines[i + 1].strip() == '{':
            lay = m.group(1)
            mb = re.search(r'set = (\d+), binding = (\d+)', lay)
            bufname = 'b%s_%s' % (mb.group(1), mb.group(2)) if mb else None
            # a uniform block: up to "} Name;"
            j = i + 2
            while not re.match(r'\}\s*(\w+);', lines[j].strip()):
                j += 1
            name = re.match(r'\}\s*(\w+);', lines[j].strip()).group(1)
            member = ' '.join(l.strip() for l in lines[i + 2:j])
            mt = re.match(r'(\w+) _m0\[', member)
            kind = mt.group(1) if mt else 'vec4'
            fn = {'vec4': 'ubo', 'float': 'uboF', 'uint': 'uboU', 'uvec4': 'uboUV', 'int': 'uboI'}.get(kind, 'ubo')
            typ = {'ubo': 'UBO', 'uboF': 'UBOF', 'uboU': 'UBOU', 'uboUV': 'UBOUV', 'uboI': 'UBOI'}[fn]
            # (named by its binding: two views of one buffer are the same bytes; View and Primitive keep their names)
            key = name if name in ('View', 'Primitive') else (bufname or name)
            decls.append('static %s& %s = %s("%s");' % (typ, name, fn, key))
            i = j + 1
            continue
        m = re.match(r'layout\(([^)]*)\) uniform (\w+) (\w+)\[\];', s)
        if m:
            typ, name = m.group(2), m.group(3)
            cxx = {'texture2D': 'Tex2D', 'texture3D': 'Tex3D', 'sampler': 'Samp'}[typ]
            decls.append('static %s %s[64];' % (cxx, name))
            i += 1
            continue
        m = re.match(r'layout\(([^)]*)\) uniform (\w+) (\w+);', s)
        if m:
            typ, name = m.group(2), m.group(3)
            cxx = {'texture2D': 'Tex2D', 'texture3D': 'Tex3D', 'sampler': 'Samp', 'samplerBuffer': 'TexBufF', 'usamplerBuffer': 'TexBufU',
                   'isamplerBuffer': 'TexBufI', 'texture2DArray': 'Tex2D', 'textureCube': 'Tex3D'}.get(typ)
            if cxx is None:
                raise ValueError('resource type ' + typ)
            ident = texnames.get(name, name)
            decls.append('static %s %s{texid("%s")};' % (cxx, name, ident))
            i += 1
            continue
        m = re.match(r'layout\(location = \d+\) (flat )?(in|out) (\w+) (\w+);', s)
        if m:
            typ, name = m.group(3), m.group(4)
            typ = 'D' if typ == 'float' else typ
            decls.append('static %s %s;' % (typ, name))
            (inputs if m.group(2) == 'in' else outputs).append((typ, name))
            i += 1
            continue
        if re.match(r'(bool|float|uint|int|vec[234]) \w+;$', s) and not line.startswith(' '):
            # a global of the shader (discard_state)
            decls.append('static ' + s.replace('float ', 'D '))
            i += 1
            continue
        body.append(line)
        i += 1
    code = '\n'.join(body)
    code = re.sub(r'\bfloat\b', 'D', code)
    code = re.sub(r'\bprecise\s+', '', code)
    code = re.sub(r'\bvoid main\(\)', 'void run()', code)
    code = code.replace('discard;', '{ g_discarded = true; return; }')
    code = re.sub(r'discard_exit\(\);', 'discard_exit(); if (g_discarded) return;', code)
    code = re.sub(r'\.(xyz|xy|yz|zw)\b(?!\()', r'.\1()', code)
    code = re.sub(r'\bivec3\(uvec3\(', 'ivec3_(uvec3(', code)
    code = re.sub(r'\bivec2\(uvec2\(', 'ivec2_(uvec2(', code)
    code = re.sub(r'\bnonuniformEXT\(', '(', code)
    out.append('namespace %s {' % ns)
    out.append('using namespace cpuglsl;')
    out.extend(decls)
    out.append(code)
    out.append('void set_inputs(Inputs& in) {')
    for typ, name in inputs:
        out.append('    in.get("%s", %s);' % (name, name))
    out.append('}')
    out.append('void get_outputs(Outputs& o) {')
    for typ, name in outputs:
        out.append('    o.put("%s", %s);' % (name, name))
    out.append('}')
    out.append('} // namespace %s' % ns)
    return '\n'.join(out)


if __name__ == '__main__':
    src = open(sys.argv[1]).read()
    tex = json.load(open(sys.argv[4])) if len(sys.argv) > 4 else {}
    open(sys.argv[3], 'w').write(transpile(src, sys.argv[2], tex))
