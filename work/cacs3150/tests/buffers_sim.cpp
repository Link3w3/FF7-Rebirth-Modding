// 3.14.3: the pose-buffer choice of the Kawaii runtime (RebirthSkelCompat.cpp, KawaiiRt::Evaluate), replayed against a
// model of USkinnedMeshComponent's two buffers: each frame the engine makes the pose in the editable one, calls the
// hook, flips. Checks that the hook reads the pose of this frame (never its own result) and that the buffer shown after
// the flip holds the result, through the cases: the first frame, double evaluations in a frame, URO interpolation frames
// (no hook), bones left out of the pose at a level of detail, a single buffer.
#include <cmath>
#include <cstdio>
#include <cstring>
#include <vector>
#include <algorithm>

struct Marks
{
    std::vector<int> Bones;
    std::vector<float> Vals;
};

constexpr int N = 12;                 // bones
const std::vector<int> Kawaii = {5, 6, 7, 8, 9};

float MarksHeld(const Marks& m, const std::vector<float>& a)
{
    if (m.Bones.empty()) { return -1.0f; }
    const size_t n = m.Bones.size();
    const size_t step = std::max<size_t>(1, n / 24);
    int tested = 0, held = 0;
    for (size_t k = 0; k < n; k += step)
    {
        ++tested;
        if (std::memcmp(&a[static_cast<size_t>(m.Bones[k]) * 12], m.Vals.data() + k * 12, 48) == 0) { ++held; }
    }
    return tested ? static_cast<float>(held) / static_cast<float>(tested) : -1.0f;
}

struct Engine
{
    std::vector<float> Buf[2];
    int Editable = 0, Read = 1;
    bool Double = true;
    Engine()
    {
        Buf[0].assign(N * 12, 0.0f);
        Buf[1].assign(N * 12, 0.0f);
    }
    void Make(int frame, bool kawaiiRequired)
    {
        auto& b = Buf[Editable];
        for (int i = 0; i < N; ++i)
        {
            const bool kawaii = std::find(Kawaii.begin(), Kawaii.end(), i) != Kawaii.end();
            if (kawaii && !kawaiiRequired) { continue; }
            float* f = &b[static_cast<size_t>(i) * 12];
            std::memset(f, 0, 48);
            f[3] = 1.0f;
            f[4] = static_cast<float>(frame * 1000 + i);   // the frame it was made in
            f[8] = f[9] = f[10] = 1.0f;
        }
    }
    void Flip()
    {
        if (!Double) { return; }
        Read = Editable;
        Editable = 1 - Editable;
    }
};

// the runtime's side (slot 0: the found buffer = the engine's [1]; slot 1: its partner = [0])
struct Runtime
{
    bool Pair = true;
    Marks Written[2];
    std::vector<int> OutBones;
    std::vector<float> OutVals;
    int LastSlot = -1;
    float LastGame = -1.0f;
    int Index = -1;           // learned: the engine's index of the buffer being made (stands for OffIndex)
    int Marked = 0, Guessed = 0, ByIndex = 0, Alternate = 0, Repeats = 0, Same = 0, Unmade = 0;
    int ReadFrameBad = 0, FedBack = 0, BadWhenGuessed = 0;
    bool GuessedNow = false;

    std::vector<float>& SlotBuf(Engine& g, int slot) { return Pair ? g.Buf[slot == 0 ? 1 : 0] : g.Buf[0]; }
    int SlotOfNumber(int number) { return number == 1 ? 0 : 1; }

    void WriteResult(std::vector<float>& b, int slot)
    {
        for (size_t k = 0; k < OutBones.size(); ++k) { std::memcpy(&b[static_cast<size_t>(OutBones[k]) * 12], OutVals.data() + k * 12, 48); }
        Written[slot].Bones = OutBones;
        Written[slot].Vals = OutVals;
    }

    void Hook(Engine& g, float game, int frame, bool learnedIndexAvailable)
    {
        const bool sameTime = game >= 0.0f && LastGame >= 0.0f && game == LastGame;
        GuessedNow = false;
        int use = 0;
        bool both = false;
        if (Pair)
        {
            const float h0 = MarksHeld(Written[0], SlotBuf(g, 0)), h1 = MarksHeld(Written[1], SlotBuf(g, 1));
            const bool known = h0 >= 0.0f && h1 >= 0.0f;
            const bool made0 = h0 >= 0.0f && h0 < 0.5f, made1 = h1 >= 0.0f && h1 < 0.5f;
            if (known && made0 != made1)
            {
                use = made0 ? 0 : 1;
                ++Marked;
            }
            else if (known && !made0 && !made1 && (sameTime || game < 0.0f))
            {
                ++Repeats;
                return;
            }
            else
            {
                const int byIndex = learnedIndexAvailable ? SlotOfNumber(g.Editable) : -1;
                if (byIndex >= 0)
                {
                    use = byIndex;
                    ++ByIndex;
                }
                else if (known && !made0 && !made1 && LastSlot >= 0)
                {
                    use = 1 - LastSlot;
                    ++Alternate;
                }
                else
                {
                    ++Guessed;
                    GuessedNow = true;
                }
                both = true;
            }
        }
        std::vector<float>& buffer = SlotBuf(g, use);
        if (sameTime && !OutBones.empty())
        {
            WriteResult(buffer, use);
            if (both) { WriteResult(SlotBuf(g, 1 - use), 1 - use); }
            ++Same;
            LastSlot = use;
            return;
        }
        std::vector<float> raw = buffer;
        // what was read: the frame each Kawaii bone was made in (restored bones: from the parent, here "this frame")
        for (int b : Kawaii)
        {
            bool restored = false;
            const Marks& m = Written[use];
            for (size_t k = 0; k < m.Bones.size(); ++k)
            {
                if (m.Bones[k] == b && std::memcmp(&raw[static_cast<size_t>(b) * 12], m.Vals.data() + k * 12, 48) == 0)
                {
                    restored = true;
                    ++Unmade;
                }
            }
            if (restored) { continue; }
            const float x = raw[static_cast<size_t>(b) * 12 + 4];
            const float fracPart = x - std::floor(x);
            if (fracPart > 0.25f) { ++FedBack; }   // our own result read as the pose
            else if (static_cast<int>(std::floor(x / 1000.0f)) != frame) { ++(GuessedNow ? BadWhenGuessed : ReadFrameBad); }
        }
        // the parents (bones 0-4) must be of this frame too
        for (int b = 0; b < 5; ++b)
        {
            if (static_cast<int>(std::floor(raw[static_cast<size_t>(b) * 12 + 4] / 1000.0f)) != frame) { ++(GuessedNow ? BadWhenGuessed : ReadFrameBad); }
        }
        LastGame = game;
        // the result: the frame's pose + 0.5 (a mark), on the Kawaii bones
        OutBones.clear();
        OutVals.clear();
        for (int b : Kawaii)
        {
            float out[12]{};
            out[3] = 1.0f;
            out[4] = static_cast<float>(frame * 1000 + b) + 0.5f;
            out[8] = out[9] = out[10] = 1.0f;
            std::memcpy(&raw[static_cast<size_t>(b) * 12], out, 48);
            OutBones.push_back(b);
            OutVals.insert(OutVals.end(), out, out + 12);
        }
        buffer = raw;
        Written[use].Bones = OutBones;
        Written[use].Vals = OutVals;
        if (both) { WriteResult(SlotBuf(g, 1 - use), 1 - use); }
        LastSlot = use;
    }
};

// Shown after the flip: does the read buffer hold this frame's result?
bool Shows(const Engine& g, int frame)
{
    const auto& b = g.Buf[g.Read];
    for (int k : Kawaii)
    {
        if (b[static_cast<size_t>(k) * 12 + 4] != static_cast<float>(frame * 1000 + k) + 0.5f) { return false; }
    }
    return true;
}

int Run(const char* name, bool pair, int frames, int uroEvery, int doubleEvery, int lodFrom, int lodTo, bool learned, bool informational = false)
{
    Engine g;
    g.Double = pair;
    if (!pair) { g.Read = 0; }
    Runtime r;
    r.Pair = pair;
    int shown = 0, hookFrames = 0, interp = 0;
    for (int f = 1; f <= frames; ++f)
    {
        const float game = static_cast<float>(f) / 60.0f;
        const bool interpolate = uroEvery > 0 && (f % uroEvery) == 0;
        const bool kawaiiRequired = !(f >= lodFrom && f <= lodTo);
        if (interpolate)
        {
            g.Make(f, kawaiiRequired);   // (interpolated: no hook)
            g.Flip();
            ++interp;
            continue;
        }
        g.Make(f, kawaiiRequired);
        r.Hook(g, game, f, learned && f > 20);
        if (doubleEvery > 0 && (f % doubleEvery) == 0)
        {
            g.Make(f, kawaiiRequired);   // a second evaluation in the same frame, the same game time
            r.Hook(g, game, f, learned && f > 20);
        }
        g.Flip();
        ++hookFrames;
        if (Shows(g, f) || (!kawaiiRequired && f > lodFrom)) { ++shown; }
    }
    const bool ok = r.FedBack == 0 && r.ReadFrameBad == 0 && shown >= hookFrames - 1;
    if (informational) { std::printf("(informational) "); }
    std::printf("%-44s %s  shown %d/%d (interp %d)  marked %d byIndex %d alternate %d guessed %d repeats %d same %d unmade %d  fedback %d stale-read %d (on guessed frames %d)\n", name,
                ok ? "OK  " : "FAIL", shown, hookFrames, interp, r.Marked, r.ByIndex, r.Alternate, r.Guessed, r.Repeats, r.Same, r.Unmade, r.FedBack, r.ReadFrameBad, r.BadWhenGuessed);
    return (ok || informational) ? 0 : 1;
}

int main()
{
    int bad = 0;
    bad += Run("two buffers", true, 200, 0, 0, -1, -1, false);
    bad += Run("two buffers, learned index", true, 200, 0, 0, -1, -1, true);
    bad += Run("two buffers, 2nd evaluation every 7th frame", true, 200, 0, 7, -1, -1, false);
    bad += Run("two buffers, URO every 3rd frame, no index", true, 200, 3, 0, -1, -1, false, true);
    bad += Run("two buffers, URO every 3rd, learned index", true, 200, 3, 0, -1, -1, true);
    bad += Run("two buffers, Kawaii bones unmade 50-80", true, 200, 0, 0, 50, 80, false);
    bad += Run("one buffer", false, 200, 0, 0, -1, -1, false);
    bad += Run("one buffer, 2nd evaluation every 5th frame", false, 200, 0, 5, -1, -1, false);
    std::printf(bad ? "FAILED: %d\n" : "all passed\n", bad);
    return bad;
}
