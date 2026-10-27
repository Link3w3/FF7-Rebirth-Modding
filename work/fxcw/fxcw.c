/* fxcw: compile HLSL with Microsoft's d3dcompiler_47.dll (FXC), for running under Wine.
   fxcw <dll> <file.hlsl> <target> <entry> <out.bin|-> [flags1 hex]   prints the compiler messages; exit 0 = compiled */
typedef void *HANDLE;
typedef unsigned long DWORD;
typedef int BOOL;
typedef long HRESULT;
typedef unsigned long long SIZE_T;
__declspec(dllimport) HANDLE GetStdHandle(DWORD);
__declspec(dllimport) BOOL WriteFile(HANDLE, const void *, DWORD, DWORD *, void *);
__declspec(dllimport) HANDLE CreateFileA(const char *, DWORD, DWORD, void *, DWORD, DWORD, HANDLE);
__declspec(dllimport) BOOL ReadFile(HANDLE, void *, DWORD, DWORD *, void *);
__declspec(dllimport) DWORD GetFileSize(HANDLE, DWORD *);
__declspec(dllimport) void *VirtualAlloc(void *, SIZE_T, DWORD, DWORD);
__declspec(dllimport) void *LoadLibraryA(const char *);
__declspec(dllimport) void *GetProcAddress(void *, const char *);
__declspec(dllimport) void ExitProcess(unsigned);
__declspec(dllimport) char *GetCommandLineA(void);
__declspec(dllimport) BOOL CloseHandle(HANDLE);

typedef struct Blob Blob;
typedef struct { void *qi; void *addref; unsigned long (*release)(Blob *); void *(*ptr)(Blob *); SIZE_T (*size)(Blob *); } BlobVtbl;
struct Blob { BlobVtbl *v; };
typedef HRESULT (*D3DDisassembleFn)(const void *, SIZE_T, unsigned, const char *, Blob **);
typedef HRESULT (*D3DCompileFn)(const void *, SIZE_T, const char *, const void *, void *, const char *, const char *, unsigned, unsigned, Blob **, Blob **);

static HANDLE out;
static unsigned slen(const char *s) { unsigned n = 0; while (s[n]) n++; return n; }
static void say(const char *s) { DWORD w; WriteFile(out, s, slen(s), &w, 0); }
static unsigned hex(const char *s) { unsigned v = 0; for (; *s; s++) { char c = *s; v = v * 16 + (c >= '0' && c <= '9' ? c - '0' : c >= 'a' && c <= 'f' ? c - 'a' + 10 : c >= 'A' && c <= 'F' ? c - 'A' + 10 : 0); } return v; }

void start(void)
{
    out = GetStdHandle((DWORD)-11);
    char *cl = GetCommandLineA();
    static char buf[8192];
    char *argv[16];
    int argc = 0;
    unsigned i = 0, j = 0;
    while (cl[i] && argc < 16) {
        while (cl[i] == ' ') i++;
        if (!cl[i]) break;
        argv[argc++] = &buf[j];
        int q = 0;
        while (cl[i] && (q || cl[i] != ' ')) { if (cl[i] == '"') { q = !q; i++; continue; } buf[j++] = cl[i++]; }
        buf[j++] = 0;
    }
    if (argc < 4) { say("usage: fxcw <dll> <file.hlsl> <target> <entry> <out.bin|-> [flags1 hex]  |  fxcw <dll> --disasm <file.dxbc> <out.txt>\n"); ExitProcess(2); }
    void *dll = LoadLibraryA(argv[1]);
    if (!dll) { say("cannot load the compiler dll\n"); ExitProcess(3); }
    if (argv[2][0] == '-' && argv[2][1] == '-' && argv[2][2] == 'l') {
        /* --list <file>: lines "<in.dxbc>|<out.asm>"; disassembles each (hex literals) */
        D3DDisassembleFn dis = (D3DDisassembleFn)GetProcAddress(dll, "D3DDisassemble");
        HANDLE f = CreateFileA(argv[3], 0x80000000u, 1, 0, 3, 0x80, 0);
        if (f == (HANDLE)(long long)-1) { say("cannot open the list\n"); ExitProcess(4); }
        DWORD size = GetFileSize(f, 0), got = 0;
        char *list = (char *)VirtualAlloc(0, size + 2, 0x3000, 4);
        ReadFile(f, list, size, &got, 0);
        CloseHandle(f);
        list[got] = '\n';
        unsigned ok = 0, bad = 0;
        char *p = list, *end = list + got + 1;
        while (p < end) {
            char *line = p;
            while (p < end && *p != '\n') p++;
            char *eol = p;
            p++;
            if (eol > line && eol[-1] == '\r') eol--;
            *eol = 0;
            char *bar = line;
            while (*bar && *bar != '|') bar++;
            if (!*bar) continue;
            *bar = 0;
            HANDLE g = CreateFileA(line, 0x80000000u, 1, 0, 3, 0x80, 0);
            if (g == (HANDLE)(long long)-1) { bad++; continue; }
            DWORD gs = GetFileSize(g, 0), gg = 0;
            char *src = (char *)VirtualAlloc(0, gs + 1, 0x3000, 4);
            ReadFile(g, src, gs, &gg, 0);
            CloseHandle(g);
            Blob *text = 0;
            HRESULT hr = dis(src, gg, 0x80, 0, &text);
            if (hr < 0 || !text) { bad++; continue; }
            HANDLE o = CreateFileA(bar + 1, 0x40000000u, 0, 0, 2, 0x80, 0);
            DWORD w;
            WriteFile(o, text->v->ptr(text), (DWORD)text->v->size(text), &w, 0);
            CloseHandle(o);
            text->v->release(text);
            ok++;
        }
        char msg[64]; unsigned n = 0;
        const char *a = "LIST ok=";
        while (*a) msg[n++] = *a++;
        char digits[16]; int k = 0; unsigned v = ok; do { digits[k++] = '0' + v % 10; v /= 10; } while (v);
        while (k) msg[n++] = digits[--k];
        a = " bad="; while (*a) msg[n++] = *a++;
        v = bad; do { digits[k++] = '0' + v % 10; v /= 10; } while (v);
        while (k) msg[n++] = digits[--k];
        msg[n++] = '\n'; msg[n] = 0;
        say(msg);
        ExitProcess(bad ? 1 : 0);
    }
    if (argv[2][0] == '-' && argv[2][1] == '-' && argv[2][2] == 'd') {
        D3DDisassembleFn dis = (D3DDisassembleFn)GetProcAddress(dll, "D3DDisassemble");
        HANDLE f = CreateFileA(argv[3], 0x80000000u, 1, 0, 3, 0x80, 0);
        if (f == (HANDLE)(long long)-1) { say("cannot open the dxbc\n"); ExitProcess(4); }
        DWORD size = GetFileSize(f, 0), got = 0;
        char *src = (char *)VirtualAlloc(0, size + 1, 0x3000, 4);
        ReadFile(f, src, size, &got, 0);
        CloseHandle(f);
        Blob *text = 0;
        unsigned dflags = argc > 5 ? hex(argv[5]) : 0;
        HRESULT hr = dis(src, got, dflags, 0, &text);
        if (hr < 0 || !text) { say("DISASM FAILED\n"); ExitProcess(1); }
        HANDLE o = CreateFileA(argv[4], 0x40000000u, 0, 0, 2, 0x80, 0);
        DWORD w;
        WriteFile(o, text->v->ptr(text), (DWORD)text->v->size(text), &w, 0);
        CloseHandle(o);
        say("DISASM OK\n");
        ExitProcess(0);
    }
    if (argc < 6) { say("usage\n"); ExitProcess(2); }
    D3DCompileFn compile = (D3DCompileFn)GetProcAddress(dll, "D3DCompile");
    if (!compile) { say("no D3DCompile\n"); ExitProcess(3); }
    HANDLE f = CreateFileA(argv[2], 0x80000000u, 1, 0, 3, 0x80, 0);
    if (f == (HANDLE)(long long)-1) { say("cannot open the source\n"); ExitProcess(4); }
    DWORD size = GetFileSize(f, 0), got = 0;
    char *src = (char *)VirtualAlloc(0, size + 1, 0x3000, 4);
    ReadFile(f, src, size, &got, 0);
    CloseHandle(f);
    unsigned flags = argc > 6 ? hex(argv[6]) : 0;
    Blob *code = 0, *err = 0;
    HRESULT hr = compile(src, got, argv[2], 0, 0, argv[4], argv[3], flags, 0, &code, &err);
    if (err) { DWORD w; WriteFile(out, err->v->ptr(err), (DWORD)err->v->size(err), &w, 0); }
    if (hr < 0 || !code) { say("\nFXC FAILED\n"); ExitProcess(1); }
    if (argv[5][0] != '-') {
        HANDLE o = CreateFileA(argv[5], 0x40000000u, 0, 0, 2, 0x80, 0);
        DWORD w;
        WriteFile(o, code->v->ptr(code), (DWORD)code->v->size(code), &w, 0);
        CloseHandle(o);
    }
    say("\nFXC OK\n");
    ExitProcess(0);
}
