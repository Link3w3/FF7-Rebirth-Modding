// hca_cli <in.wav> <out.hca> [kbps per channel]: encodes a WAV with SoundBankCore's HCA encoder.
#include "../core/SoundBankCore.hpp"
#include <cstdio>
#include <fstream>
#include <iterator>
int main(int argc, char** argv)
{
    if (argc < 3) { std::fprintf(stderr, "usage: hca_cli in.wav out.hca [kbps]\n"); return 2; }
    std::ifstream f(argv[1], std::ios::binary);
    std::vector<uint8_t> data((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
    CacsSound::Pcm pcm;
    std::string error;
    if (!CacsSound::ReadWav(data.data(), data.size(), pcm, error)) { std::fprintf(stderr, "%s\n", error.c_str()); return 1; }
    const double kbps = argc > 3 ? std::atof(argv[3]) : 85.25;
    const int frameBytes = CacsSound::Hca::FrameBytesFor(pcm.Rate, pcm.Channels, kbps);
    CacsSound::Hca::Encoder enc;
    CacsSound::Hca::Info info;
    CacsSound::Bytes out = enc.Encode(pcm, frameBytes, &info, &error);
    if (out.empty()) { std::fprintf(stderr, "%s\n", error.c_str()); return 1; }
    std::ofstream o(argv[2], std::ios::binary);
    o.write(reinterpret_cast<const char*>(out.data()), static_cast<std::streamsize>(out.size()));
    std::printf("%d ch %d Hz, %zu samples, %d frames of %d bytes, delay %d padding %d, mean noise %.1f\n", info.Channels, info.Rate, info.Samples, info.Frames,
                info.FrameBytes, info.Delay, info.Padding, info.MeanNoise);
    return 0;
}
