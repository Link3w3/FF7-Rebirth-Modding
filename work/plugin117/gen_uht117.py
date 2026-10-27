"""Writes a stand-in for UnrealHeaderTool's <Header>.generated.h (enough for a clang syntax check) from the header itself:
USTRUCT / UCLASS GENERATED_BODY macros at the right line numbers, exec thunk declarations for UFUNCTIONs, UENUM FOREACH.
    gen_uht.py <header.h> <file id> <api macro> <out.generated.h>"""
import re, sys
header, file_id, api, out = sys.argv[1:5]
lines = open(header, encoding='utf-8').read().split('\n')
text = []
guard = api.replace('_API', '') + '_' + header.split('/')[-1].replace('.h', '') + '_generated_h'
text.append('#include "UObject/ObjectMacros.h"\n#include "UObject/ScriptMacros.h"\nPRAGMA_DISABLE_DEPRECATION_WARNINGS')
text.append('#ifdef %s\n#error "already included"\n#endif\n#define %s' % (guard, guard))
i = 0
pending = None  # ('struct'|'class', macro line)
enums = []
while i < len(lines):
    line = lines[i].strip()
    n = i + 1
    if line.startswith('USTRUCT('):
        pending = ('struct', n)
    elif line.startswith('UCLASS('):
        pending = ('class', n)
    elif line.startswith('UENUM('):
        m = re.match(r'enum\s+class\s+(\w+)', lines[i + 1].strip())
        values = []
        j = i + 2
        while not lines[j].strip().startswith('};'):
            v = re.match(r'\s*(\w+)\s*(UMETA\(.*\))?\s*,?', lines[j])
            if v and v.group(1) and not lines[j].strip().startswith(('/', '*', '{')):
                values.append(v.group(1))
            j += 1
        enums.append((m.group(1), values))
    elif pending and re.match(r'(struct|class)\s', line):
        m = re.match(r'(struct|class)\s+(?:\w+_API\s+)?(\w+)(?:\s*:\s*public\s+(\w+))?', line)
        kind, macro_line = pending
        name, parent = m.group(2), m.group(3)
        # GENERATED_BODY line and, for a class, its UFUNCTIONs
        j = i
        while 'GENERATED_BODY()' not in lines[j]:
            j += 1
        body = j + 1
        funcs = []
        depth = 0
        k = j
        while k < len(lines):
            if lines[k].startswith('};'):
                break
            if lines[k].strip().startswith('UFUNCTION('):
                f = re.search(r'(\w+)\s*\(', re.sub(r'^\s*(static\s+|virtual\s+)?[\w:<>,\s\*&]+?\s+', '', lines[k + 1].strip(), count=1))
                fm = re.search(r'\b(\w+)\s*\(', lines[k + 1])
                funcs.append(fm.group(1))
            k += 1
        P = '%s_%d' % (file_id, body)
        if kind == 'struct':
            text.append('#define %s_GENERATED_BODY \\\n\tfriend struct Z_Construct_UScriptStruct_%s_Statics; \\\n\tstatic class UScriptStruct* StaticStruct();\n' % (P, name))
            text.append('template<> %s UScriptStruct* StaticStruct<struct %s>();' % (api, name))
        else:
            thunks = ' \\\n'.join('\tDECLARE_FUNCTION(exec%s);' % f for f in reversed(funcs))
            short = name[1:]
            text.append('#define %s_SPARSE_DATA' % P)
            text.append('#define %s_RPC_WRAPPERS \\\n%s\n' % (P, thunks))
            text.append('#define %s_RPC_WRAPPERS_NO_PURE_DECLS \\\n%s\n' % (P, thunks))
            for suffix in ('INCLASS_NO_PURE_DECLS', 'INCLASS'):
                text.append('#define %s_%s \\\nprivate: \\\n\tstatic void StaticRegisterNatives%s(); \\\n\tfriend struct Z_Construct_UClass_%s_Statics; \\\npublic: \\\n'
                            '\tDECLARE_CLASS(%s, %s, COMPILED_IN_FLAGS(0), CASTCLASS_None, TEXT("/Script/%s"), NO_API) \\\n\tDECLARE_SERIALIZER(%s)\n'
                            % (P, suffix, name, name, name, parent, api.replace('_API', ''), name))
            text.append('#define %s_STANDARD_CONSTRUCTORS \\\n\tNO_API %s(const FObjectInitializer& ObjectInitializer); \\\n\tDEFINE_DEFAULT_OBJECT_INITIALIZER_CONSTRUCTOR_CALL(%s) \\\n'
                        '\tDECLARE_VTABLE_PTR_HELPER_CTOR(NO_API, %s); \\\nDEFINE_VTABLE_PTR_HELPER_CTOR_CALLER(%s); \\\nprivate: \\\n\tNO_API %s(%s&&); \\\n\tNO_API %s(const %s&); \\\npublic:\n'
                        % (P, name, name, name, name, name, name, name, name))
            # (a class that declares no constructor gets UHT's ObjectInitializer one)
            body_text = '\n'.join(lines[j:k])
            declares = re.search(r'\b%s\s*\(' % re.escape(name), body_text) is not None
            own = '' if declares else '\tNO_API %s(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get()) : Super(ObjectInitializer) { }; \\\n' % name
            call = 'DEFINE_DEFAULT_CONSTRUCTOR_CALL' if declares else 'DEFINE_DEFAULT_OBJECT_INITIALIZER_CONSTRUCTOR_CALL'
            text.append('#define %s_ENHANCED_CONSTRUCTORS \\\n%sprivate: \\\n\tNO_API %s(%s&&); \\\n\tNO_API %s(const %s&); \\\npublic: \\\n'
                        '\tDECLARE_VTABLE_PTR_HELPER_CTOR(NO_API, %s); \\\nDEFINE_VTABLE_PTR_HELPER_CTOR_CALLER(%s); \\\n\t%s(%s)\n'
                        % (P, own, name, name, name, name, name, name, call, name))
            text.append('#define %s_PRIVATE_PROPERTY_OFFSET' % P)
            text.append('#define %s_%d_PROLOG' % (file_id, macro_line))
            text.append('#define %s_GENERATED_BODY \\\nPRAGMA_DISABLE_DEPRECATION_WARNINGS \\\npublic: \\\n\t%s_PRIVATE_PROPERTY_OFFSET \\\n\t%s_SPARSE_DATA \\\n'
                        '\t%s_RPC_WRAPPERS_NO_PURE_DECLS \\\n\t%s_INCLASS_NO_PURE_DECLS \\\n\t%s_ENHANCED_CONSTRUCTORS \\\nprivate: \\\nPRAGMA_ENABLE_DEPRECATION_WARNINGS\n'
                        % (P, P, P, P, P, P))
            text.append('template<> %s UClass* StaticClass<class %s>();' % (api, name))
        pending = None
    i += 1
text.append('#undef CURRENT_FILE_ID\n#define CURRENT_FILE_ID %s' % file_id)
for name, values in enums:
    text.append('#define FOREACH_ENUM_%s(op) \\\n%s\n' % (name.upper(), ' \\\n'.join('\top(%s::%s)' % (name, v) for v in values)))
    text.append('enum class %s : uint8;\ntemplate<> %s UEnum* StaticEnum<%s>();' % (name, api, name))
text.append('PRAGMA_ENABLE_DEPRECATION_WARNINGS')
open(out, 'w').write('\n'.join(text) + '\n')
print('wrote', out)
