"""Reflection schema of the BonamikRt types, read from the reconstructed headers (property order = game order)."""
import os, re

PUB = '/work/bnm/Plugins/BonamikPlugin/Source/BonamikRt/Public'

PRIMS = {'bool', 'uint8', 'int8', 'uint16', 'int16', 'uint32', 'int32', 'uint64', 'int64', 'float', 'double',
         'FString', 'FName', 'FText'}
NATIVE_STRUCTS = {'FVector': 12, 'FQuat': 16, 'FRotator': 12, 'FVector2D': 8, 'FColor': 4, 'FLinearColor': 16,
                  'FGuid': 16, 'FIntPoint': 8, 'FVector4': 16}

def parse_headers(pub=PUB):
    structs, enums = {}, {}
    for fn in sorted(os.listdir(pub)):
        if not fn.endswith('.h'):
            continue
        text = open(os.path.join(pub, fn), encoding='utf-8', errors='replace').read()
        # enums: "enum class E : uint8 {" or "enum E {" (TEnumAsByte)
        for m in re.finditer(r'enum\s+(?:class\s+)?(E\w+)\s*(?::\s*(\w+))?\s*\{', text):
            enums[m.group(1)] = m.group(2) or 'uint8'
        for m in re.finditer(r'(?:USTRUCT|UCLASS)\([^)]*\)\s*(?:struct|class)\s+(?:\w+_API\s+)?(\w+)\s*(?::\s*public\s+(\w+))?\s*\{', text):
            name, base = m.group(1), m.group(2)
            body_start = m.end()
            depth, i = 1, body_start
            while depth and i < len(text):
                if text[i] == '{': depth += 1
                elif text[i] == '}': depth -= 1
                i += 1
            body = text[body_start:i - 1]
            props = []
            for line in body.split('\n'):
                s = line.strip()
                if not s or s.startswith(('UPROPERTY', 'GENERATED', '//', '#', 'public:', 'private:', 'protected:', 'UFUNCTION')):
                    continue
                if '(' in s or s.startswith(('class ', 'struct ', 'friend ', 'static ', 'virtual ', 'enum ', 'typedef ', 'using ')):
                    continue
                pm = re.match(r'^(.+?)\s*([A-Za-z_]\w*)\s*(?:\[(\d+)\])?\s*;$', s)
                if not pm:
                    continue
                ptype = pm.group(1).replace(' *', '*').strip()
                props.append((pm.group(2), ptype, int(pm.group(3) or 1)))
            structs[name] = {'base': base, 'props': props, 'file': fn}
    return structs, enums

if __name__ == '__main__':
    s, e = parse_headers()
    for k in ['USQEX_BonamikAsset', 'USQEX_BonamikAsset_v2', 'FSQEX_BonamikBodyDesc_v2']:
        print(k, s[k]['base'], len(s[k]['props']), s[k]['props'][:6])
    print(len(s), 'types,', len(e), 'enums', sorted(set(e.values())))
