# (re)puts the Customization code (custom_*.inc) into src/RebirthSkelCompat.cpp, in place of the copy there
src = 'src/RebirthSkelCompat.cpp'
c = open(src).read()
custom = ''.join(open(f).read() for f in ['custom_a.inc', 'custom_b.inc', 'custom_c.inc', 'custom_d.inc', 'custom_e.inc', 'custom_f.inc', 'custom_g.inc'])
start_marker = custom.split('\n', 1)[0] + '\n' + custom.split('\n', 2)[1]
first = custom.split('\n', 1)[0]
i = c.find('// 3.11.0: Customization.')
if i >= 0:
    i = c.rfind('\n// ----', 0, i) + 1
    j = c.index('} // namespace Custom\n', i) + len('} // namespace Custom\n')
    c = c[:i] + custom + c[j:]
else:
    raise SystemExit('no Customization block to replace')
fwd = "std::string ReadFileBytes(const fs::path& path);   // (3.11.0: defined below)\n\nnamespace Forms\n{\nuint64_t NowMs();"
if fwd not in c:
    old = "namespace Forms\n{\nuint64_t NowMs();"
    assert c.count(old) == 1
    c = c.replace(old, fwd)
open(src, 'w').write(c)
print('ok', len(c))
