"""Reflected property layouts (UE 4.26 cooked game: no editor-only data) read from C++ headers.

Classes and structs: name -> {'base', 'props': [(name, type, dim)], 'kind', 'file'}; enums: name -> underlying type.
Unversioned property data lists a struct's own properties first, then its base's (the PropertyLink order).
Preprocessor: WITH_EDITORONLY_DATA, WITH_EDITOR and CPP are 0 (so "#if !CPP" blocks, the reflection declarations of
noexport types, are read); anything unknown counts as 1 and is reported."""
import os, re, sys

ROOTS = [
    '/work/uesdk/Engine/Source/Runtime/CoreUObject/Public/UObject/NoExportTypes.h',
    '/work/uesdk/Engine/Source/Runtime/MovieScene/Public',
    '/work/uesdk/Engine/Source/Runtime/MovieSceneTracks/Public',
    '/work/uesdk/Engine/Source/Runtime/Engine/Classes',
    '/work/uesdk/Engine/Source/Runtime/Engine/Public',
    '/work/bizcut1015/hdr/extra',
    '/work/bizcut1015/hdr/LevelSequence',
    '/work/bizcut1015/hdr/EndGame',
]
DEFINES = {'WITH_EDITORONLY_DATA': 0, 'WITH_EDITOR': 0, 'CPP': 0, 'UE_BUILD_SHIPPING': 1, 'UE_BUILD_DEBUG': 0,
           'WITH_ENGINE': 1, 'PLATFORM_WINDOWS': 1, 'UE_SERVER': 0, 'WITH_DEV_AUTOMATION_TESTS': 0, 'STATS': 0,
           'ENABLE_NAN_DIAGNOSTIC': 0, 'DO_CHECK': 0, 'WITH_PHYSX': 1, 'WITH_CHAOS': 0, 'PHYSICS_INTERFACE_PHYSX': 1,
           'UE_ENABLE_DEBUG_DRAWING': 0, 'ENABLE_VISUAL_LOG': 0, 'WITH_APEX': 0, 'WITH_PHYSX_COOKING': 0}
UNKNOWN = set()


def strip_comments(text):
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == '/' and i + 1 < n and text[i + 1] == '/':
            j = text.find('\n', i)
            i = n if j < 0 else j
            continue
        if c == '/' and i + 1 < n and text[i + 1] == '*':
            j = text.find('*/', i + 2)
            seg = text[i:(n if j < 0 else j + 2)]
            out.append('\n' * seg.count('\n'))
            i = n if j < 0 else j + 2
            continue
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == '\\' else 1
            out.append(text[i:j + 1])
            i = j + 1
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def eval_cond(expr):
    e = expr.strip()
    e = re.sub(r'defined\s*\(\s*(\w+)\s*\)', lambda m: '1' if DEFINES.get(m.group(1), 0) else '0', e)
    e = re.sub(r'defined\s+(\w+)', lambda m: '1' if DEFINES.get(m.group(1), 0) else '0', e)

    def name(m):
        k = m.group(0)
        if k in DEFINES:
            return str(DEFINES[k])
        if re.match(r'^\d', k):
            return k
        UNKNOWN.add(k)
        return '1'
    e = re.sub(r'\b[A-Za-z_]\w*\b', name, e)
    e = e.replace('&&', ' and ').replace('||', ' or ').replace('!', ' not ').replace(' not =', '!=')
    try:
        return bool(eval(e))
    except Exception:
        UNKNOWN.add('expr:' + expr.strip())
        return True


def preprocess(text):
    lines = text.split('\n')
    out = []
    stack = []   # (active, taken)

    def active():
        return all(a for a, _ in stack)
    for line in lines:
        s = line.strip()
        m = re.match(r'#\s*(if|ifdef|ifndef|elif|else|endif)\b(.*)', s)
        if m:
            d, rest = m.group(1), m.group(2)
            if d == 'if':
                v = eval_cond(rest)
                stack.append([v, v])
            elif d == 'ifdef':
                v = bool(DEFINES.get(rest.strip(), 0))
                stack.append([v, v])
            elif d == 'ifndef':
                v = not DEFINES.get(rest.strip(), 0)
                stack.append([v, v])
            elif d == 'elif':
                if stack:
                    top = stack[-1]
                    if top[1]:
                        top[0] = False
                    else:
                        v = eval_cond(rest)
                        top[0] = v
                        top[1] = v
            elif d == 'else':
                if stack:
                    top = stack[-1]
                    top[0] = not top[1]
                    top[1] = True
            elif d == 'endif':
                if stack:
                    stack.pop()
            out.append('')
            continue
        out.append(line if active() else '')
    return '\n'.join(out)


def balanced(text, i, open_c='(', close_c=')'):
    """Index just past the bracket matching text[i] (== open_c)."""
    depth = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == open_c:
            depth += 1
        elif c == close_c:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


def split_decl(decl):
    """'TArray<FFoo> Bar[3]' -> ('TArray<FFoo>', 'Bar', 3); bitfields 'uint8 bX : 1' -> bool."""
    d = ' '.join(decl.replace('\n', ' ').split())
    d = re.sub(r'\s*=\s*[^;]*$', '', d)            # default member initializers
    bit = False
    m = re.match(r'^(.*?)\s*:\s*\d+\s*$', d)
    if m and '<' not in d[m.end(1):]:
        d = m.group(1)
        bit = True
    dim = 1
    m = re.match(r'^(.*)\[\s*([^\]]+)\s*\]\s*$', d)
    if m:
        d = m.group(1).strip()
        try:
            dim = int(eval(m.group(2), {}, {}))
        except Exception:
            dim = m.group(2)
    m = re.match(r'^(.*?)([A-Za-z_]\w*)\s*$', d)
    if not m:
        return None
    t, name = m.group(1).strip(), m.group(2)
    for q in ('mutable ', 'const ', 'volatile '):
        if t.startswith(q):
            t = t[len(q):]
    t = re.sub(r'\b(class|struct|enum)\s+', '', t)
    t = re.sub(r'\s*\*\s*', '*', t)
    t = re.sub(r'\s*<\s*', '<', t)
    t = re.sub(r'\s*>\s*', '>', t)
    t = re.sub(r'\s*,\s*', ', ', t)
    if bit:
        t = 'bool'
    return t.strip(), name, dim


def parse_text(text, fn, out, enums):
    text = preprocess(strip_comments(text))
    # enums (UENUM'd or not): "enum class E : uint8 {", "enum E : uint8 {", "namespace E { enum Type {"
    for m in re.finditer(r'\benum\s+(?:class\s+)?(\w+)\s*(?::\s*(\w+))?\s*\{', text):
        nm, under = m.group(1), m.group(2)
        if nm == 'Type':
            ns = re.findall(r'namespace\s+(\w+)\s*\{[^{}]*$', text[:m.start()])
            if ns:
                enums.setdefault(ns[-1], under or 'uint8')
                enums.setdefault(ns[-1] + '::Type', under or 'uint8')
            continue
        enums.setdefault(nm, under or 'int32')
    for m in re.finditer(r'\b(UCLASS|USTRUCT)\s*\(', text):
        kind = m.group(1)
        j = balanced(text, m.end() - 1)
        hm = re.match(r'\s*(class|struct)\s+(?:\w+_API\s+)?(?:alignas\(\d+\)\s+)?(\w+)\s*(?:final\s*)?(?::\s*public\s+([\w:]+)[^{]*)?\{',
                      text[j:])
        if not hm:
            continue
        name, base = hm.group(2), hm.group(3)
        body_start = j + hm.end()
        body_end = balanced(text, body_start - 1, '{', '}')
        body = text[body_start:body_end - 1]
        props = []
        for pm in re.finditer(r'\bUPROPERTY\s*\(', body):
            k = balanced(body, pm.end() - 1)
            # the declaration: up to the next ';' at depth 0
            depth, q = 0, k
            while q < len(body):
                c = body[q]
                if c in '<({':
                    depth += 1
                elif c in '>)}':
                    depth -= 1
                elif c == ';' and depth <= 0:
                    break
                q += 1
            r = split_decl(body[k:q])
            if r:
                props.append(r)
        if name in out and out[name]['props'] and not props:
            continue
        out[name] = {'base': base, 'props': props, 'kind': kind, 'file': fn}


def load(roots=ROOTS):
    out, enums = {}, {}
    files = []
    for r in roots:
        if os.path.isfile(r):
            files.append(r)
            continue
        for dp, dn, fns in os.walk(r):
            for f in sorted(fns):
                if f.endswith('.h'):
                    files.append(os.path.join(dp, f))
    for f in files:
        try:
            text = open(f, encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        parse_text(text, f, out, enums)
    return out, enums


if __name__ == '__main__':
    S, E = load()
    print(len(S), 'types', len(E), 'enums; unknown macros:', sorted(UNKNOWN)[:40])
    for k in sys.argv[1:]:
        s = S.get(k)
        print(k, s and (s['base'], s['file']))
        for p in (s['props'] if s else []):
            print('   ', p)
