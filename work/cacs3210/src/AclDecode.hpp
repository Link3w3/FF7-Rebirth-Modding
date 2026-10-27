// AclDecode.hpp (Create a Character System 3.20.0): FINAL FANTASY VII REBIRTH's animation data (ACL 1.x uniformly
// sampled clips, as UE4's ACL plugin cooks a sequence's CompressedByteStream) decoded into each track's rotation per
// sample: the variable and full-float formats, clip and segment range reduction, default, constant and animated tracks.
// Self-contained (no engine, no allocation outside the result): the game mod decodes the motions of an animation set
// with it (a Kawaii Dynamic Motions node's "pose_animset"); the offline tests check it against the Python decoder.
#pragma once

#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

namespace Acl
{
constexpr uint32_t ClipTag = 0xac10ac10u;
inline constexpr uint8_t BitRateBits[19] = {0, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 32};
constexpr uint8_t RawBitRate = 18;
constexpr uint32_t MaxTracks = 4096;
constexpr uint32_t MaxSamples = 200000;

struct Clip
{
    uint32_t NumTracks = 0;
    uint32_t NumSamples = 0;
    float SampleRate = 30.0f;
    uint16_t Version = 0;
    // each track's rotation (x y z w) a sample: filled for the tracks asked for, empty for the others
    std::vector<std::vector<std::array<float, 4>>> Rotations;
};

namespace Detail
{
template <class T>
bool Get(const uint8_t* d, size_t size, size_t at, T& out)
{
    if (at > size || size - at < sizeof(T)) { return false; }
    std::memcpy(&out, d + at, sizeof(T));
    return true;
}

inline bool BitOf(const std::vector<uint32_t>& words, size_t i) { return ((words[i >> 5] >> (31 - (i & 31))) & 1u) != 0; }

// numBits (0 - 32) at bitOffset of an MSB-first bit stream (ACL packs its values big-endian)
inline bool ReadBits(const uint8_t* d, size_t size, uint64_t bitOffset, int numBits, uint32_t& out)
{
    out = 0;
    if (numBits == 0) { return true; }
    if (numBits < 0 || numBits > 32) { return false; }
    const size_t byte = static_cast<size_t>(bitOffset >> 3);
    const int skip = static_cast<int>(bitOffset & 7);
    const size_t need = static_cast<size_t>((skip + numBits + 7) / 8);
    if (byte > size || size - byte < need) { return false; }
    uint64_t v = 0;
    for (size_t k = 0; k < 8; ++k) { v = (v << 8) | (byte + k < size ? d[byte + k] : 0u); }
    const int shift = 64 - skip - numBits;
    const uint64_t mask = numBits == 32 ? 0xFFFFFFFFull : ((1ull << numBits) - 1ull);
    out = static_cast<uint32_t>((v >> shift) & mask);
    return true;
}

// (3.20.1) a 32-bit value's bytes the other way round (a whole float of a fixed format as it is in memory)
inline uint32_t Swap32(uint32_t v) { return (v >> 24) | ((v >> 8) & 0xFF00u) | ((v << 8) & 0xFF0000u) | (v << 24); }

inline float FloatOfBits(uint32_t bits)
{
    float f = 0.0f;
    std::memcpy(&f, &bits, sizeof(f));
    return f;
}

inline uint16_t BigU16(const uint8_t* p) { return static_cast<uint16_t>((p[0] << 8) | p[1]); }
} // namespace Detail

// Where an ACL clip starts in `data` (its tag 8 bytes in), or SIZE_MAX: the cooked byte stream begins with it.
inline size_t FindClip(const uint8_t* data, size_t size, size_t from = 0)
{
    for (size_t at = from + 8; at + 4 <= size; ++at)
    {
        uint32_t tag = 0;
        std::memcpy(&tag, data + at, sizeof(tag));
        if (tag == ClipTag) { return at - 8; }
    }
    return static_cast<size_t>(-1);
}

// Whether `data` begins with an ACL clip header that fits in `size` bytes.
inline bool LooksLikeClip(const uint8_t* data, size_t size)
{
    uint32_t total = 0, tag = 0;
    return size >= 48 && Detail::Get(data, size, 0, total) && Detail::Get(data, size, 8, tag) && tag == ClipTag && total >= 48 && total <= size;
}

// Decodes the clip at `data` (its first byte: the clip's size field). `want` (one flag a track, or empty: every track):
// the tracks whose rotations are kept. False, with `why`, for data this decoder does not read.
inline bool Decode(const uint8_t* data, size_t size, const std::vector<uint8_t>& want, Clip& out, std::string& why)
{
    using namespace Detail;
    out = Clip{};
    uint32_t total = 0, tag = 0;
    uint16_t version = 0;
    uint8_t algorithm = 0;
    if (!Get(data, size, 0, total) || !Get(data, size, 8, tag) || !Get(data, size, 12, version) || !Get(data, size, 14, algorithm) || tag != ClipTag)
    {
        why = "no ACL clip header";
        return false;
    }
    if (total < 48 || total > size)
    {
        why = "the ACL clip's size does not fit its data";
        return false;
    }
    const size_t limit = total;
    const size_t ch = 16;
    uint16_t numBones = 0, numSegments = 0, segStart = 0, segHeaders = 0, defaultBits = 0, constantBits = 0, constantData = 0, clipRange = 0;
    uint8_t rotFmt = 0, transFmt = 0, scaleFmt = 0, clipRR = 0, segRR = 0, hasScale = 0, defaultScale = 0;
    uint32_t numSamples = 0;
    float sampleRate = 0.0f;
    bool ok = Get(data, limit, ch + 0, numBones) && Get(data, limit, ch + 2, numSegments) && Get(data, limit, ch + 4, rotFmt) &&
              Get(data, limit, ch + 5, transFmt) && Get(data, limit, ch + 6, scaleFmt) && Get(data, limit, ch + 7, clipRR) && Get(data, limit, ch + 8, segRR) &&
              Get(data, limit, ch + 9, hasScale) && Get(data, limit, ch + 10, defaultScale) && Get(data, limit, ch + 12, numSamples) &&
              Get(data, limit, ch + 16, sampleRate) && Get(data, limit, ch + 20, segStart) && Get(data, limit, ch + 22, segHeaders) &&
              Get(data, limit, ch + 24, defaultBits) && Get(data, limit, ch + 26, constantBits) && Get(data, limit, ch + 28, constantData) &&
              Get(data, limit, ch + 30, clipRange);
    if (!ok || numBones == 0 || numBones > MaxTracks || numSamples == 0 || numSamples > MaxSamples || !(sampleRate > 0.0f && sampleRate <= 1000.0f) ||
        numSegments == 0 || numSegments > 4096 || rotFmt > 4 || transFmt > 3 || scaleFmt > 3)
    {
        why = "an ACL clip header out of range";
        return false;
    }
    (void)defaultScale;
    const uint32_t per = hasScale ? 3u : 2u;
    const size_t bits = static_cast<size_t>(numBones) * per;
    const size_t words = (bits + 31) / 32;
    std::vector<uint32_t> defaults(words), constants(words);
    for (size_t w = 0; w < words; ++w)
    {
        if (!Get(data, limit, ch + defaultBits + w * 4, defaults[w]) || !Get(data, limit, ch + constantBits + w * 4, constants[w]))
        {
            why = "an ACL clip's track bit sets out of its data";
            return false;
        }
    }
    // each component of each track: 0 default, 1 constant, 2 animated
    std::vector<uint8_t> kind(bits);
    for (size_t i = 0; i < bits; ++i) { kind[i] = BitOf(defaults, i) ? 0 : (BitOf(constants, i) ? 1 : 2); }
    out.NumTracks = numBones;
    out.NumSamples = numSamples;
    out.SampleRate = sampleRate;
    out.Version = version;
    out.Rotations.assign(numBones, {});
    const auto wanted = [&](size_t b) { return want.empty() || (b < want.size() && want[b] != 0); };
    for (size_t b = 0; b < numBones; ++b)
    {
        if (wanted(b)) { out.Rotations[b].assign(numSamples, std::array<float, 4>{0.0f, 0.0f, 0.0f, 1.0f}); }
    }
    const auto dropW = [](float x, float y, float z) {
        const float s = 1.0f - x * x - y * y - z * z;
        return std::array<float, 4>{x, y, z, s > 0.0f ? std::sqrt(s) : 0.0f};
    };
    // the constant tracks
    size_t p = ch + constantData;
    for (size_t b = 0; b < numBones; ++b)
    {
        for (uint32_t s = 0; s < per; ++s)
        {
            if (kind[b * per + s] != 1) { continue; }
            if (s == 0)
            {
                std::array<float, 4> q{};
                if (rotFmt == 0)
                {
                    for (int c = 0; c < 4; ++c) { ok = ok && Get(data, limit, p + 4 * c, q[c]); }
                    p += 16;
                }
                else
                {
                    float v[3]{};
                    for (int c = 0; c < 3; ++c) { ok = ok && Get(data, limit, p + 4 * c, v[c]); }
                    p += 12;
                    q = dropW(v[0], v[1], v[2]);
                }
                if (ok && wanted(b)) { std::fill(out.Rotations[b].begin(), out.Rotations[b].end(), q); }
            }
            else
            {
                p += 12;
            }
        }
    }
    if (!ok)
    {
        why = "an ACL clip's constant tracks out of its data";
        return false;
    }
    // the clip's range data: per animated component, in track order
    struct Range
    {
        bool Has = false;
        float Min[4]{}, Extent[4]{};
    };
    std::vector<Range> clipRanges(bits);
    p = ch + clipRange;
    for (size_t b = 0; b < numBones; ++b)
    {
        for (uint32_t s = 0; s < per; ++s)
        {
            const size_t i = b * per + s;
            if (kind[i] != 2 || !(clipRR & (1u << s))) { continue; }
            Range& r = clipRanges[i];
            r.Has = true;
            const int n = (s == 0 && rotFmt == 0) ? 4 : 3;
            for (int c = 0; c < n; ++c) { ok = ok && Get(data, limit, p + 4 * c, r.Min[c]) && Get(data, limit, p + 4 * n + 4 * c, r.Extent[c]); }
            p += static_cast<size_t>(8 * n);
        }
    }
    if (!ok)
    {
        why = "an ACL clip's range data out of its data";
        return false;
    }
    std::vector<uint32_t> animated;   // component indices (track * per + component), in order
    for (size_t i = 0; i < bits; ++i)
    {
        if (kind[i] == 2) { animated.push_back(static_cast<uint32_t>(i)); }
    }
    const bool variable[3] = {rotFmt == 4, transFmt == 3, scaleFmt == 3};
    // the segments: their first samples, then a header each
    std::vector<uint32_t> starts;
    if (numSegments > 1 && segStart != 0xFFFF)
    {
        starts.resize(numSegments);
        for (size_t s = 0; s < numSegments; ++s) { ok = ok && Get(data, limit, ch + segStart + 4 * s, starts[s]); }
    }
    else
    {
        starts.assign(1, 0u);
    }
    if (!ok || starts.size() != numSegments)
    {
        why = "an ACL clip's segments do not match its header";
        return false;
    }
    starts.push_back(numSamples);
    std::vector<uint8_t> rates(animated.size());
    std::vector<const uint8_t*> segRanges(animated.size());
    for (size_t g = 0; g < numSegments; ++g)
    {
        uint32_t sampleBits = 0, fmtOff = 0, rangeOff = 0, trackOff = 0;
        const size_t h = ch + segHeaders + 16 * g;
        if (!Get(data, limit, h, sampleBits) || !Get(data, limit, h + 4, fmtOff) || !Get(data, limit, h + 8, rangeOff) || !Get(data, limit, h + 12, trackOff))
        {
            why = "an ACL clip's segment header out of its data";
            return false;
        }
        const uint32_t first = starts[g], end = starts[g + 1];
        if (end < first || end > numSamples)
        {
            why = "an ACL clip's segment out of its samples";
            return false;
        }
        // the variable components' bit rates (a byte each), then their segment ranges (6 bytes each)
        size_t f = ch + fmtOff;
        size_t q = ch + rangeOff;
        for (size_t a = 0; a < animated.size(); ++a)
        {
            const uint32_t s = animated[a] % per;
            rates[a] = 0xFF;
            segRanges[a] = nullptr;
            if (!variable[s]) { continue; }
            if (f >= limit)
            {
                why = "an ACL clip's bit rates out of its data";
                return false;
            }
            rates[a] = data[f++];
            if (rates[a] > RawBitRate)
            {
                why = "an ACL clip's bit rate out of range";
                return false;
            }
        }
        for (size_t a = 0; a < animated.size(); ++a)
        {
            const uint32_t s = animated[a] % per;
            if (!variable[s] || !(segRR & (1u << s))) { continue; }
            if (q + 6 > limit)
            {
                why = "an ACL clip's segment ranges out of its data";
                return false;
            }
            segRanges[a] = data + q;
            q += 6;
        }
        const uint64_t trackBase = static_cast<uint64_t>(ch + trackOff) * 8u;
        for (uint32_t k = 0; k < end - first; ++k)
        {
            uint64_t bit = trackBase + static_cast<uint64_t>(k) * sampleBits;
            for (size_t a = 0; a < animated.size(); ++a)
            {
                const uint32_t i = animated[a];
                const uint32_t b = i / per, s = i % per;
                float v[4] = {0.0f, 0.0f, 0.0f, 0.0f};
                int n = 3;
                bool ranged = true;   // the clip's range applies
                if (variable[s])
                {
                    const uint8_t rate = rates[a];
                    const int nb = BitRateBits[rate];
                    if (rate == 0)
                    {
                        // constant in this segment: its value in the segment's range data (3 x u16)
                        for (int c = 0; c < 3; ++c) { v[c] = segRanges[a] ? static_cast<float>(BigU16(segRanges[a] + 2 * c)) / 65535.0f : 0.0f; }
                    }
                    else if (rate == RawBitRate)
                    {
                        for (int c = 0; c < 3; ++c)
                        {
                            uint32_t raw = 0;
                            ok = ok && ReadBits(data, limit, bit + 32u * static_cast<unsigned>(c), 32, raw);
                            v[c] = FloatOfBits(raw);
                        }
                        bit += 96;
                        ranged = false;
                    }
                    else
                    {
                        const float top = static_cast<float>((1u << nb) - 1u);
                        for (int c = 0; c < 3; ++c)
                        {
                            uint32_t raw = 0;
                            ok = ok && ReadBits(data, limit, bit + static_cast<uint64_t>(nb) * static_cast<unsigned>(c), nb, raw);
                            v[c] = static_cast<float>(raw) / top;
                        }
                        bit += static_cast<uint64_t>(nb) * 3u;
                        if (segRanges[a])
                        {
                            for (int c = 0; c < 3; ++c)
                            {
                                const float mn = static_cast<float>(segRanges[a][c]) / 255.0f;
                                const float ex = static_cast<float>(segRanges[a][3 + c]) / 255.0f;
                                v[c] = v[c] * ex + mn;
                            }
                        }
                    }
                }
                else
                {
                    const uint8_t fmt = s == 0 ? rotFmt : (s == 1 ? transFmt : scaleFmt);
                    if (s == 0 && fmt == 0) { n = 4; }
                    else if ((s == 0 && fmt == 1) || (s != 0 && fmt == 0)) { n = 3; }
                    else
                    {
                        why = "an ACL clip in a fixed packed format this decoder does not read";
                        return false;
                    }
                    // (3.20.1) whole floats as they are in memory (little-endian), each sample of the track on a 4-byte
                    // boundary of the track data (ACL's memcpy of the packed sample: the safety fallback's full rotations)
                    bit = trackBase + ((bit - trackBase + 31u) / 32u) * 32u;
                    for (int c = 0; c < n; ++c)
                    {
                        uint32_t raw = 0;
                        ok = ok && ReadBits(data, limit, bit + 32u * static_cast<unsigned>(c), 32, raw);
                        v[c] = FloatOfBits(Swap32(raw));
                    }
                    bit += 32u * static_cast<unsigned>(n);
                }
                if (!ok)
                {
                    why = "an ACL clip's samples out of its data";
                    return false;
                }
                if (ranged && clipRanges[i].Has)
                {
                    for (int c = 0; c < n; ++c) { v[c] = v[c] * clipRanges[i].Extent[c] + clipRanges[i].Min[c]; }
                }
                if (s == 0 && wanted(b))
                {
                    out.Rotations[b][first + k] = n == 4 ? std::array<float, 4>{v[0], v[1], v[2], v[3]} : dropW(v[0], v[1], v[2]);
                }
            }
        }
    }
    return true;
}
} // namespace Acl
