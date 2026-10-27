// hcaenc: raw PCM16 (interleaved) -> HCA, and HCA -> raw PCM16 (to check)
//   hcaenc enc <in.pcm> <out.hca> <rate> <channels> [quality 0-4]
//   hcaenc dec <in.hca> <out.pcm> [keycode]
#include "hca/hca_codec.hpp"
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>
using namespace cricodecs;
static std::vector<uint8_t> slurp(const char* p) {
    std::ifstream f(p, std::ios::binary);
    return std::vector<uint8_t>((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
}
int main(int argc, char** argv) {
    if (argc < 4) { std::fprintf(stderr, "usage\n"); return 2; }
    std::string mode = argv[1];
    auto in = slurp(argv[2]);
    if (mode == "enc") {
        hca::HcaEncodeConfig c;
        c.sample_rate = (uint32_t)std::atoi(argv[4]);
        c.channel_count = (uint8_t)std::atoi(argv[5]);
        if (argc > 6) c.quality = (hca::HcaQuality)std::atoi(argv[6]);
        std::vector<int16_t> pcm(in.size() / 2);
        std::memcpy(pcm.data(), in.data(), pcm.size() * 2);
        auto r = hca::encode(std::span<const int16_t>(pcm), c);
        if (!r) { std::fprintf(stderr, "encode: %s\n", r.error().c_str()); return 1; }
        std::ofstream o(argv[3], std::ios::binary);
        o.write((const char*)r->data(), r->size());
        return 0;
    }
    uint64_t key = argc > 4 ? std::strtoull(argv[4], nullptr, 0) : 0;
    auto r = hca::decode(std::span<const uint8_t>(in), key, 0);
    if (!r) { std::fprintf(stderr, "decode: %s\n", r.error().c_str()); return 1; }
    std::ofstream o(argv[3], std::ios::binary);
    o.write((const char*)r->data(), r->size() * 2);
    return 0;
}
