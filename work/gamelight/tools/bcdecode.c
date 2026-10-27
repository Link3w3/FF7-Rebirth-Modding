// bcdecode <format> <width> <height> <in.raw> <out.raw>
// format: bc6h (float RGB out, 12 bytes/px), bc6hs (signed), bc7 / bc1 / bc3 / bc5 / bc4 (RGBA8 out, 4 bytes/px)
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define BCDEC_IMPLEMENTATION
#include "../bcdec/bcdec.h"
int main(int argc, char** argv) {
    if (argc != 6) { fprintf(stderr, "usage\n"); return 2; }
    const char* fmt = argv[1]; int w = atoi(argv[2]), h = atoi(argv[3]);
    FILE* f = fopen(argv[4], "rb"); if (!f) return 3;
    fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET);
    unsigned char* in = malloc(n); if (fread(in, 1, n, f) != (size_t)n) return 4; fclose(f);
    int bw = (w + 3) / 4, bh = (h + 3) / 4;
    int isf = !strncmp(fmt, "bc6h", 4);
    int bpp = isf ? 12 : 4;
    int blk = (!strcmp(fmt, "bc1") || !strcmp(fmt, "bc4")) ? 8 : 16;
    if ((long)bw * bh * blk > n) { fprintf(stderr, "short input %ld < %ld\n", n, (long)bw * bh * blk); return 5; }
    int pw = bw * 4, ph = bh * 4;
    unsigned char* out = calloc((size_t)pw * ph, bpp);
    for (int by = 0; by < bh; by++) for (int bx = 0; bx < bw; bx++) {
        const unsigned char* b = in + ((size_t)by * bw + bx) * blk;
        unsigned char* dst = out + ((size_t)by * 4 * pw + bx * 4) * bpp;
        if (isf) bcdec_bc6h_float(b, dst, pw * 3, !strcmp(fmt, "bc6hs"));
        else if (!strcmp(fmt, "bc7")) bcdec_bc7(b, dst, pw * 4);
        else if (!strcmp(fmt, "bc1")) bcdec_bc1(b, dst, pw * 4);
        else if (!strcmp(fmt, "bc3")) bcdec_bc3(b, dst, pw * 4);
        else if (!strcmp(fmt, "bc5")) { unsigned char t[32]; bcdec_bc5(b, t, 8); for (int y = 0; y < 4; y++) for (int x = 0; x < 4; x++) { unsigned char* p = dst + ((size_t)y * pw + x) * 4; p[0] = t[y*8+x*2]; p[1] = t[y*8+x*2+1]; p[2] = 0; p[3] = 255; } }
        else if (!strcmp(fmt, "bc4")) { unsigned char t[16]; bcdec_bc4(b, t, 4); for (int y = 0; y < 4; y++) for (int x = 0; x < 4; x++) { unsigned char* p = dst + ((size_t)y * pw + x) * 4; p[0] = p[1] = p[2] = t[y*4+x]; p[3] = 255; } }
        else { fprintf(stderr, "format?\n"); return 6; }
    }
    FILE* o = fopen(argv[5], "wb");
    for (int y = 0; y < h; y++) fwrite(out + (size_t)y * pw * bpp, bpp, w, o);
    fclose(o);
    return 0;
}
