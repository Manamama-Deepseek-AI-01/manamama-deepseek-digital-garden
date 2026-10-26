#!/usr/bin/env python3
"""Read a DEX file far enough to disassemble one method — no JDK, no baksmali.

Why this exists: on a stock Android 10 device there is no `java`, so jadx,
apktool and `rea`'s Android tools (which want a JADX MCP jar + JDK) are all
unavailable. Android's own framework jars store their dex *uncompressed*, so a
plain `grep -a` finds the message you saw in logcat and this script reads the
branch that produced it.

Usage:
    python3 dex_method_disasm.py <file.dex>                       # list classes
    python3 dex_method_disasm.py <file.dex> --search onyx         # filter names
    python3 dex_method_disasm.py <file.dex> 'Landroid/onyx/pm/X;' # all methods
    python3 dex_method_disasm.py <file.dex> 'Landroid/onyx/pm/X;' isAllow

Layout note, paid for in blood: the `35c`/`3rc` invoke formats put the
**method/type index first** and the register list after it —

    35c:  unit0 = op | A<<12 | G<<8      unit1 = method index
          unit2 = C | D<<4 | E<<8 | F<<12   (G is the 5th register)

Swap unit1/unit2 and every decoded register becomes impossible (a `v14` inside
a 6-register method) while the instruction widths still look fine, so the bug
hides until you hand-decode the raw code units.
"""
import struct, sys

data = open(sys.argv[1], 'rb').read()

def u32(off): return struct.unpack_from('<I', data, off)[0]
def u16(off): return struct.unpack_from('<H', data, off)[0]
def u8(off):  return data[off]

def uleb(off):
    result = 0; shift = 0
    while True:
        b = data[off]; off += 1
        result |= (b & 0x7f) << shift
        if not (b & 0x80): return result, off
        shift += 7

def sleb(off):
    result = 0; shift = 0
    while True:
        b = data[off]; off += 1
        result |= (b & 0x7f) << shift
        shift += 7
        if not (b & 0x80):
            if b & 0x40: result -= (1 << shift)
            return result, off

N_str   = u32(56); O_str   = u32(60)
N_type  = u32(64); O_type  = u32(68)
N_proto = u32(72); O_proto = u32(76)
N_field = u32(80); O_field = u32(84)
N_meth  = u32(88); O_meth  = u32(92)
N_cls   = u32(96); O_cls   = u32(100)

def string(i):
    off = u32(O_str + 4*i)
    n, off = uleb(off)
    end = data.index(b'\x00', off)
    return data[off:end].decode('utf-8', 'replace')

def type_name(i):
    return string(u32(O_type + 4*i))

def proto(i):
    o = O_proto + 12*i
    ret = type_name(u32(o+4)); params_off = u32(o+8)
    params = []
    if params_off:
        n = u32(params_off)
        params = [type_name(u16(params_off+4+2*k)) for k in range(n)]
    return ret, params

def field(i):
    o = O_field + 8*i
    return type_name(u16(o)), string(u32(o+4))

def method(i):
    o = O_meth + 8*i
    ret, params = proto(u16(o+2))
    return type_name(u16(o)), string(u32(o+4)), ret, params

def pretty_type(t):
    m = {'V':'void','Z':'boolean','B':'byte','S':'short','C':'char','I':'int',
         'J':'long','F':'float','D':'double'}
    if t in m: return m[t]
    arr = 0
    while t.startswith('['): arr += 1; t = t[1:]
    base = t[1:-1].replace('/', '.') if t.startswith('L') else m.get(t, t)
    return base + '[]'*arr

def sig(cls, name, ret, params):
    return f"{pretty_type(cls)}.{name}({', '.join(pretty_type(p) for p in params)}) -> {pretty_type(ret)}"

def classes():
    out = {}
    for c in range(N_cls):
        o = O_cls + 32*c
        cn = type_name(u32(o))
        out[cn] = u32(o+24)  # class_data_off
    return out

def class_methods(class_data_off):
    if not class_data_off: return []
    off = class_data_off
    sf, off = uleb(off); inf, off = uleb(off)
    dm, off = uleb(off); vm, off = uleb(off)
    for _ in range(sf): _, off = uleb(off); _, off = uleb(off)
    for _ in range(inf): _, off = uleb(off); _, off = uleb(off)
    res = []
    idx = 0
    for name, count in (('direct', dm), ('virtual', vm)):
        idx = 0
        for _ in range(count):
            diff, off = uleb(off); idx += diff
            access, off = uleb(off)
            code_off, off = uleb(off)
            res.append((idx, code_off, name))
    return res

# ---- instruction widths (dex 039) ----
W2 = set([0x02,0x05,0x08,0x13,0x15,0x16,0x19,0x1a,0x1c,0x1f,0x20,0x22,0x23,0x29,0xfe,0xff])
W3 = set([0x03,0x06,0x09,0x14,0x17,0x1b,0x24,0x25,0x26,0x2a,0x2b,0x2c,0xfc,0xfd])
W4 = set([0xfa,0xfb])

def width(op):
    if op == 0x18: return 5
    if op in W4: return 4
    if op in W3: return 3
    if op in W2: return 2
    if 0x2d <= op <= 0x3d: return 2
    if 0x52 <= op <= 0x6d: return 2
    if 0x6e <= op <= 0x72: return 3
    if 0x74 <= op <= 0x78: return 3
    if 0xd0 <= op <= 0xe2: return 2
    return 1

NAME = {
 0x00:'nop',0x01:'move',0x02:'move/from16',0x03:'move/16',0x04:'move-wide',
 0x07:'move-object',0x0a:'move-result',0x0b:'move-result-wide',0x0c:'move-result-object',
 0x0d:'move-exception',0x0e:'return-void',0x0f:'return',0x10:'return-wide',0x11:'return-object',
 0x12:'const/4',0x13:'const/16',0x14:'const',0x15:'const/high16',0x16:'const-wide/16',
 0x17:'const-wide/32',0x18:'const-wide',0x19:'const-wide/high16',0x1a:'const-string',
 0x1b:'const-string/jumbo',0x1c:'const-class',0x1d:'monitor-enter',0x1e:'monitor-exit',
 0x1f:'check-cast',0x20:'instance-of',0x21:'array-length',0x22:'new-instance',0x23:'new-array',
 0x24:'filled-new-array',0x25:'filled-new-array/range',0x26:'fill-array-data',0x27:'throw',
 0x28:'goto',0x29:'goto/16',0x2a:'goto/32',0x2b:'packed-switch',0x2c:'sparse-switch',
 0x2d:'cmpl-float',0x2e:'cmpg-float',0x2f:'cmpl-double',0x30:'cmpg-double',0x31:'cmp-long',
 0x32:'if-eq',0x33:'if-ne',0x34:'if-lt',0x35:'if-ge',0x36:'if-gt',0x37:'if-le',
 0x38:'if-eqz',0x39:'if-nez',0x3a:'if-ltz',0x3b:'if-gez',0x3c:'if-gtz',0x3d:'if-lez',
 0x52:'iget',0x53:'iget-wide',0x54:'iget-object',0x55:'iget-boolean',0x56:'iget-byte',
 0x57:'iget-char',0x58:'iget-short',0x59:'iput',0x5a:'iput-wide',0x5b:'iput-object',
 0x5c:'iput-boolean',0x5d:'iput-byte',0x5e:'iput-char',0x5f:'iput-short',
 0x60:'sget',0x61:'sget-wide',0x62:'sget-object',0x63:'sget-boolean',0x64:'sget-byte',
 0x65:'sget-char',0x66:'sget-short',0x67:'sput',0x68:'sput-wide',0x69:'sput-object',
 0x6a:'sput-boolean',0x6b:'sput-byte',0x6c:'sput-char',0x6d:'sput-short',
 0x6e:'invoke-virtual',0x6f:'invoke-super',0x70:'invoke-direct',0x71:'invoke-static',
 0x72:'invoke-interface',0x74:'invoke-virtual/range',0x75:'invoke-super/range',
 0x76:'invoke-direct/range',0x77:'invoke-static/range',0x78:'invoke-interface/range',
 0x7b:'neg-int',0x80:'int-to-long',0x81:'int-to-float',0x82:'int-to-double',
 0x8f:'int-to-byte',0x90:'add-int',0x91:'sub-int',0x92:'mul-int',0x93:'div-int',
 0x94:'rem-int',0x95:'and-int',0x96:'or-int',0x97:'xor-int',0x98:'shl-int',
 0x99:'shr-int',0x9a:'ushr-int',0x9b:'add-long',0x9c:'sub-long',0x9d:'mul-long',
 0x9e:'div-long',0x9f:'rem-long',0xa0:'and-long',0xa1:'or-long',0xa2:'xor-long',
 0xa3:'shl-long',0xa4:'shr-long',0xa5:'ushr-long',0xab:'add-int/2addr',0xac:'sub-int/2addr',
 0xad:'mul-int/2addr',0xae:'div-int/2addr',0xaf:'rem-int/2addr',0xb0:'and-int/2addr',
 0xb1:'or-int/2addr',0xb2:'xor-int/2addr',0xb3:'shl-int/2addr',0xb4:'shr-int/2addr',
 0xb5:'ushr-int/2addr',0xd0:'add-int/lit16',0xd1:'rsub-int',0xd2:'mul-int/lit16',
 0xd3:'div-int/lit16',0xd4:'rem-int/lit16',0xd5:'and-int/lit16',0xd6:'or-int/lit16',
 0xd7:'xor-int/lit16',0xd8:'add-int/lit8',0xd9:'rsub-int/lit8',0xda:'mul-int/lit8',
 0xdb:'div-int/lit8',0xdc:'rem-int/lit8',0xdd:'and-int/lit8',0xde:'or-int/lit8',
 0xdf:'xor-int/lit8',0xe0:'shl-int/lit8',0xe1:'shr-int/lit8',0xe2:'ushr-int/lit8',
 0xfa:'invoke-polymorphic',0xfb:'invoke-polymorphic/range',0xfc:'invoke-custom',
 0xfd:'invoke-custom/range',0xfe:'const-method-handle',0xff:'const-method-type',
}

def disasm(code_off):
    regs = u16(code_off); ins = u16(code_off+2); outs = u16(code_off+4)
    tries = u16(code_off+6)
    insns_size = u32(code_off+12)
    base = code_off + 16
    units = [u16(base + 2*i) for i in range(insns_size)]
    pc = 0
    out = []
    out.append(f"    registers={regs} ins={ins} outs={outs} tries={tries} code_units={insns_size}")
    while pc < insns_size:
        u0 = units[pc]; op = u0 & 0xff; hi = u0 >> 8
        w = width(op)
        nm = NAME.get(op, f"op_{op:02x}")
        extra = ''
        if op == 0x1a:
            extra = f'"{string(units[pc+1])}"'
        elif op == 0x1b:
            extra = f'"{string(units[pc+1] | (units[pc+2] << 16))}"'
        elif op == 0x1c:
            extra = f"v{hi}, {pretty_type(type_name(units[pc+1]))}"
        elif op == 0x22:
            extra = f"v{hi}, {pretty_type(type_name(units[pc+1]))}"
        elif op == 0x1f:
            extra = f"v{hi}, {pretty_type(type_name(units[pc+1]))}"
        elif op in (0x20, 0x23):
            extra = f"v{u0>>12}, v{(u0>>8)&0xf}, {pretty_type(type_name(units[pc+1]))}"
        elif 0x52 <= op <= 0x5f:
            fc, fn = field(units[pc+1])
            extra = f"v{hi}, v{(u0>>12)&0xf}, {pretty_type(fc)}.{fn}"
        elif 0x60 <= op <= 0x6d:
            fc, fn = field(units[pc+1])
            extra = f"v{hi}, {pretty_type(fc)}.{fn}"
        elif 0x6e <= op <= 0x72:
            mc, mn, ret, ps = method(units[pc+1])
            a = u0 >> 12
            g = (u0 >> 8) & 0xf
            u2 = units[pc+2]
            cs = [u2 & 0xf, (u2 >> 4) & 0xf, (u2 >> 8) & 0xf, (u2 >> 12) & 0xf, g]
            regs_s = cs[:a]
            extra = f"{{{', '.join('v'+str(r) for r in regs_s)}}}, {sig(mc, mn, ret, ps)}"
        elif 0x74 <= op <= 0x78:
            mc, mn, ret, ps = method(units[pc+1])
            start = units[pc+2]; cnt = u0 >> 8
            extra = f"{{v{start}..v{start+cnt-1}}}, {sig(mc, mn, ret, ps)}"
        elif op in (0x32,0x33,0x34,0x35,0x36,0x37):
            off = struct.unpack('<h', struct.pack('<H', units[pc+1]))[0]
            extra = f"v{(u0>>8)&0xf}, v{u0>>12}, -> {pc+off}"
        elif 0x38 <= op <= 0x3d:
            off = struct.unpack('<h', struct.pack('<H', units[pc+1]))[0]
            extra = f"v{hi}, -> {pc+off}"
        elif op == 0x28:
            off = struct.unpack('<b', struct.pack('<B', hi))[0]
            extra = f"-> {pc+off}"
        elif op == 0x29:
            off = struct.unpack('<h', struct.pack('<H', units[pc+1]))[0]
            extra = f"-> {pc+off}"
        elif op == 0x2a:
            off = struct.unpack('<i', struct.pack('<I', units[pc+1] | (units[pc+2] << 16)))[0]
            extra = f"-> {pc+off}"
        elif op == 0x12:
            extra = f"v{hi>>4}, #{struct.unpack('<b', struct.pack('<B', (hi & 0xf) | ((hi & 8) << 1)))[0]}"
        elif op in (0x13,0x15,0x16,0x19,0xfe,0xff):
            extra = f"v{hi}, #{units[pc+1]}"
        elif op in (0x14,0x17):
            extra = f"v{hi}, #{units[pc+1] | (units[pc+2] << 16)}"
        elif op == 0x0f or op == 0x10 or op == 0x11:
            extra = f"v{hi}"
        elif op == 0x0a or op == 0x0b or op == 0x0c or op == 0x0d or op == 0x21:
            extra = f"v{hi}"
        elif 0xd8 <= op <= 0xe2:
            extra = f"v{hi}, v{(u0>>12)&0xf}, #{struct.unpack('<b', struct.pack('<B', units[pc+1] & 0xff))[0]}"
        elif 0xd0 <= op <= 0xd7:
            extra = f"v{hi}, v{(u0>>12)&0xf}, #{units[pc+1]}"
        elif 0x90 <= op <= 0xaf:
            extra = f"v{hi}, v{(u0>>12)&0xf}, v{(units[pc+1])&0xff}"
        elif op == 0x24 or op == 0x25:
            extra = pretty_type(type_name(units[pc+1]))
        out.append(f"    {pc:5d}: {nm:26} {extra}")
        pc += w
    return '\n'.join(out)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    cls = classes()
    if len(sys.argv) == 2:
        for k in sorted(cls): print(k)
        sys.exit()
    if sys.argv[2] == '--search':
        needle = sys.argv[3].lower() if len(sys.argv) > 3 else ''
        for k in sorted(cls):
            if needle in k.lower(): print(k)
        sys.exit()
    target = sys.argv[2]
    if not target.startswith('L'):
        target = 'L' + target.replace('.', '/') + ';'
    want = sys.argv[3] if len(sys.argv) > 3 else None
    cd = cls.get(target)
    if cd is None:
        print(f"class not found: {target}", file=sys.stderr)
        print("hint: try --search <substring>", file=sys.stderr)
        sys.exit(1)
    for mi, code_off, kind in class_methods(cd):
        mc, mn, ret, ps = method(mi)
        if want and mn != want: continue
        print(f"\n=== {pretty_type(mc)}.{mn}{tuple(pretty_type(p) for p in ps)} [{kind}] code_off={code_off}")
        if code_off: print(disasm(code_off))
        else: print("    (no code)")
