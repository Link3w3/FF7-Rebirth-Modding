"""Stand-in for UnrealHeaderTool's .generated.h (enough for a syntax check): per GENERATED_BODY line, the struct or class body."""
import re, sys
header, out, module = sys.argv[1], sys.argv[2], sys.argv[3]
lines = open(header, encoding='utf-8').read().split('\n')
fid = 'SKELCHECK_FILE_ID'
text = ['#include "UObject/ObjectMacros.h"', '#include "UObject/ScriptMacros.h"', '#undef CURRENT_FILE_ID', '#define CURRENT_FILE_ID ' + fid]
pending = None
api = module.upper() + '_API'
for i, line in enumerate(lines, 1):
    s = line.strip()
    if s.startswith('USTRUCT'): pending = 'struct'
    elif s.startswith('UCLASS'):
        pending = 'class'
        text.append('#define %s_%d_PROLOG' % (fid, i))
    elif s.startswith('UENUM'): pending = 'enum'
    m = re.match(r'(struct|class)\s+(?:\w+_API\s+)?(\w+)\s*(?::\s*public\s+(\w+))?', s)
    if m and pending in ('struct', 'class') and not s.endswith(';'):
        kind, name, base = pending, m.group(2), m.group(3)
        pending = (kind, name, base)
        continue
    m = re.match(r'enum\s+class\s+(\w+)\s*:\s*(\w+)', s)
    if m and pending == 'enum':
        text.append('enum class %s : %s; template<> %s UEnum* StaticEnum<%s>();' % (m.group(1), m.group(2), api, m.group(1)))
        pending = None
        continue
    if 'GENERATED_BODY()' in s and isinstance(pending, tuple):
        kind, name, base = pending
        macro = '%s_%d_GENERATED_BODY' % (fid, i)
        if kind == 'struct':
            text.append('#define %s friend struct Z_Construct_UScriptStruct_%s_Statics; static class UScriptStruct* StaticStruct();' % (macro, name))
            text.append('template<> %s UScriptStruct* StaticStruct<struct %s>();' % (api, name))
        else:
            funcs = []
            j = i
            depth = 0
            for k in range(i, len(lines)):
                t = lines[k].strip()
                if t.startswith('UFUNCTION'):
                    for q in range(k + 1, min(k + 4, len(lines))):
                        mm = re.search(r'(\w+)\s*\(', lines[q].replace('virtual ', '').replace('static ', ''))
                        if mm and not lines[q].strip().startswith(('//', '/*', '*')):
                            name2 = re.findall(r'(\w+)\s*\(', lines[q])[-1] if False else re.search(r'\b(\w+)\s*\((?!.*\()', lines[q])
                            fn = re.findall(r'\b(\w+)\s*\(', lines[q])
                            funcs.append(fn[0] if fn[0] not in ('UFUNCTION',) else fn[1]); break
                if t.startswith('};'): break
            body = ' '.join('DECLARE_FUNCTION(exec%s);' % f for f in funcs)
            declared = any(re.search(r'\b%s\s*\(' % name, lines[k]) for k in range(i, len(lines)) if not lines[k].strip().startswith(('//', '/*', '*')))
            text.append('#define %s public: %s private: static void StaticRegisterNatives%s(); friend struct Z_Construct_UClass_%s_Statics; public: '
                        'DECLARE_CLASS(%s, %s, COMPILED_IN_FLAGS(0), CASTCLASS_None, TEXT("/Script/%s"), NO_API) DECLARE_SERIALIZER(%s) '
                        'private: NO_API %s(%s&&); NO_API %s(const %s&); public: DECLARE_VTABLE_PTR_HELPER_CTOR(NO_API, %s); '
                        'DEFINE_VTABLE_PTR_HELPER_CTOR_CALLER(%s); %s private:'
                        % (macro, body, name, name, name, base, module, name, name, name, name, name, name, name,
                           ('DEFINE_DEFAULT_CONSTRUCTOR_CALL(%s)' % name) if declared else
                           ('public: NO_API %s(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get()); DEFINE_DEFAULT_OBJECT_INITIALIZER_CONSTRUCTOR_CALL(%s)' % (name, name))))
            text.append('template<> %s UClass* StaticClass<class %s>();' % (api, name))
        pending = None
open(out, 'w').write('\n'.join(text) + '\n')
