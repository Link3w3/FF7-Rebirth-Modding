"""Lists or extracts an archive (RAR5, zip, 7z, ...) through the system's libarchive (ctypes; no extra packages).
    unarchive.py list <archive>
    unarchive.py extract <archive> <empty out dir>
Entry paths are kept inside the out dir (absolute paths and '..' are refused)."""
import ctypes
import os
import sys

L = ctypes.CDLL('libarchive.so.13')
L.archive_read_new.restype = ctypes.c_void_p
L.archive_entry_pathname_utf8.restype = ctypes.c_char_p
L.archive_entry_pathname_utf8.argtypes = [ctypes.c_void_p]
L.archive_entry_pathname.restype = ctypes.c_char_p
L.archive_entry_pathname.argtypes = [ctypes.c_void_p]
L.archive_entry_size.restype = ctypes.c_int64
L.archive_entry_size.argtypes = [ctypes.c_void_p]
L.archive_entry_filetype.restype = ctypes.c_uint
L.archive_entry_filetype.argtypes = [ctypes.c_void_p]
L.archive_read_data.restype = ctypes.c_ssize_t
L.archive_read_data.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
L.archive_error_string.restype = ctypes.c_char_p
L.archive_error_string.argtypes = [ctypes.c_void_p]
for f in ('archive_read_support_format_all', 'archive_read_support_filter_all', 'archive_read_free', 'archive_read_data_skip'):
    getattr(L, f).argtypes = [ctypes.c_void_p]
L.archive_read_open_filename.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
L.archive_read_next_header.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
AE_IFDIR = 0o040000


def entries(path, out=None):
    a = L.archive_read_new()
    L.archive_read_support_format_all(a); L.archive_read_support_filter_all(a)
    r = L.archive_read_open_filename(a, path.encode(), 1 << 20)
    assert r == 0, L.archive_error_string(a)
    e = ctypes.c_void_p()
    buf = ctypes.create_string_buffer(1 << 20)
    n = 0
    while True:
        r = L.archive_read_next_header(a, ctypes.byref(e))
        if r == 1:          # ARCHIVE_EOF
            break
        assert r in (0, -20), L.archive_error_string(a)     # OK / WARN
        p = L.archive_entry_pathname_utf8(e) or L.archive_entry_pathname(e)
        name = p.decode('utf-8', 'replace').replace('\\', '/')
        size = L.archive_entry_size(e)
        isdir = L.archive_entry_filetype(e) == AE_IFDIR
        n += 1
        print('%12d %s%s' % (size, name, '/' if isdir and not name.endswith('/') else ''))
        if out is None or isdir:
            L.archive_read_data_skip(a)
            continue
        rel = os.path.normpath(name).lstrip('/')
        assert not rel.startswith('..'), name
        dst = os.path.join(out, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, 'wb') as f:
            while True:
                k = L.archive_read_data(a, buf, len(buf))
                assert k >= 0, L.archive_error_string(a)
                if k == 0:
                    break
                f.write(buf.raw[:k])
    L.archive_read_free(a)
    print(n, 'entries')


if __name__ == '__main__':
    if sys.argv[1] == 'list':
        entries(sys.argv[2])
    else:
        assert not os.listdir(sys.argv[3]), 'out dir must be empty'
        entries(sys.argv[2], sys.argv[3])
