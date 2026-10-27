CRC32_POLY = 0x04c11db7
TABLE_DEP = []
for i in range(256):
    c = i << 24
    for j in range(8):
        c = ((c << 1) ^ CRC32_POLY) if (c & 0x80000000) else (c << 1)
        c &= 0xffffffff
    TABLE_DEP.append(c)
# standard reflected crc32 table (zlib)
TABLE_REF = []
for i in range(256):
    c = i
    for j in range(8):
        c = (c >> 1) ^ 0xEDB88320 if c & 1 else c >> 1
    TABLE_REF.append(c)
def strihash_dep_wide(s):
    h = 0
    for ch in s:
        v = ord(ch.upper()) if ch.isascii() else ord(ch)
        b1 = v & 0xff
        h = ((h >> 8) & 0x00FFFFFF) ^ TABLE_DEP[(h ^ b1) & 0xff]
        b2 = (v >> 8) & 0xff
        h = ((h >> 8) & 0x00FFFFFF) ^ TABLE_DEP[(h ^ b2) & 0xff]
    return h
def strihash_dep_ansi(s):
    h = 0
    for ch in s:
        v = ord(ch.upper())
        h = ((h >> 8) & 0x00FFFFFF) ^ TABLE_DEP[(h ^ v) & 0xff]
    return h
def memcrc32(b, crc=0):
    crc = ~crc & 0xffffffff
    for x in b:
        crc = (crc >> 8) ^ TABLE_REF[(crc ^ x) & 0xff]
    return ~crc & 0xffffffff
def strcrc32_wide(s, crc=0):
    # 4.26 FCrc::StrCrc32: processes each char as 4 bytes (TCHAR zero-extended to 32 bits)
    crc = ~crc & 0xffffffff
    for ch in s:
        c = ord(ch)
        for k in range(4):
            crc = (crc >> 8) ^ TABLE_REF[(crc ^ (c & 0xff)) & 0xff]; c >>= 8
    return ~crc & 0xffffffff
