"""UE 4.17's UMaterial::AppendReferencedTextures order: for each expression of the material in order, a function call
adds its function then that function's dependent functions (GetDependentFunctions: nested first, AddUnique) and each of
those adds its own expressions' textures (AddUnique); any other expression adds its texture."""
import struct
import sys
sys.path[:0] = ['/work/kh3mat1018/tools', '/work/kh3fx', '/work/kh3bnm/src/rebirth_fx']
import kh3mat, tagged


# Engine material functions' own texture expressions (read from the engine's content): DitherTemporalAA samples a noise
# texture, which takes a slot in every KH3 material that dithers.
ENGINE_FUNCTION_TEXTURES = {
    '/Engine/Functions/Engine_MaterialFunctions02/Utility/DitherTemporalAA.DitherTemporalAA':
        ['/Engine/EngineMaterials/Good64x64TilingNoiseHighFreq.Good64x64TilingNoiseHighFreq'],
}


def _exprs(lib, path):
    if path in ENGINE_FUNCTION_TEXTURES:
        return [('tex', t) for t in ENGINE_FUNCTION_TEXTURES[path]]
    if not path.startswith('/Game/') or not lib.exists(path):
        return []
    pk = lib.package(path)
    e = lib.top(pk, ('Material', 'MaterialFunction'))
    tp = lib.props(pk, e)
    arr = tagged.find(tp, 'Expressions') or tagged.find(tp, 'FunctionExpressions')
    out = []
    for a, _, _ in (arr.elements if arr else []):
        v = struct.unpack_from('<i', pk.data, a)[0]
        if v <= 0:
            continue
        ex = pk.exports[v - 1]
        c = pk.class_name(ex)
        pp = lib.props(pk, ex)
        if c == 'MaterialExpressionMaterialFunctionCall':
            f = tagged.find(pp, 'MaterialFunction')
            out.append(('call', kh3mat._value(pk, f) if f else None))
        else:
            t = tagged.find(pp, 'Texture')
            out.append(('tex', kh3mat._value(pk, t) if t else None))
    return out


def dependents(lib, fn, acc):
    for kind, v in _exprs(lib, fn):
        if kind == 'call' and v:
            dependents(lib, v, acc)
            if v not in acc:
                acc.append(v)
    return acc


def function_textures(lib, fn, out):
    for kind, v in _exprs(lib, fn):
        if kind == 'tex' and v and v not in out:
            out.append(v)


def refs(lib, path, postorder=True):
    out = []
    for kind, v in _exprs(lib, path):
        if kind == 'call':
            if not v:
                continue
            fns = [v]
            for d in dependents(lib, v, []):
                if d not in fns:
                    fns.append(d)
            for f in fns:
                function_textures(lib, f, out)
        elif v and v not in out:
            out.append(v)
    return out
