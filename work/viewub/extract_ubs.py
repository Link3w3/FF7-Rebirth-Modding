"""Uniform buffer layouts of the game (FShaderParametersMetadata members) from ff7rebirth_.exe.

UE 4.26 builds a shader parameter struct's member list from one small function per member: it fills an FMember on the
stack (name [rsp+20h], shader type [rsp+28h], offset [rsp+30h], base type [rsp+34h], precision [rsp+38h], rows [rsp+3Ch],
columns [rsp+40h], elements [rsp+44h], struct [rsp+48h]), appends it, and returns the function of the member declared
before it (the chain ends with a function that returns 0). Following the chain from any member gives the whole struct.

    python3 -I extract_ubs.py <exe> <out.json> [member names to start from...]
"""
import json, re, struct, sys
from collections import defaultdict

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG, X86_REG_RIP, X86_REG_RSP

EXE = sys.argv[1]
OUT = sys.argv[2]
STARTS = sys.argv[3:] or ['SVPositionToTranslatedWorld']

data = open(EXE, 'rb').read()
pe = pefile.PE(EXE, fast_load=True)
SECS = [(s.Name.rstrip(b'\0').decode(), s.VirtualAddress, s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData) for s in pe.sections]
TEXT = [s for s in SECS if s[0] == '.text'][0]


def rva_to_off(rva):
    for n, va, vs, raw, rs in SECS:
        if va <= rva < va + max(vs, rs):
            return raw + rva - va if rva - va < rs else None
    return None


def wstr(rva, maxlen=300):
    o = rva_to_off(rva)
    if o is None:
        return None
    out = []
    for k in range(maxlen):
        if o + 2 * k + 1 >= len(data):
            return None
        c = data[o + 2 * k] | (data[o + 2 * k + 1] << 8)
        if c == 0:
            break
        if c < 32 or c > 126:
            return None
        out.append(chr(c))
    return ''.join(out)


md = Cs(CS_ARCH_X86, CS_MODE_64)
md.detail = True
REG32 = {}


def reg_name(r):
    return md.reg_name(r)


def base64(name):
    """eax/ax/al/rax -> rax etc."""
    m = {'eax': 'rax', 'ax': 'rax', 'al': 'rax', 'ecx': 'rcx', 'cx': 'rcx', 'cl': 'rcx', 'edx': 'rdx', 'dx': 'rdx', 'dl': 'rdx',
         'ebx': 'rbx', 'bx': 'rbx', 'bl': 'rbx', 'esi': 'rsi', 'si': 'rsi', 'sil': 'rsi', 'edi': 'rdi', 'di': 'rdi', 'dil': 'rdi',
         'ebp': 'rbp', 'r8d': 'r8', 'r8b': 'r8', 'r9d': 'r9', 'r9b': 'r9', 'r10d': 'r10', 'r10b': 'r10', 'r11d': 'r11', 'r11b': 'r11'}
    return m.get(name, name)


def member_function(start_rva):
    """Simulate one member function: (fields dict at stack offsets, returned function rva) or None."""
    off = rva_to_off(start_rva)
    regs = {}
    stack = {}
    ret = None
    count = 0
    for insn in md.disasm(data[off:off + 400], start_rva):
        count += 1
        if count > 80:
            return None
        mn = insn.mnemonic
        ops = insn.operands
        if mn == 'ret':
            ret = regs.get('rax')
            break
        if mn in ('jmp',) and ops and ops[0].type == X86_OP_IMM:
            return None
        if mn == 'lea' and ops[1].type == X86_OP_MEM and ops[1].mem.base == X86_REG_RIP:
            regs[base64(reg_name(ops[0].reg))] = insn.address + insn.size + ops[1].mem.disp
            continue
        if mn == 'lea':
            mem = ops[1].mem
            dst = base64(reg_name(ops[0].reg))
            value = mem.disp
            ok = True
            if mem.base:
                b = regs.get(base64(reg_name(mem.base)))
                ok &= b is not None
                value += b or 0
            if mem.index:
                x = regs.get(base64(reg_name(mem.index)))
                ok &= x is not None
                value += (x or 0) * mem.scale
            if ok:
                regs[dst] = value & 0xFFFFFFFFFFFFFFFF
            else:
                regs.pop(dst, None)
            continue
        if mn == 'xor' and ops[0].type == X86_OP_REG and ops[1].type == X86_OP_REG and ops[0].reg == ops[1].reg:
            regs[base64(reg_name(ops[0].reg))] = 0
            continue
        if mn == 'mov' and ops[0].type == X86_OP_REG:
            dst = base64(reg_name(ops[0].reg))
            if ops[1].type == X86_OP_IMM:
                regs[dst] = ops[1].imm & 0xFFFFFFFFFFFFFFFF
            elif ops[1].type == X86_OP_REG:
                src = base64(reg_name(ops[1].reg))
                if src in regs:
                    regs[dst] = regs[src]
                else:
                    regs.pop(dst, None)
            else:
                regs.pop(dst, None)
            continue
        if mn == 'mov' and ops[0].type == X86_OP_MEM and ops[0].mem.base == X86_REG_RSP:
            disp = ops[0].mem.disp
            size = ops[0].size
            if ops[1].type == X86_OP_IMM:
                v = ops[1].imm & ((1 << (8 * size)) - 1)
            elif ops[1].type == X86_OP_REG:
                v = regs.get(base64(reg_name(ops[1].reg)))
                if v is None:
                    continue
                v &= (1 << (8 * size)) - 1
            else:
                continue
            for k in range(size):
                stack[disp + k] = (v >> (8 * k)) & 0xFF
            continue
        if mn == 'call':
            continue
        # anything else writing a register forgets it
        if ops and ops[0].type == X86_OP_REG and mn not in ('cmp', 'test', 'push'):
            regs.pop(base64(reg_name(ops[0].reg)), None)

    def rd(at, n):
        if not all((at + k) in stack for k in range(n)):
            return None
        return int.from_bytes(bytes(stack[at + k] for k in range(n)), 'little')

    name_ptr = rd(0x20, 8)
    if name_ptr is None:
        return None
    name = wstr(name_ptr)
    if not name or not re.match(r'^[A-Za-z_]\w*$', name):
        return None
    f = dict(name=name, type_ptr=rd(0x28, 8), offset=rd(0x30, 4), base=rd(0x34, 1), precision=rd(0x38, 4),
             rows=rd(0x3c, 4), columns=rd(0x40, 4), elements=rd(0x44, 4), struct=rd(0x48, 8))
    return f, ret


# 1) every member function: starts "mov [rsp+8], rbx; push rdi" and soon "movsxd rdi, dword ptr [rdx+8]"
n, va, vs, raw, rs = TEXT
code = data[raw:raw + rs]
funcs = {}
for m in re.finditer(rb'\x48\x89\x5C\x24\x08\x57', code):
    i = m.start()
    window = code[i:i + 40]
    if b'\x48\x63\x7A\x08' not in window:
        continue
    rva = va + i
    r = member_function(rva)
    if r is None:
        continue
    funcs[rva] = r
print('member functions:', len(funcs), file=sys.stderr)

# 2) chains: f -> returned (the member declared before)
prev_of = {rva: r[1] for rva, r in funcs.items()}
next_of = defaultdict(list)
for rva, p in prev_of.items():
    if p:
        next_of[p].append(rva)


def chain_from(rva):
    # walk back to the first member, then forward
    seen = set()
    first = rva
    while prev_of.get(first) in funcs and first not in seen:
        seen.add(first)
        first = prev_of[first]
    out = [first]
    cur = first
    seen = {first}
    while True:
        nxt = [x for x in next_of.get(cur, []) if x in funcs]
        if len(nxt) != 1 or nxt[0] in seen:
            break
        cur = nxt[0]
        seen.add(cur)
        out.append(cur)
    return out


BASE = {0: 'INVALID', 1: 'bool', 2: 'int', 3: 'uint', 4: 'float', 5: 'TEXTURE', 6: 'SRV', 7: 'UAV', 8: 'SAMPLER',
        9: 'RDG_TEXTURE', 10: 'RDG_TEXTURE_ACCESS', 11: 'RDG_TEXTURE_SRV', 12: 'RDG_TEXTURE_UAV', 13: 'RDG_BUFFER',
        14: 'RDG_BUFFER_ACCESS', 15: 'RDG_BUFFER_SRV', 16: 'RDG_BUFFER_UAV', 17: 'RDG_UNIFORM_BUFFER',
        18: 'NESTED_STRUCT', 19: 'INCLUDED_STRUCT', 20: 'REFERENCED_STRUCT', 21: 'RENDER_TARGET_BINDING_SLOTS'}

result = {}
by_name = defaultdict(list)
for rva, (f, p) in funcs.items():
    by_name[f['name']].append(rva)
for start in STARTS:
    if start not in by_name:
        print('no member named', start, file=sys.stderr)
        continue
    for rva in by_name[start]:
        chain = chain_from(rva)
        members = []
        for c in chain:
            f = dict(funcs[c][0])
            f['type'] = wstr(f.pop('type_ptr')) if f.get('type_ptr') else None
            f['base_name'] = BASE.get(f['base'], f['base'])
            f['fn'] = hex(c)
            members.append(f)
        key = '%s@%x' % (start, rva)
        result[key] = members
        print(key, len(members), 'members; first', members[0]['name'], 'last', members[-1]['name'], file=sys.stderr)
json.dump(result, open(OUT, 'w'), indent=1)
