"""Patch a game pixel shader's blue-noise dither (FINAL FANTASY VII REBIRTH, RM_Surface coverage test), in its DXIL text.

The game's cut-out test:
    Slice = (round(ConstantContext) + (View.StateFrameIndex & 7)) & 63          -> 8 of the volume's 64 slices
    Noise = View.SpatiotemporalBlueNoiseVolumeTexture.Load(SvPosition.x & 127, SvPosition.y & 127, Slice)
    keep  = DynamicCoverage > Noise.w * 0.996 + 0.002  &&  Coverage > Noise.x * 0.996 + 0.002

Patched (the cut-off comparisons stay exactly the game's):
    Slice = (round(ConstantContext) + View.StateFrameIndex) & 63                 -> all 64 slices, one per frame
    Noise = Load(Cell.u & 127, Cell.v & 127, Slice), Cell = floor(UV * 2^-round(log2(footprint)))
            (hashed alpha: the noise is anchored to the surface's texture coordinates, one cell about one pixel
             along each UV axis, so it moves with the strands and two overlapping cards get different thresholds)
"""
import re

FRAME_LOAD = re.compile(r'^  (%\w+) = call %dx\.types\.CBufRet\.i32 @dx\.op\.cbufferLoadLegacy\.i32\(i32 59, %dx\.types\.Handle %\w+, i32 175\)', re.M)
EXTRACT = r'^  (%%\w+) = extractvalue %%dx\.types\.CBufRet\.i32 %s, 0'
AND7 = r'^  (%%\w+) = and i32 %s, 7$'
TEXLOAD = re.compile(r'^  (%\w+) = call %dx\.types\.ResRet\.f32 @dx\.op\.textureLoad\.f32\(i32 66, %dx\.types\.Handle (%\w+), i32 0, i32 (%\w+), i32 (%\w+), i32 (%\w+), i32 undef, i32 undef, i32 undef\)', re.M)
EXTRACT_F = r'^  (%%\w+) = extractvalue %%dx\.types\.ResRet\.f32 %s, (\d)'
SAMPLE = re.compile(r'^  (%\w+) = call %dx\.types\.ResRet\.f32 @dx\.op\.sample(?:Bias|Level|Grad)?\.f32\(i32 \d+, %dx\.types\.Handle %\w+, %dx\.types\.Handle %\w+, float (%\w+), float (%\w+),', re.M)


class PatchError(Exception):
    pass


def _def_line(text, name):
    m = re.search(r'^  %s = .*$' % re.escape(name), text, re.M)
    if not m:
        raise PatchError('no definition of %s' % name)
    return m


def _uses(text, name):
    return re.findall(r'^  (%%\w+) = .*%s\b(?![\w.]).*$' % re.escape(name), text, re.M)


def coverage_uv(text, load):
    """The texture coordinates the coverage texture is sampled at: the sample whose .x is compared with Noise.x."""
    nx = re.search(EXTRACT_F % re.escape(load), text, re.M)
    xs = [m for m in re.finditer(EXTRACT_F % re.escape(load), text, re.M) if m.group(2) == '0']
    if not xs:
        raise PatchError('Noise.x is not read')
    noise_x = xs[0].group(1)
    # noise_x -> fmul -> fadd -> fcmp ogt float %cov, %thr
    mul = [u for u in _uses(text, noise_x)]
    for m1 in mul:
        for a1 in _uses(text, m1):
            for c1 in _uses(text, a1):
                line = _def_line(text, c1).group(0)
                m = re.search(r'fcmp fast ogt float (%\w+), ' + re.escape(a1) + r'\b', line)
                if not m:
                    continue
                cov = m.group(1)
                d = _def_line(text, cov).group(0)
                e = re.search(r'extractvalue %dx\.types\.ResRet\.f32 (%\w+), 0', d)
                if not e:
                    raise PatchError('the coverage value is not a sample: ' + d.strip())
                s = _def_line(text, e.group(1)).group(0)
                sm = SAMPLE.search(s + '\n')
                if not sm:
                    raise PatchError('the coverage value is not a texture sample: ' + s.strip())
                return sm.group(2), sm.group(3)
    raise PatchError('no coverage comparison against Noise.x')


def texcoord0(text):
    """(u, v) loads of TEXCOORD0 from the input signature (for shaders without a coverage texture)."""
    sig = re.search(r'; Input signature:\n;\n; Name +Index +Mask +Register.*\n; [-\s]+\n((?:; .*\n)+)', text)
    if not sig:
        raise PatchError('no input signature')
    rows = [l[2:].split() for l in sig.group(1).splitlines() if l.strip(';').strip()]
    for k, r in enumerate(rows):
        if r[0] == 'TEXCOORD' and r[1] == '0':
            u = re.search(r'^  (%%\w+) = call float @dx\.op\.loadInput\.f32\(i32 4, i32 %d, i32 0, i8 0,' % k, text, re.M)
            v = re.search(r'^  (%%\w+) = call float @dx\.op\.loadInput\.f32\(i32 4, i32 %d, i32 0, i8 1,' % k, text, re.M)
            if u and v:
                return u.group(1), v.group(1)
    raise PatchError('TEXCOORD0 is not loaded')


def patch(text, hashed=True):
    """-> (patched text, report)"""
    fl = FRAME_LOAD.findall(text)
    if len(fl) != 1:
        raise PatchError('%d loads of View.StateFrameIndex' % len(fl))
    ex = re.search(EXTRACT % re.escape(fl[0]), text, re.M)
    if not ex:
        raise PatchError('the frame index is not extracted')
    frame = ex.group(1)
    a7 = re.search(AND7 % re.escape(frame), text, re.M)
    if not a7:
        raise PatchError('no "frame & 7"')
    loads = [m for m in TEXLOAD.finditer(text)]
    loads = [m for m in loads if True]
    if len(loads) != 1:
        raise PatchError('%d 3D texture loads' % len(loads))
    ld = loads[0]
    load, xreg, yreg = ld.group(1), ld.group(3), ld.group(4)
    report = {'frame_mask_line': a7.group(0).strip()}
    out = text[:a7.start()] + '  %s = and i32 %s, 63' % (a7.group(1), frame) + text[a7.end():]
    if hashed:
        try:
            u, v = coverage_uv(out, load)
            report['uv'] = 'coverage sample'
        except PatchError as e:
            u, v = texcoord0(out)
            report['uv'] = 'TEXCOORD0 (%s)' % e
        xm = _def_line(out, xreg)
        ym = _def_line(out, yreg)
        if not re.search(r'= and i32 %\w+, 127$', xm.group(0)) or not re.search(r'= and i32 %\w+, 127$', ym.group(0)):
            raise PatchError('the noise coordinates are not "& 127": %s / %s' % (xm.group(0).strip(), ym.group(0).strip()))
        first = min(xm.start(), ym.start())
        # the uv values must be defined above the coordinate lines
        for name in (u, v):
            if _def_line(out, name).start() > first:
                raise PatchError('%s is defined after the noise coordinates' % name)
        block = '\n'.join([
            '  %hdf_dux = call float @dx.op.unary.f32(i32 83, float {u})'.format(u=u),
            '  %hdf_duy = call float @dx.op.unary.f32(i32 84, float {u})'.format(u=u),
            '  %hdf_dvx = call float @dx.op.unary.f32(i32 83, float {v})'.format(v=v),
            '  %hdf_dvy = call float @dx.op.unary.f32(i32 84, float {v})'.format(v=v),
            '  %hdf_aux = call float @dx.op.unary.f32(i32 6, float %hdf_dux)',
            '  %hdf_auy = call float @dx.op.unary.f32(i32 6, float %hdf_duy)',
            '  %hdf_avx = call float @dx.op.unary.f32(i32 6, float %hdf_dvx)',
            '  %hdf_avy = call float @dx.op.unary.f32(i32 6, float %hdf_dvy)',
            '  %hdf_fu0 = call float @dx.op.binary.f32(i32 35, float %hdf_aux, float %hdf_auy)',
            '  %hdf_fv0 = call float @dx.op.binary.f32(i32 35, float %hdf_avx, float %hdf_avy)',
            '  %hdf_fu = call float @dx.op.binary.f32(i32 35, float %hdf_fu0, float 0x3EB0C6F7A0000000)',
            '  %hdf_fv = call float @dx.op.binary.f32(i32 35, float %hdf_fv0, float 0x3EB0C6F7A0000000)',
            '  %hdf_lu = call float @dx.op.unary.f32(i32 23, float %hdf_fu)',
            '  %hdf_lv = call float @dx.op.unary.f32(i32 23, float %hdf_fv)',
            '  %hdf_ru = call float @dx.op.unary.f32(i32 26, float %hdf_lu)',
            '  %hdf_rv = call float @dx.op.unary.f32(i32 26, float %hdf_lv)',
            '  %hdf_nu = fsub fast float -0.000000e+00, %hdf_ru',
            '  %hdf_nv = fsub fast float -0.000000e+00, %hdf_rv',
            '  %hdf_su = call float @dx.op.unary.f32(i32 21, float %hdf_nu)',
            '  %hdf_sv = call float @dx.op.unary.f32(i32 21, float %hdf_nv)',
            '  %hdf_cu = fmul fast float {u}, %hdf_su'.format(u=u),
            '  %hdf_cv = fmul fast float {v}, %hdf_sv'.format(v=v),
            '  %hdf_gu = call float @dx.op.unary.f32(i32 27, float %hdf_cu)',
            '  %hdf_gv = call float @dx.op.unary.f32(i32 27, float %hdf_cv)',
            '  %hdf_iu = fptosi float %hdf_gu to i32',
            '  %hdf_iv = fptosi float %hdf_gv to i32',
        ]) + '\n'
        xname = re.match(r'  (%\w+) = ', xm.group(0)).group(1)
        yname = re.match(r'  (%\w+) = ', ym.group(0)).group(1)
        # replace the two coordinate lines (in place), the block above the first of them
        lines = out.split('\n')
        for k, l in enumerate(lines):
            if l.startswith('  %s = and i32 ' % xname) and l.endswith(', 127'):
                lines[k] = '  %s = and i32 %%hdf_iu, 127' % xname
            elif l.startswith('  %s = and i32 ' % yname) and l.endswith(', 127'):
                lines[k] = '  %s = and i32 %%hdf_iv, 127' % yname
        out = '\n'.join(lines)
        at = min(out.index('  %s = and i32 %%hdf_iu, 127' % xname), out.index('  %s = and i32 %%hdf_iv, 127' % yname))
        out = out[:at] + block + out[at:]
        # the derivative ops need their declarations
        decl_unary = 'declare float @dx.op.unary.f32(i32, float)'
        decl_binary = 'declare float @dx.op.binary.f32(i32, float, float)'
        if decl_unary not in out:
            out = out.replace('\n; Function Attrs:', '\n; Function Attrs: nounwind readnone\n%s #0\n\n; Function Attrs:' % decl_unary, 1)
        if decl_binary not in out:
            out = out.replace('\n; Function Attrs:', '\n; Function Attrs: nounwind readnone\n%s #0\n\n; Function Attrs:' % decl_binary, 1)
        report['uv_regs'] = [u, v]
        report['coords'] = [xname, yname]
    return out, report
