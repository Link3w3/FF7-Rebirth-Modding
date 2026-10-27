"""List UPROPERTYs of UCLASS/USTRUCTs in UE headers in declaration order, with preprocessor context,
to build a 4.26 schema by hand when no usmap is available.
    hdrschema.py <header> [TypeName ...]"""
import re, sys

def parse(path):
    src = open(path, encoding='utf-8', errors='replace').read()
    # strip comments
    src = re.sub(r'/\*.*?\*/', lambda m: '\n' * m.group(0).count('\n'), src, flags=re.S)
    src = re.sub(r'//[^\n]*', '', src)
    lines = src.split('\n')
    types = []
    stack = []   # preprocessor condition stack
    cur = None
    depth = 0
    pending_uprop = None
    pending_type = None
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if ln.startswith('#if'):
            stack.append(ln)
        elif ln.startswith('#elif'):
            if stack: stack[-1] = ln
        elif ln.startswith('#else'):
            if stack: stack[-1] = stack[-1] + ' #else'
        elif ln.startswith('#endif'):
            if stack: stack.pop()
        m = re.match(r'(UCLASS|USTRUCT)\s*\(', ln)
        if m:
            pending_type = m.group(1)
        if pending_type:
            m2 = re.match(r'(?:class|struct)\s+(?:[A-Z_]+_API\s+)?(\w+)(?:\s+final)?\s*(?::\s*public\s+([\w:]+))?', ln)
            if m2 and not ln.endswith(';'):
                cur = {'kind': pending_type, 'name': m2.group(1), 'super': m2.group(2), 'props': [], 'cond': list(stack)}
                types.append(cur)
                pending_type = None
        if ln.startswith('UPROPERTY'):
            # gather the declaration (may span lines)
            spec = ln
            j = i
            while spec.count('(') > spec.count(')'):
                j += 1; spec += ' ' + lines[j].strip()
            decl = ''
            j += 1
            while j < len(lines) and ';' not in decl:
                decl += ' ' + lines[j].strip(); j += 1
            decl = decl.strip()
            if cur is not None:
                editor = any('WITH_EDITOR' in c and '#else' not in c for c in stack)
                cur['props'].append({'decl': decl, 'spec': spec, 'editor': editor, 'cond': list(stack)})
            i = j - 1
        i += 1
    return types

if __name__ == '__main__':
    want = sys.argv[2:]
    for t in parse(sys.argv[1]):
        if want and t['name'] not in want:
            continue
        print('%s %s : %s %s' % (t['kind'], t['name'], t['super'], t['cond'] or ''))
        k = 0
        for p in t['props']:
            tag = 'EDITOR ' if p['editor'] else ''
            tr = 'transient ' if re.search(r'\b[Tt]ransient\b', p['spec']) else ''
            print('   %s%s%s   %s' % (('%3d ' % k) if not p['editor'] else '    ', tag, tr, p['decl']))
            if not p['editor']:
                m = re.search(r'\[(\w+)\]\s*;', p['decl'])
                k += 1
