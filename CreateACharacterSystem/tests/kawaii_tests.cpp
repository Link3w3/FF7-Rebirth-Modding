// Off-target tests for KawaiiSolver.hpp and the core's "kawaii" config (g++ -std=c++20).
#include "../src/KawaiiSolver.hpp"

#include <cstdio>
#include <cstdlib>
#include <string>

using namespace Kawaii;

static int Failures = 0;
#define CHECK(cond)                                                                                  \
    do                                                                                               \
    {                                                                                                \
        if (!(cond)) { std::printf("FAIL %s:%d  %s\n", __FILE__, __LINE__, #cond); ++Failures; }    \
    } while (0)

static bool Near(float a, float b, float tolerance) { return std::fabs(a - b) <= tolerance; }
static bool NearV(V3 a, V3 b, float tolerance) { return Size(a - b) <= tolerance; }

// A model: "Root" at the origin, "Spine" above it, a hanging chain "Hair1".."HairN" from the spine (10 cm each, down -Z),
// and "Tip" under the last hair bone (excluded in some tests); every bone's rotation the identity.
struct Model
{
    Skeleton Skel;
    std::vector<Xf> Ref;   // component space

    explicit Model(int hairs = 5, float length = 10.0f)
    {
        Add(L"Root", -1, {0, 0, 0});
        Add(L"Spine", 0, {0, 0, 100});
        int parent = 1;
        for (int i = 1; i <= hairs; ++i)
        {
            Add(L"Hair" + std::to_wstring(i), parent, {0, 0, 100 - length * static_cast<float>(i)});
            parent = static_cast<int>(Skel.Names.size()) - 1;
        }
        Add(L"Tip", parent, {0, 0, 100 - length * static_cast<float>(hairs) - 2.0f});
    }
    void Add(const std::wstring& name, int parent, V3 at)
    {
        Skel.Names.push_back(name);
        Skel.Parents.push_back(parent);
        Xf x;
        x.T = at;
        Ref.push_back(x);
        Skel.RefLength.push_back(parent >= 0 ? Size(at - Ref[static_cast<size_t>(parent)].T) : 0.0f);
    }
    int Bone(const wchar_t* name) const { return Skel.Find(name); }
};

static SkelCompat::KawaiiNode HairNode()
{
    SkelCompat::KawaiiNode n;
    n.Name = L"hair";
    n.RootBone = L"Hair1";
    return n;
}

// Every bone's distance to its parent in `pose` as in the model's reference.
static bool LengthsKept(const Model& m, const std::vector<Xf>& pose, float tolerance = 0.05f)
{
    for (int b = 1; b < m.Skel.Count(); ++b)
    {
        const int p = m.Skel.Parents[static_cast<size_t>(b)];
        const float want = Size(m.Ref[static_cast<size_t>(b)].T - m.Ref[static_cast<size_t>(p)].T);
        const float got = Size(pose[static_cast<size_t>(b)].T - pose[static_cast<size_t>(p)].T);
        if (!Near(want, got, tolerance))
        {
            std::printf("  bone %d length %.4f, want %.4f\n", b, got, want);
            return false;
        }
    }
    return true;
}

static void TestMath()
{
    const Q4 q = FromRotator(0, 90, 0);   // yaw 90: X -> Y
    CHECK(NearV(Rotate(q, {1, 0, 0}), {0, 1, 0}, 1e-5f));
    CHECK(NearV(Unrotate(q, Rotate(q, {1, 2, 3})), {1, 2, 3}, 1e-5f));
    const Q4 p = FromRotator(90, 0, 0);   // pitch 90: X -> Z
    CHECK(NearV(Rotate(p, {1, 0, 0}), {0, 0, 1}, 1e-5f));
    const Q4 r = FromRotator(0, 0, 90);   // roll 90 (UE's): Y -> -Z
    CHECK(NearV(Rotate(r, {0, 1, 0}), {0, 0, -1}, 1e-5f));
    const Q4 between = FindBetweenVectors({1, 0, 0}, {0, 0, 2});
    CHECK(NearV(Rotate(between, {1, 0, 0}), {0, 0, 1}, 1e-5f));
    const Q4 opposite = FindBetweenVectors({1, 0, 0}, {-1, 0, 0});
    CHECK(NearV(Rotate(opposite, {1, 0, 0}), {-1, 0, 0}, 1e-4f));
    // transforms: a * b applies a then b; Relative undoes Multiply
    Xf a{FromRotator(10, 20, 30), {1, 2, 3}, {1, 1, 1}};
    Xf b{FromRotator(-5, 40, 0), {10, -4, 7}, {2, 2, 2}};
    const Xf ab = Multiply(a, b);
    CHECK(NearV(TransformPosition(ab, {3, 4, 5}), TransformPosition(b, TransformPosition(a, {3, 4, 5})), 1e-3f));
    const Xf back = Relative(ab, b);
    CHECK(NearV(back.T, a.T, 1e-3f) && NearV(TransformPosition(back, {1, 1, 1}), TransformPosition(a, {1, 1, 1}), 1e-3f));
    CHECK(NearV(InverseTransformPosition(b, TransformPosition(b, {5, 6, 7})), {5, 6, 7}, 1e-4f));
    CHECK(NearV(TransformPosition(InverseOf(b), TransformPosition(b, {5, 6, 7})), {5, 6, 7}, 1e-4f));
    CHECK(NearV(RotateAngleAxis({1, 0, 0}, 90, {0, 0, 1}), {0, 1, 0}, 1e-5f));
    const Q4 half = Slerp(Q4{}, FromRotator(0, 90, 0), 0.5f);
    CHECK(Near(RadiansToDegrees(Angle(half)), 45.0f, 1e-3f));
    // curves
    SkelCompat::KawaiiCurve c;
    CHECK(c.Eval(0.5f) == 1.0f);
    c.Keys = {{0.0f, 1.0f}, {1.0f, 0.0f}};
    CHECK(Near(c.Eval(0.25f), 0.75f, 1e-6f) && c.Eval(-1.0f) == 1.0f && c.Eval(2.0f) == 0.0f);
}

// No motion, no forces: the bones stay where the animation puts them.
static void TestAtRest()
{
    Model m;
    SkelCompat::KawaiiNode cfg = HairNode();
    Chain chain({cfg});
    std::vector<uint8_t> changed;
    std::vector<Xf> pose;
    for (int f = 0; f < 120; ++f)
    {
        pose = m.Ref;
        CHECK(chain.Evaluate(m.Skel, pose, changed, Xf{}, 1.0f / 60.0f, nullptr) == 1);
    }
    for (int b = 0; b < m.Skel.Count(); ++b) { CHECK(NearV(pose[static_cast<size_t>(b)].T, m.Ref[static_cast<size_t>(b)].T, 1e-3f)); }
    CHECK(changed[static_cast<size_t>(m.Bone(L"Hair1"))] && changed[static_cast<size_t>(m.Bone(L"Tip"))] && !changed[static_cast<size_t>(m.Bone(L"Spine"))]);
}

// The character runs +X: the hair trails behind (-X), keeps its lengths, and settles back once it stops.
static void TestInertia()
{
    Model m;
    SkelCompat::KawaiiNode cfg = HairNode();
    cfg.WorldDampingLocation = 0.0f;
    Chain chain({cfg});
    std::vector<uint8_t> changed;
    std::vector<Xf> pose;
    Xf component;
    float minX = 0.0f;
    for (int f = 0; f < 60; ++f)
    {
        component.T.X += 600.0f / 60.0f;   // 6 m/s
        pose = m.Ref;
        chain.Evaluate(m.Skel, pose, changed, component, 1.0f / 60.0f, nullptr);
        CHECK(LengthsKept(m, pose));
        minX = std::min(minX, pose[static_cast<size_t>(m.Bone(L"Hair5"))].T.X);
    }
    CHECK(minX < -5.0f);   // (behind the spine, in the mesh's space)
    CHECK(pose[static_cast<size_t>(m.Bone(L"Hair1"))].T.X > pose[static_cast<size_t>(m.Bone(L"Hair5"))].T.X);
    for (int f = 0; f < 600; ++f)
    {
        pose = m.Ref;
        chain.Evaluate(m.Skel, pose, changed, component, 1.0f / 60.0f, nullptr);
    }
    CHECK(NearV(pose[static_cast<size_t>(m.Bone(L"Hair5"))].T, m.Ref[static_cast<size_t>(m.Bone(L"Hair5"))].T, 0.5f));
}

// A move longer than the teleport threshold in one frame is not felt.
static void TestTeleport()
{
    Model m;
    SkelCompat::KawaiiNode cfg = HairNode();
    cfg.WorldDampingLocation = 0.0f;
    Chain chain({cfg});
    std::vector<uint8_t> changed;
    std::vector<Xf> pose = m.Ref;
    Xf component;
    chain.Evaluate(m.Skel, pose, changed, component, 1.0f / 60.0f, nullptr);
    component.T.X += 5000.0f;
    for (int f = 0; f < 5; ++f)
    {
        pose = m.Ref;
        chain.Evaluate(m.Skel, pose, changed, component, 1.0f / 60.0f, nullptr);
    }
    CHECK(NearV(pose[static_cast<size_t>(m.Bone(L"Hair5"))].T, m.Ref[static_cast<size_t>(m.Bone(L"Hair5"))].T, 0.01f));
}

// Gravity pulls a chain that the animation holds out sideways; the stiffness holds it partly.
static void TestGravity()
{
    Model m;
    // the hair held out along +X instead of hanging
    for (int i = 1; i <= 5; ++i) { m.Ref[static_cast<size_t>(m.Bone((L"Hair" + std::to_wstring(i)).c_str()))].T = {10.0f * static_cast<float>(i), 0, 100}; }
    m.Ref[static_cast<size_t>(m.Bone(L"Tip"))].T = {52, 0, 100};
    for (int b = 1; b < m.Skel.Count(); ++b) { m.Skel.RefLength[static_cast<size_t>(b)] = Size(m.Ref[static_cast<size_t>(b)].T - m.Ref[static_cast<size_t>(m.Skel.Parents[static_cast<size_t>(b)])].T); }
    SkelCompat::KawaiiNode cfg = HairNode();
    cfg.Gravity[2] = -980.0f;
    Chain chain({cfg});
    std::vector<uint8_t> changed;
    std::vector<Xf> pose;
    for (int f = 0; f < 240; ++f)
    {
        pose = m.Ref;
        chain.Evaluate(m.Skel, pose, changed, Xf{}, 1.0f / 60.0f, nullptr);
    }
    CHECK(LengthsKept(m, pose));
    CHECK(pose[static_cast<size_t>(m.Bone(L"Hair5"))].T.Z < 90.0f);
    CHECK(pose[static_cast<size_t>(m.Bone(L"Hair5"))].T.Z < pose[static_cast<size_t>(m.Bone(L"Hair2"))].T.Z);
    // the hair bones turned toward their simulated children (rotations changed), the excluded-free tip carried along
    CHECK(Angle(pose[static_cast<size_t>(m.Bone(L"Hair2"))].R) > 0.01f);
}

// A sphere where the hair hangs: the bones stay out of it (by its radius plus theirs).
static void TestSphere()
{
    Model m;
    SkelCompat::KawaiiNode cfg = HairNode();
    SkelCompat::KawaiiLimit s;
    s.Bone = L"Spine";
    s.Offset[0] = 4.0f;          // just in front of the hair, in the spine's space
    s.Offset[2] = -30.0f;
    s.Radius = 8.0f;
    cfg.Spheres.push_back(s);
    Chain chain({cfg});
    std::vector<uint8_t> changed;
    std::vector<Xf> pose;
    for (int f = 0; f < 120; ++f)
    {
        pose = m.Ref;
        chain.Evaluate(m.Skel, pose, changed, Xf{}, 1.0f / 60.0f, nullptr);
    }
    const V3 center{4, 0, 70};
    for (int i = 2; i <= 5; ++i)
    {
        const float d = Size(pose[static_cast<size_t>(m.Bone((L"Hair" + std::to_wstring(i)).c_str()))].T - center);
        CHECK(d >= 8.0f + 3.0f - 1.0f);   // (the length restore runs after the collision: close to, not exactly, outside)
    }
    CHECK(LengthsKept(m, pose));
}

// A capsule, a tapered capsule, a box and a floor plane push the bones out the same way.
static void TestShapes()
{
    for (int kind = 0; kind < 4; ++kind)
    {
        Model m;
        SkelCompat::KawaiiNode cfg = HairNode();
        cfg.Gravity[2] = -980.0f;
        SkelCompat::KawaiiLimit l;
        l.Bone = L"Spine";
        if (kind == 0)
        {
            l.Offset[0] = 3.0f;
            l.Offset[2] = -40.0f;
            l.Radius = 5.0f;
            l.Length = 20.0f;
            cfg.Capsules.push_back(l);
        }
        else if (kind == 1)
        {
            l.Offset[0] = 3.0f;
            l.Offset[2] = -40.0f;
            l.Radius0 = 6.0f;
            l.Radius1 = 3.0f;
            l.Length = 20.0f;
            cfg.TaperedCapsules.push_back(l);
        }
        else if (kind == 2)
        {
            l.Offset[0] = 6.0f;
            l.Offset[2] = -40.0f;
            l.Extent[0] = 5.0f;
            l.Extent[1] = 5.0f;
            l.Extent[2] = 10.0f;
            cfg.Boxes.push_back(l);
        }
        else
        {
            // the hair held out level along +X droops under gravity onto a floor at z = 90 (the component's space)
            for (int i = 1; i <= 5; ++i) { m.Ref[static_cast<size_t>(m.Bone((L"Hair" + std::to_wstring(i)).c_str()))].T = {10.0f * static_cast<float>(i), 0, 100}; }
            m.Ref[static_cast<size_t>(m.Bone(L"Tip"))].T = {52, 0, 100};
            for (int b = 1; b < m.Skel.Count(); ++b)
            {
                m.Skel.RefLength[static_cast<size_t>(b)] = Size(m.Ref[static_cast<size_t>(b)].T - m.Ref[static_cast<size_t>(m.Skel.Parents[static_cast<size_t>(b)])].T);
            }
            l.Bone.clear();
            l.Offset[2] = 90.0f;
            cfg.Planes.push_back(l);
        }
        Chain chain({cfg});
        std::vector<uint8_t> changed;
        std::vector<Xf> pose;
        for (int f = 0; f < 120; ++f)
        {
            pose = m.Ref;
            chain.Evaluate(m.Skel, pose, changed, Xf{}, 1.0f / 60.0f, nullptr);
        }
        CHECK(LengthsKept(m, pose));
        if (kind == 3)
        {
            // (without the floor it droops below z = 90: TestGravity)
            for (int i = 2; i <= 5; ++i) { CHECK(pose[static_cast<size_t>(m.Bone((L"Hair" + std::to_wstring(i)).c_str()))].T.Z >= 90.0f + 3.0f - 0.5f); }
        }
        else
        {
            // pushed away from the shape (it sits on +X): the hair moved toward -X
            CHECK(pose[static_cast<size_t>(m.Bone(L"Hair5"))].T.X < -0.5f);
        }
    }
}

// Exclude bones keep their local transform under their parent (carried, not simulated); skipped bones (another physics')
// leave the chain from them down.
static void TestExcludeAndSkip()
{
    Model m;
    SkelCompat::KawaiiNode cfg = HairNode();
    cfg.ExcludeBones = {L"Tip"};
    cfg.WorldDampingLocation = 0.0f;
    Chain chain({cfg});
    std::vector<uint8_t> changed;
    std::vector<Xf> pose;
    Xf component;
    for (int f = 0; f < 30; ++f)
    {
        component.T.X += 10.0f;
        pose = m.Ref;
        chain.Evaluate(m.Skel, pose, changed, component, 1.0f / 60.0f, nullptr);
    }
    const Xf local = Relative(m.Ref[static_cast<size_t>(m.Bone(L"Tip"))], m.Ref[static_cast<size_t>(m.Bone(L"Hair5"))]);
    const Xf want = Multiply(local, pose[static_cast<size_t>(m.Bone(L"Hair5"))]);
    CHECK(NearV(pose[static_cast<size_t>(m.Bone(L"Tip"))].T, want.T, 1e-3f));
    CHECK(changed[static_cast<size_t>(m.Bone(L"Tip"))]);
    // skip from Hair3 down: Hair3.. are not moved by this node (only carried under Hair2)
    Chain other({cfg});
    std::vector<uint8_t> skip(static_cast<size_t>(m.Skel.Count()), 0);
    skip[static_cast<size_t>(m.Bone(L"Hair3"))] = 1;
    component = Xf{};
    for (int f = 0; f < 30; ++f)
    {
        component.T.X += 10.0f;
        pose = m.Ref;
        other.Evaluate(m.Skel, pose, changed, component, 1.0f / 60.0f, &skip);
    }
    const Xf local3 = Relative(m.Ref[static_cast<size_t>(m.Bone(L"Hair3"))], m.Ref[static_cast<size_t>(m.Bone(L"Hair2"))]);
    CHECK(NearV(pose[static_cast<size_t>(m.Bone(L"Hair3"))].T, Multiply(local3, pose[static_cast<size_t>(m.Bone(L"Hair2"))]).T, 1e-3f));
    // (carried, the bones from Hair3 down stay in line with Hair2 as in the pose: the chain bends above Hair3 only)
    const auto bendAt3 = [&](const std::vector<Xf>& p) {
        const V3 a = SafeNormal(p[static_cast<size_t>(m.Bone(L"Hair3"))].T - p[static_cast<size_t>(m.Bone(L"Hair2"))].T);
        const V3 b = SafeNormal(p[static_cast<size_t>(m.Bone(L"Hair4"))].T - p[static_cast<size_t>(m.Bone(L"Hair3"))].T);
        return 1.0f - Dot(a, b);
    };
    CHECK(bendAt3(pose) < 1e-4f);
    // "skip_bonamik_bones": false: the node keeps them (the chain bends at Hair3 too)
    SkelCompat::KawaiiNode keep = cfg;
    keep.SkipBonamikBones = false;
    Chain kept({keep});
    component = Xf{};
    float bend = 0.0f;
    for (int f = 0; f < 30; ++f)
    {
        component.T.X += 10.0f;
        pose = m.Ref;
        kept.Evaluate(m.Skel, pose, changed, component, 1.0f / 60.0f, &skip);
        bend = std::max(bend, bendAt3(pose));
    }
    CHECK(bend > 1e-3f);
}

// Two strands held side by side by bone constraints keep their distance as one is pushed.
static void TestBoneConstraints()
{
    Model m(4);
    // a second strand, 6 cm to the side (+Y)
    int parent = m.Bone(L"Spine");
    for (int i = 1; i <= 4; ++i)
    {
        m.Add(L"Strand" + std::to_wstring(i), parent, {0, 6, 100 - 10.0f * static_cast<float>(i)});
        parent = m.Skel.Count() - 1;
    }
    SkelCompat::KawaiiNode cfg = HairNode();
    cfg.AdditionalRootBones.push_back({L"Strand1", false, {}});
    cfg.ExcludeBones = {L"Tip"};
    for (int i = 2; i <= 4; ++i) { cfg.BoneConstraints.push_back({L"Hair" + std::to_wstring(i), L"Strand" + std::to_wstring(i), false, SkelCompat::KawaiiCompliance::Leather, false}); }
    cfg.BoneConstraintIterationsBeforeCollision = 4;
    cfg.BoneConstraintIterationsAfterCollision = 4;
    SkelCompat::KawaiiLimit s;   // a sphere pushing only the first strand
    s.Bone = L"Spine";
    s.Offset[1] = -6.0f;
    s.Offset[2] = -30.0f;
    s.Radius = 7.0f;
    cfg.Spheres.push_back(s);
    Chain chain({cfg});
    std::vector<uint8_t> changed;
    std::vector<Xf> pose;
    for (int f = 0; f < 120; ++f)
    {
        pose = m.Ref;
        chain.Evaluate(m.Skel, pose, changed, Xf{}, 1.0f / 60.0f, nullptr);
    }
    CHECK(chain.Nodes[0].MergedConstraints() == 3);
    const float d = Size(pose[static_cast<size_t>(m.Bone(L"Hair3"))].T - pose[static_cast<size_t>(m.Bone(L"Strand3"))].T);
    CHECK(Near(d, 6.0f, 1.5f));
    CHECK(changed[static_cast<size_t>(m.Bone(L"Strand4"))]);
}

// Subdivision: points between the bones (collision only by default), their own constraints, a dummy bone past the tips.
static void TestSubdivision()
{
    Model m;
    SkelCompat::KawaiiNode cfg = HairNode();
    cfg.ExcludeBones = {L"Tip"};
    cfg.BoneSubdivisionCount = 2;
    cfg.DummyBoneLength = 5.0f;
    Chain chain({cfg});
    std::vector<uint8_t> changed;
    std::vector<Xf> pose = m.Ref;
    chain.Evaluate(m.Skel, pose, changed, Xf{}, 1.0f / 60.0f, nullptr);
    // 5 real bones, 2 points in each of the 4 gaps, a tip dummy with its own 2 points
    CHECK(chain.Nodes[0].SimulatedBones() == 5 + 4 * 2 + 1 + 2);
    Xf component;
    for (int f = 0; f < 60; ++f)
    {
        component.T.X += 8.0f;
        pose = m.Ref;
        chain.Evaluate(m.Skel, pose, changed, component, 1.0f / 60.0f, nullptr);
        CHECK(LengthsKept(m, pose, 0.1f) || f < 0);
    }
    // the last real bone turned toward its dummy bone (it trails)
    CHECK(Angle(pose[static_cast<size_t>(m.Bone(L"Hair5"))].R) > 0.001f);
    // the same with simulated points
    cfg.BoneSubdivisionCollisionOnly = false;
    Chain simulated({cfg});
    component = Xf{};
    for (int f = 0; f < 60; ++f)
    {
        component.T.X += 8.0f;
        pose = m.Ref;
        simulated.Evaluate(m.Skel, pose, changed, component, 1.0f / 60.0f, nullptr);
    }
    CHECK(pose[static_cast<size_t>(m.Bone(L"Hair5"))].T.X < -0.5f);
}

// World space: the bones lag behind the mesh's moves without any world damping settings.
static void TestWorldAndBaseSpace()
{
    for (int space = 0; space < 2; ++space)
    {
        Model m;
        SkelCompat::KawaiiNode cfg = HairNode();
        if (space == 0) { cfg.SimulationSpace = SkelCompat::KawaiiSpace::World; }
        else
        {
            cfg.SimulationSpace = SkelCompat::KawaiiSpace::BaseBone;
            cfg.SimulationBaseBone = L"Spine";
            cfg.WorldDampingLocation = 0.0f;
        }
        Chain chain({cfg});
        std::vector<uint8_t> changed;
        std::vector<Xf> pose;
        Xf component;
        float minX = 0.0f;
        for (int f = 0; f < 60; ++f)
        {
            component.T.X += 10.0f;
            pose = m.Ref;
            chain.Evaluate(m.Skel, pose, changed, component, 1.0f / 60.0f, nullptr);
            minX = std::min(minX, pose[static_cast<size_t>(m.Bone(L"Hair5"))].T.X);
            CHECK(LengthsKept(m, pose));
        }
        CHECK(minX < -5.0f);
    }
}

// Fixed substeps: a 30 fps frame runs two 60 Hz steps; a hitch runs at most max_substeps; the results stay sane.
static void TestSubsteps()
{
    Model m;
    SkelCompat::KawaiiNode cfg = HairNode();
    cfg.WorldDampingLocation = 0.2f;
    Chain at30({cfg}), at60({cfg});
    std::vector<uint8_t> changed;
    std::vector<Xf> pose30, pose60;
    Xf c30, c60;
    for (int f = 0; f < 120; ++f)
    {
        c60.T.X += 5.0f;
        pose60 = m.Ref;
        at60.Evaluate(m.Skel, pose60, changed, c60, 1.0f / 60.0f, nullptr);
        if (f % 2 == 1)
        {
            c30.T.X += 10.0f;
            pose30 = m.Ref;
            at30.Evaluate(m.Skel, pose30, changed, c30, 1.0f / 30.0f, nullptr);
        }
    }
    // (frame-rate independent: both trail by about the same)
    CHECK(Near(pose30[static_cast<size_t>(m.Bone(L"Hair5"))].T.X, pose60[static_cast<size_t>(m.Bone(L"Hair5"))].T.X, 1.0f));
    std::vector<Xf> pose = m.Ref;
    at60.Evaluate(m.Skel, pose, changed, c60, 2.0f, nullptr);   // a 2 s hitch
    CHECK(LengthsKept(m, pose));
}

// Warm-up: the bones settle under gravity before the first frame shows.
static void TestWarmUp()
{
    Model m;
    for (int i = 1; i <= 5; ++i) { m.Ref[static_cast<size_t>(m.Bone((L"Hair" + std::to_wstring(i)).c_str()))].T = {10.0f * static_cast<float>(i), 0, 100}; }
    m.Ref[static_cast<size_t>(m.Bone(L"Tip"))].T = {52, 0, 100};
    SkelCompat::KawaiiNode cfg = HairNode();
    cfg.Gravity[2] = -980.0f;
    cfg.WarmUpFrames = 120;
    cfg.NeedWarmUp = true;
    Chain chain({cfg});
    std::vector<uint8_t> changed;
    std::vector<Xf> pose = m.Ref;
    chain.Evaluate(m.Skel, pose, changed, Xf{}, 1.0f / 60.0f, nullptr);
    CHECK(pose[static_cast<size_t>(m.Bone(L"Hair5"))].T.Z < 99.0f);
}

static bool HasMessage(const SkelCompat::Config& cfg, const wchar_t* part)
{
    for (const auto& m : cfg.Messages)
    {
        if (m.find(part) != std::wstring::npos) { return true; }
    }
    return false;
}

static void TestConfig()
{
    const char* text = R"({"schema": "RebirthSkelCompat/1", "kawaii": [
        {"models": ["/Game/Character/Player/PC0010_13_Young_Sephiroth/Model/PC0010_13"], "requires_paks": ["YoungSephiroth_P"], "disable_bonamik": true,
         "nodes": [
          {"name": "hair", "root_bone": "H_Hair_a", "exclude_bones": ["H_Hair_x"], "additional_root_bones": ["H_Hair_b", {"root_bone": "H_Hair_c", "exclude_bones": []}],
           "damping": 0.2, "stiffness": 0.1, "world_damping_location": 0.5, "world_damping_rotation": 0.6, "radius": 2, "limit_angle": 30,
           "damping_curve": [[0, 1], [1, 0.5]], "dummy_bone_length": 4, "bone_forward_axis": "Y-", "planar_constraint": "z",
           "simulation_space": "base_bone", "simulation_base_bone": "C_Head", "target_framerate": 30, "use_fixed_substepping": false, "max_substeps": 2,
           "warm_up": true, "warm_up_frames": 10, "teleport_distance_threshold": 200, "teleport_rotation_threshold": 5, "skel_comp_move_scale": [1, 1, 0.5],
           "gravity": [0, 0, -980], "use_legacy_gravity": true, "simple_external_force": [10, 0, 0], "use_world_space_simple_external_force": false,
           "bone_subdivision_count": 2, "bone_subdivision_collision_only": false, "bone_constraint_subdivision_count": 1,
           "spheres": [{"bone": "C_Head", "offset": [1, 2, 3], "rotation": [0, 90, 0], "radius": 9, "limit_type": "inner"}],
           "capsules": [{"bone": "C_Spine_c", "radius": 6, "length": 20}],
           "tapered_capsules": [{"bone": "C_Spine_c", "radius0": 6, "radius1": 3, "length": 15}],
           "boxes": [{"bone": "C_Spine_c", "extent": [5, 6, 7]}],
           "planes": [{"offset": [0, 0, 0]}],
           "bone_constraints": [{"bone1": "H_Hair_a", "bone2": "H_Hair_b", "compliance": "rubber"}, ["H_Hair_b", "H_Hair_c"]],
           "bone_constraint_global_compliance": "wood", "bone_constraint_iteration_count_before_collision": 2},
          {"root_bone": "bad name"},
          {"root_bone": "C_Coat", "damping": 2, "spheres": [{"radius": 3}], "enable_wind": true}
         ]},
        {"model": "/Game/Character/Player/PC0010*", "nodes": [{"root_bone": "C_Coat"}]},
        {"nodes": [{"root_bone": "X"}]}
    ]})";
    SkelCompat::Config cfg;
    CHECK(SkelCompat::AppendConfig(text, L"kawaii.json", cfg));
    CHECK(cfg.Kawaii.size() == 2);
    if (cfg.Kawaii.size() == 2)
    {
        const auto& set = cfg.Kawaii[0];
        CHECK(set.DisableBonamik && set.RequiresPaks.size() == 1 && set.Nodes.size() == 2);
        CHECK(set.Models.size() == 1 && set.Models[0] == L"/Game/Character/Player/PC0010_13_Young_Sephiroth/Model/PC0010_13.PC0010_13");
        const auto& n = set.Nodes[0];
        CHECK(n.Name == L"hair" && n.RootBone == L"H_Hair_a" && n.ExcludeBones.size() == 1 && n.AdditionalRootBones.size() == 2);
        CHECK(n.AdditionalRootBones.size() == 2 && !n.AdditionalRootBones[0].OverrideExcludeBones && n.AdditionalRootBones[1].OverrideExcludeBones);
        CHECK(Near(n.Damping, 0.2f, 1e-6f) && Near(n.Stiffness, 0.1f, 1e-6f) && Near(n.WorldDampingLocation, 0.5f, 1e-6f) && Near(n.LimitAngle, 30.0f, 1e-6f));
        CHECK(n.DampingCurve.Keys.size() == 2 && n.DummyBoneLength == 4.0f && n.BoneForwardAxis == SkelCompat::KawaiiAxis::YNegative);
        CHECK(n.PlanarConstraint == SkelCompat::KawaiiPlanar::Z && n.SimulationSpace == SkelCompat::KawaiiSpace::BaseBone && n.SimulationBaseBone == L"C_Head");
        CHECK(n.TargetFramerate == 30 && !n.UseFixedSubstepping && n.MaxSubsteps == 2 && n.NeedWarmUp && n.WarmUpFrames == 10);
        CHECK(n.TeleportDistanceThreshold == 200.0f && n.TeleportRotationThreshold == 5.0f && n.SkelCompMoveScale[2] == 0.5f);
        CHECK(n.Gravity[2] == -980.0f && n.UseLegacyGravity && n.SimpleExternalForce[0] == 10.0f && !n.UseWorldSpaceSimpleExternalForce);
        CHECK(n.BoneSubdivisionCount == 2 && !n.BoneSubdivisionCollisionOnly && n.BoneConstraintSubdivisionCount == 1);
        CHECK(n.Spheres.size() == 1 && n.Spheres[0].Inner && n.Spheres[0].Radius == 9.0f && n.Spheres[0].Rotation[1] == 90.0f && n.Spheres[0].Offset[2] == 3.0f);
        CHECK(n.Capsules.size() == 1 && n.TaperedCapsules.size() == 1 && n.TaperedCapsules[0].Radius1 == 3.0f && n.Boxes.size() == 1 && n.Boxes[0].Extent[2] == 7.0f);
        CHECK(n.Planes.size() == 1 && n.Planes[0].Bone.empty());
        CHECK(n.BoneConstraints.size() == 2 && n.BoneConstraints[0].OverrideCompliance && n.BoneConstraints[0].Compliance == SkelCompat::KawaiiCompliance::Rubber);
        CHECK(n.BoneConstraintGlobalCompliance == SkelCompat::KawaiiCompliance::Wood && n.BoneConstraintIterationsBeforeCollision == 2);
        // the third node: its bad damping kept the default, its sphere without a bone dropped, wind noted
        const auto& coat = set.Nodes[1];
        CHECK(coat.RootBone == L"C_Coat" && Near(coat.Damping, 0.1f, 1e-6f) && coat.Spheres.empty());
        CHECK(cfg.Kawaii[1].Models.size() == 1 && cfg.Kawaii[1].Models[0] == L"/Game/Character/Player/PC0010*");
    }
    CHECK(HasMessage(cfg, L"needs its \"root_bone\""));
    CHECK(!HasMessage(cfg, L"enable_wind is not run in the game"));   // (3.18.0: it runs)
    if (!cfg.Kawaii.empty() && cfg.Kawaii[0].Nodes.size() == 2) { CHECK(cfg.Kawaii[0].Nodes[1].EnableWind); }
    CHECK(HasMessage(cfg, L"physics settings"));
    CHECK(HasMessage(cfg, L"needs its \"bone\""));
    CHECK(HasMessage(cfg, L"names no model"));
    // lookups: the exact path first, else the longest prefix
    CHECK(SkelCompat::KawaiiFor(cfg, L"/Game/Character/Player/PC0010_13_Young_Sephiroth/Model/PC0010_13.PC0010_13") == &cfg.Kawaii[0]);
    CHECK(SkelCompat::KawaiiFor(cfg, L"/Game/Character/Player/PC0010_00_Sephiroth/Model/PC0010_00.PC0010_00") == &cfg.Kawaii[1]);
    CHECK(SkelCompat::KawaiiFor(cfg, L"/Game/Character/Player/PC0000_00/Model/PC0000_00.PC0000_00") == nullptr);
    // pak requirements
    SkelCompat::FinishConfig(cfg, [](const std::wstring& name) { return name != L"YoungSephiroth_P"; });
    CHECK(cfg.Kawaii.size() == 1 && HasMessage(cfg, L"is off: it requires YoungSephiroth_P"));
    // a file with only "kawaii" is a file
    SkelCompat::Config only;
    CHECK(SkelCompat::AppendConfig(R"({"schema": "RebirthSkelCompat/1", "kawaii": []})", L"empty.json", only));
    // "disable_bonamik" naming the BNMs to turn off (a name, or a path: its name), the others left running
    SkelCompat::Config named;
    CHECK(SkelCompat::AppendConfig(R"({"schema": "RebirthSkelCompat/1", "kawaii": [
        {"model": "/Game/A/B.B", "disable_bonamik": ["PC0010_13_BNM", "/Game/Character/Player/PC0010_13_Young_Sephiroth/Model/PC0010_13_Hair_BNM.PC0010_13_Hair_BNM", 3],
         "nodes": [{"root_bone": "C_Coat"}]},
        {"model": "/Game/A/C.C", "disable_bonamik": "yes", "nodes": [{"root_bone": "C_Coat"}]}]})", L"named.json", named));
    CHECK(named.Kawaii.size() == 2);
    if (named.Kawaii.size() == 2)
    {
        const auto& set = named.Kawaii[0];
        CHECK(set.DisableBonamik && set.DisableBonamikAssets.size() == 2 && set.DisableBonamikAssets[0] == L"PC0010_13_BNM" &&
              set.DisableBonamikAssets[1] == L"PC0010_13_Hair_BNM");
        CHECK(!named.Kawaii[1].DisableBonamik && named.Kawaii[1].DisableBonamikAssets.empty());
    }
    CHECK(HasMessage(named, L"disable_bonamik: entries must be BNM names"));
    CHECK(HasMessage(named, L"disable_bonamik must be true, false or a list of BNM names"));
}

// (3.17.0) Sync bones: the chain's pose follows an animated bone's move from its reference pose.
static void TestSyncBones()
{
    Model m;
    m.Add(L"Knee", 0, {0, 10, 50});   // (a leg bone beside the hair, not in its chain)
    m.Skel.RefLocation.clear();
    for (const auto& x : m.Ref) { m.Skel.RefLocation.push_back(x.T); }
    const size_t knee = static_cast<size_t>(m.Bone(L"Knee"));
    const auto at = [&](const std::vector<Xf>& pose, const wchar_t* name) { return pose[static_cast<size_t>(m.Bone(name))].T; };
    // (the knee moved by the test, not the node: its length left out)
    const auto lengthsKept = [&](const std::vector<Xf>& pose, float tolerance) {
        std::vector<Xf> check = pose;
        check[knee] = m.Ref[knee];
        return LengthsKept(m, check, tolerance);
    };
    const auto run = [&](const SkelCompat::KawaiiNode& cfg, V3 kneeMove, int frames, std::vector<Xf>& pose) {
        Chain chain({cfg});
        std::vector<uint8_t> changed;
        for (int f = 0; f < frames; ++f)
        {
            pose = m.Ref;
            pose[knee].T += kneeMove;
            chain.Evaluate(m.Skel, pose, changed, Xf{}, 1.0f / 60.0f, nullptr);
        }
    };
    SkelCompat::KawaiiNode cfg = HairNode();
    cfg.ExcludeBones = {L"Tip"};
    cfg.Stiffness = 0.5f;
    SkelCompat::KawaiiSyncBone sync;
    sync.Bone = L"Knee";
    sync.Targets.push_back({L"Hair1", true, {}});
    cfg.SyncBones.push_back(sync);
    std::vector<Xf> pose, plain;
    // the knee where its reference pose has it: nothing moves
    run(cfg, {0, 0, 0}, 60, pose);
    CHECK(NearV(at(pose, L"Hair5"), at(m.Ref, L"Hair5"), 0.01f));
    // 20 cm forward: the hair goes forward with it, each bone kept at its length; the chain's root stays (it follows its
    // animation), even on the first frame
    {
        Chain chain({cfg});
        std::vector<uint8_t> changed;
        pose = m.Ref;
        pose[knee].T.X += 20.0f;
        chain.Evaluate(m.Skel, pose, changed, Xf{}, 1.0f / 60.0f, nullptr);
        CHECK(NearV(at(pose, L"Hair1"), at(m.Ref, L"Hair1"), 0.01f));
    }
    run(cfg, {20, 0, 0}, 120, pose);
    CHECK(at(pose, L"Hair5").X > 10.0f);
    CHECK(at(pose, L"Hair2").X > 2.0f && at(pose, L"Hair2").X < at(pose, L"Hair5").X);
    CHECK(lengthsKept(pose, 0.1f));
    CHECK(NearV(at(pose, L"Hair1"), at(m.Ref, L"Hair1"), 0.01f));
    // each moved bone turned toward its child from its animated direction (straight down here)
    for (const wchar_t* name : {L"Hair2", L"Hair3", L"Hair4"})
    {
        const int b = m.Bone(name);
        int child = -1;
        for (int c = 0; c < m.Skel.Count(); ++c)
        {
            if (m.Skel.Parents[static_cast<size_t>(c)] == b) { child = c; }
        }
        const V3 toChild = SafeNormal(pose[static_cast<size_t>(child)].T - pose[static_cast<size_t>(b)].T);
        CHECK(NearV(Rotate(pose[static_cast<size_t>(b)].R, V3{0, 0, -1}), toChild, 0.01f));
    }
    // the directions it may go: forward only kept back, backward only, and X scaled to nothing
    SkelCompat::KawaiiNode back = cfg;
    back.SyncBones[0].Direction[0] = SkelCompat::KawaiiSyncDirection::Negative;
    run(back, {20, 0, 0}, 60, pose);
    CHECK(NearV(at(pose, L"Hair5"), at(m.Ref, L"Hair5"), 0.01f));
    run(back, {-20, 0, 0}, 120, pose);
    CHECK(at(pose, L"Hair5").X < -10.0f);
    SkelCompat::KawaiiNode noX = cfg;
    noX.SyncBones[0].GlobalScale[0] = 0.0f;
    run(noX, {20, 0, 0}, 60, pose);
    CHECK(NearV(at(pose, L"Hair5"), at(m.Ref, L"Hair5"), 0.01f));
    // the scale along the chain: nothing at the root's end, all of it at the far end
    SkelCompat::KawaiiNode curved = cfg;
    curved.SyncBones[0].Targets[0].ScaleCurve.Keys = {{0.0f, 0.0f}, {1.0f, 1.0f}};
    run(curved, {20, 0, 0}, 120, pose);
    std::vector<Xf> full;
    run(cfg, {20, 0, 0}, 120, full);
    CHECK(at(pose, L"Hair2").X < at(full, L"Hair2").X - 1.0f && at(pose, L"Hair5").X > 5.0f);
    // the root alone (no child bones): nothing moves (its root follows its animation)
    SkelCompat::KawaiiNode rootOnly = cfg;
    rootOnly.SyncBones[0].Targets[0].IncludeChildBones = false;
    run(rootOnly, {20, 0, 0}, 60, pose);
    CHECK(NearV(at(pose, L"Hair5"), at(m.Ref, L"Hair5"), 0.01f));
    // a target below the root: it and the bones below it
    SkelCompat::KawaiiNode lower = cfg;
    lower.SyncBones[0].Targets[0].Bone = L"Hair3";
    run(lower, {20, 0, 0}, 120, pose);
    CHECK(NearV(at(pose, L"Hair2"), at(m.Ref, L"Hair2"), 0.01f) && at(pose, L"Hair5").X > 5.0f);
    // distance attenuation: every bone farther from the knee than its outer radius gets none of the move
    SkelCompat::KawaiiNode far = cfg;
    far.SyncBones[0].DistanceAttenuation = true;
    far.SyncBones[0].AttenuationInnerRadius = 0.0f;
    far.SyncBones[0].AttenuationOuterRadius = 1.0f;
    run(far, {20, 0, 0}, 60, pose);
    CHECK(NearV(at(pose, L"Hair5"), at(m.Ref, L"Hair5"), 0.01f));
    // by the move's length: none under 10 cm, all of it over 11
    SkelCompat::KawaiiNode byDistance = cfg;
    byDistance.SyncBones[0].ScaleCurveByDeltaDistance.Keys = {{0.0f, 0.0f}, {10.0f, 0.0f}, {11.0f, 1.0f}};
    run(byDistance, {5, 0, 0}, 60, pose);
    CHECK(NearV(at(pose, L"Hair5"), at(m.Ref, L"Hair5"), 0.01f));
    run(byDistance, {20, 0, 0}, 120, pose);
    CHECK(at(pose, L"Hair5").X > 10.0f);
    // a bone the model lacks: nothing (and no crash)
    SkelCompat::KawaiiNode missing = cfg;
    missing.SyncBones[0].Bone = L"NoSuchBone";
    run(missing, {20, 0, 0}, 30, pose);
    CHECK(NearV(at(pose, L"Hair5"), at(m.Ref, L"Hair5"), 0.01f));
    // with points put between the bones (and a dummy end bone): the bones keep their lengths (no stretch from points
    // placed before the sync)
    for (int collisionOnly = 0; collisionOnly < 2; ++collisionOnly)
    {
        SkelCompat::KawaiiNode sub = cfg;
        sub.BoneSubdivisionCount = 2;
        sub.BoneSubdivisionCollisionOnly = collisionOnly != 0;
        sub.DummyBoneLength = 5.0f;
        run(sub, {20, 0, 0}, 120, pose);
        CHECK(lengthsKept(pose, 0.15f));
        CHECK(at(pose, L"Hair5").X > 8.0f);
    }
    // no sync bones: the same as before
    SkelCompat::KawaiiNode none = cfg;
    none.SyncBones.clear();
    run(none, {20, 0, 0}, 60, plain);
    CHECK(NearV(at(plain, L"Hair5"), at(m.Ref, L"Hair5"), 0.001f));
    // without the model's reference places: it starts from the first pose it sees (the knee already moved: no move)
    Model bare;
    bare.Add(L"Knee", 0, {0, 10, 50});
    {
        Chain chain({cfg});
        std::vector<uint8_t> changed;
        for (int f = 0; f < 60; ++f)
        {
            pose = bare.Ref;
            pose[static_cast<size_t>(bare.Bone(L"Knee"))].T.X += 20.0f;
            chain.Evaluate(bare.Skel, pose, changed, Xf{}, 1.0f / 60.0f, nullptr);
        }
        CHECK(NearV(pose[static_cast<size_t>(bare.Bone(L"Hair5"))].T, bare.Ref[static_cast<size_t>(bare.Bone(L"Hair5"))].T, 0.01f));
    }
    // the config: a sync bone needs its bone and targets
    SkelCompat::Config bad;
    SkelCompat::AppendConfig(R"({"schema": "RebirthSkelCompat/1", "kawaii": [{"model": "/Game/A/B.B", "nodes": [{"root_bone": "Hair1",
        "sync_bones": [{"target_roots": ["Hair1"]}, {"bone": "Knee"}, {"bone": "Knee", "target_roots": ["Hair1"], "apply_direction_x": "up"}]}]}]})",
                             L"bad.json", bad);
    CHECK(bad.Kawaii.size() == 1 && bad.Kawaii[0].Nodes.size() == 1 && bad.Kawaii[0].Nodes[0].SyncBones.size() == 1);
    CHECK(bad.Messages.size() == 3);
}

// (3.17.0) A sphere that goes past a hanging bone in one frame: with fixed steps and the shapes placed between their
// last and this frame's places, the bone is pushed along on its side; without, the sphere jumps past it. And with
// keep_collision_side, a bone found inside on the sphere's other side is put back out on the side it was on.
static void TestFastShapes()
{
    Model m;
    m.Add(L"Mover", 0, {-30, 0, 70});
    const size_t mover = static_cast<size_t>(m.Bone(L"Mover"));
    const size_t hair3 = static_cast<size_t>(m.Bone(L"Hair3"));   // (at z 70, x 0)
    SkelCompat::KawaiiNode cfg = HairNode();
    cfg.ExcludeBones = {L"Tip"};
    cfg.Stiffness = 0.2f;
    cfg.Radius = 1.0f;
    SkelCompat::KawaiiLimit ball;
    ball.Bone = L"Mover";
    ball.Radius = 4.0f;
    cfg.Spheres.push_back(ball);
    // the sphere at x -6 (near the bone at x 0: 4 + 1 + 1 apart), then at x `to` the next frame
    const auto run = [&](const SkelCompat::KawaiiNode& c, float to = 6.0f) {
        Chain chain({c});
        std::vector<uint8_t> changed;
        std::vector<Xf> pose;
        for (int f = 0; f < 31; ++f)
        {
            pose = m.Ref;
            pose[mover].T = f < 30 ? V3{-6.0f, 0, 70} : V3{to, 0, 70};
            chain.Evaluate(m.Skel, pose, changed, Xf{}, 1.0f / 60.0f, nullptr);
        }
        return pose[hair3].T.X - pose[mover].T.X;   // (+: the bone on the far side of where the sphere went)
    };
    SkelCompat::KawaiiNode stepped = cfg;
    stepped.UseFixedSubstepping = true;
    stepped.TargetFramerate = 480;
    stepped.MaxSubsteps = 8;
    CHECK(run(stepped) > 0.0f);                    // pushed along ahead of it
    SkelCompat::KawaiiNode jumped = stepped;
    jumped.InterpolateLimitsInSubsteps = false;
    CHECK(run(jumped) < 0.0f);                     // (KawaiiPhysics' way: the sphere already past it at every step)
    SkelCompat::KawaiiNode once = cfg;
    once.UseFixedSubstepping = false;
    CHECK(run(once, 2.0f) < 0.0f);                 // one step: inside, on its far side: pushed out that way, through
    SkelCompat::KawaiiNode kept = once;
    kept.KeepCollisionSide = true;
    CHECK(run(kept, 2.0f) > 0.0f);                 // put back out on its side
}

// A node written as JSON (the editor's export) reads back the same.
static void TestJsonRoundTrip()
{
    SkelCompat::KawaiiNode n;
    n.Name = L"hair \"front\"";
    n.RootBone = L"C_HairF_a_Phy";
    n.ExcludeBones = {L"C_HairX"};
    n.AdditionalRootBones = {{L"C_HairB_a_Phy", false, {}}, {L"C_HairJ_a_Phy", true, {L"C_HairJ_c_Phy"}}};
    n.Damping = 0.15f;
    n.Stiffness = 0.12f;
    n.WorldDampingLocation = 0.65f;
    n.WorldDampingRotation = 0.6f;
    n.Radius = 0.75f;
    n.LimitAngle = 40.0f;
    n.StiffnessCurve.Keys = {{0.0f, 1.6f}, {1.0f, 0.8f}};
    n.RadiusCurve.Keys = {{0.0f, 0.67f}, {0.5f, 0.75f}, {1.0f, 1.5f}};
    n.DummyBoneLength = 4.0f;
    n.BoneForwardAxis = SkelCompat::KawaiiAxis::ZNegative;
    n.BoneSubdivisionCount = 3;
    n.BoneSubdivisionCollisionOnly = false;
    n.BoneSubdivisionDensifyByRadius = true;
    n.PlanarConstraint = SkelCompat::KawaiiPlanar::Y;
    n.SimulationSpace = SkelCompat::KawaiiSpace::BaseBone;
    n.SimulationBaseBone = L"C_Head_a";
    n.TargetFramerate = 30;
    n.UseFixedSubstepping = false;
    n.MaxSubsteps = 2;
    n.NeedWarmUp = true;
    n.WarmUpFrames = 12;
    n.UseWarmUpWhenResetDynamics = false;
    n.TeleportDistanceThreshold = 250.0f;
    n.TeleportRotationThreshold = 30.0f;
    n.SkelCompMoveScale[2] = 0.5f;
    n.Gravity[2] = -150.0f;
    n.UseLegacyGravity = true;
    n.UseDefaultGravityZ = true;
    n.UseWorldSpaceGravity = false;
    n.SimpleExternalForce[0] = 12.5f;
    n.UseWorldSpaceSimpleExternalForce = false;
    n.SkipBonamikBones = false;
    SkelCompat::KawaiiLimit sphere;
    sphere.Bone = L"C_Head_a";
    sphere.Offset[0] = 8.57f;
    sphere.Radius = 6.51f;
    sphere.Inner = true;
    n.Spheres.push_back(sphere);
    SkelCompat::KawaiiLimit capsule;
    capsule.Bone = L"C_Neck_a";
    capsule.Offset[0] = 4.5f;
    capsule.Rotation[0] = 90.0f;
    capsule.Rotation[1] = 180.0f;
    capsule.Radius = 5.77f;
    capsule.Length = 9.0f;
    n.Capsules.push_back(capsule);
    SkelCompat::KawaiiLimit tapered = capsule;
    tapered.Radius0 = 6.0f;
    tapered.Radius1 = 3.0f;
    n.TaperedCapsules.push_back(tapered);
    SkelCompat::KawaiiLimit box;
    box.Bone = L"C_Spine_c";
    box.Extent[0] = 4.0f;
    box.Extent[1] = 7.0f;
    box.Extent[2] = 9.0f;
    n.Boxes.push_back(box);
    SkelCompat::KawaiiLimit floor;
    floor.Offset[2] = 5.0f;
    n.Planes.push_back(floor);
    n.BoneConstraintGlobalCompliance = SkelCompat::KawaiiCompliance::Rubber;
    n.BoneConstraintIterationsBeforeCollision = 2;
    n.BoneConstraintIterationsAfterCollision = 3;
    n.AutoAddChildDummyBoneConstraint = false;
    n.BoneConstraintSubdivisionCount = 2;
    n.BoneConstraintSubdivisionFeedbackScale = 0.5f;
    n.BoneConstraints = {{L"A_b", L"B_b", false, SkelCompat::KawaiiCompliance::Leather, false},
                         {L"A_c", L"B_c", true, SkelCompat::KawaiiCompliance::Wood, true}};
    SkelCompat::KawaiiSyncBone sync;
    sync.Bone = L"L_Foreleg_a";
    sync.Targets = {{L"L_CoatA_a_Phy", true, {}}, {L"L_CoatB_b_Phy", false, {}}, {L"C_CoatA_a_Phy", true, {}}};
    sync.Targets[2].ScaleCurve.Keys = {{0.0f, 0.0f}, {0.6f, 1.0f}, {1.0f, 0.8f}};
    sync.GlobalScale[1] = 0.25f;
    sync.ScaleCurveByDeltaDistance.Keys = {{0.0f, 0.5f}, {80.0f, 1.0f}};
    sync.Direction[0] = SkelCompat::KawaiiSyncDirection::Positive;
    sync.Direction[2] = SkelCompat::KawaiiSyncDirection::None;
    sync.DistanceAttenuation = true;
    sync.AttenuationInnerRadius = 12.0f;
    sync.AttenuationOuterRadius = 40.0f;
    sync.MaxAttenuationRate = 0.75f;
    n.SyncBones.push_back(sync);
    SkelCompat::KawaiiSyncBone plainSync;
    plainSync.Bone = L"R_Foreleg_a";
    plainSync.Targets = {{L"R_CoatA_a_Phy", true, {}}};
    n.SyncBones.push_back(plainSync);
    n.InterpolateLimitsInSubsteps = false;
    n.KeepCollisionSide = true;
    const std::wstring text = L"{\"schema\": \"RebirthSkelCompat/1\", \"kawaii\": [{\"model\": \"/Game/A/B.B\", \"nodes\": [" + SkelCompat::KawaiiNodeJson(n, L"  ") + L"]}]}";
    SkelCompat::Config cfg;
    CHECK(SkelCompat::AppendConfig(SkelCompat::Narrow(text), L"export.json", cfg));
    for (const auto& m : cfg.Messages) { std::printf("  message: %s\n", SkelCompat::Narrow(m).c_str()); }
    CHECK(cfg.Messages.empty());
    CHECK(cfg.Kawaii.size() == 1 && cfg.Kawaii[0].Nodes.size() == 1);
    if (cfg.Kawaii.size() != 1 || cfg.Kawaii[0].Nodes.size() != 1)
    {
        std::printf("%s\n", SkelCompat::Narrow(text).c_str());
        return;
    }
    const SkelCompat::KawaiiNode& r = cfg.Kawaii[0].Nodes[0];
    CHECK(r.Name == n.Name && r.RootBone == n.RootBone && r.ExcludeBones == n.ExcludeBones && r.AdditionalRootBones.size() == 2);
    CHECK(r.AdditionalRootBones[1].OverrideExcludeBones && r.AdditionalRootBones[1].ExcludeBones == n.AdditionalRootBones[1].ExcludeBones &&
          !r.AdditionalRootBones[0].OverrideExcludeBones);
    CHECK(r.Damping == n.Damping && r.Stiffness == n.Stiffness && r.WorldDampingLocation == n.WorldDampingLocation && r.WorldDampingRotation == n.WorldDampingRotation &&
          r.Radius == n.Radius && r.LimitAngle == n.LimitAngle);
    CHECK(r.StiffnessCurve.Keys == n.StiffnessCurve.Keys && r.RadiusCurve.Keys == n.RadiusCurve.Keys && r.DampingCurve.Keys.empty());
    CHECK(r.DummyBoneLength == n.DummyBoneLength && r.BoneForwardAxis == n.BoneForwardAxis && r.BoneSubdivisionCount == 3 && !r.BoneSubdivisionCollisionOnly &&
          r.BoneSubdivisionDensifyByRadius);
    CHECK(r.PlanarConstraint == n.PlanarConstraint && r.SimulationSpace == n.SimulationSpace && r.SimulationBaseBone == n.SimulationBaseBone);
    CHECK(r.TargetFramerate == 30 && !r.UseFixedSubstepping && r.MaxSubsteps == 2 && r.NeedWarmUp && r.WarmUpFrames == 12 && !r.UseWarmUpWhenResetDynamics);
    CHECK(r.TeleportDistanceThreshold == 250.0f && r.TeleportRotationThreshold == 30.0f && r.SkelCompMoveScale[2] == 0.5f);
    CHECK(r.Gravity[2] == -150.0f && r.UseLegacyGravity && r.UseDefaultGravityZ && !r.UseWorldSpaceGravity && r.SimpleExternalForce[0] == 12.5f &&
          !r.UseWorldSpaceSimpleExternalForce && !r.SkipBonamikBones);
    CHECK(r.Spheres.size() == 1 && r.Spheres[0].Inner && r.Spheres[0].Radius == 6.51f && r.Spheres[0].Offset[0] == 8.57f);
    CHECK(r.Capsules.size() == 1 && r.Capsules[0].Rotation[1] == 180.0f && r.Capsules[0].Length == 9.0f);
    CHECK(r.TaperedCapsules.size() == 1 && r.TaperedCapsules[0].Radius0 == 6.0f && r.TaperedCapsules[0].Radius1 == 3.0f);
    CHECK(r.Boxes.size() == 1 && r.Boxes[0].Extent[2] == 9.0f && r.Planes.size() == 1 && r.Planes[0].Bone.empty() && r.Planes[0].Offset[2] == 5.0f);
    CHECK(r.BoneConstraintGlobalCompliance == SkelCompat::KawaiiCompliance::Rubber && r.BoneConstraintIterationsBeforeCollision == 2 &&
          r.BoneConstraintIterationsAfterCollision == 3 && !r.AutoAddChildDummyBoneConstraint && r.BoneConstraintSubdivisionCount == 2 &&
          r.BoneConstraintSubdivisionFeedbackScale == 0.5f);
    CHECK(r.BoneConstraints.size() == 2 && r.BoneConstraints[1].OverrideCompliance && r.BoneConstraints[1].Compliance == SkelCompat::KawaiiCompliance::Wood &&
          r.BoneConstraints[1].ExcludeFromSubdivision && !r.BoneConstraints[0].OverrideCompliance);
    CHECK(!r.InterpolateLimitsInSubsteps && r.KeepCollisionSide);
    CHECK(r.SyncBones.size() == 2);
    if (r.SyncBones.size() == 2)
    {
        const SkelCompat::KawaiiSyncBone& s = r.SyncBones[0];
        CHECK(s.Bone == sync.Bone && s.Targets.size() == 3 && s.Targets[0].Bone == L"L_CoatA_a_Phy" && s.Targets[0].IncludeChildBones &&
              !s.Targets[1].IncludeChildBones && s.Targets[2].ScaleCurve.Keys == sync.Targets[2].ScaleCurve.Keys);
        CHECK(s.GlobalScale[0] == 1.0f && s.GlobalScale[1] == 0.25f && s.ScaleCurveByDeltaDistance.Keys == sync.ScaleCurveByDeltaDistance.Keys);
        CHECK(s.Direction[0] == SkelCompat::KawaiiSyncDirection::Positive && s.Direction[1] == SkelCompat::KawaiiSyncDirection::Both &&
              s.Direction[2] == SkelCompat::KawaiiSyncDirection::None);
        CHECK(s.DistanceAttenuation && s.AttenuationInnerRadius == 12.0f && s.AttenuationOuterRadius == 40.0f && s.MaxAttenuationRate == 0.75f);
        CHECK(r.SyncBones[1].Bone == L"R_Foreleg_a" && r.SyncBones[1].Targets.size() == 1 && !r.SyncBones[1].DistanceAttenuation);
    }
    // the defaults write only the root
    SkelCompat::KawaiiNode plain;
    plain.RootBone = L"Root";
    plain.Name = L"Root";
    CHECK(SkelCompat::KawaiiNodeJson(plain) == L"{\n  \"root_bone\": \"Root\"\n}");
}


// ---- (3.18.0) external forces, wind, multipliers, alpha, sets, mirror, outside shapes, sweeps, triggers ----
static std::vector<Xf> Run(Chain& chain, const Model& m, int frames, const Environment* env = nullptr, Xf component = Xf{}, float dt = 1.0f / 60.0f)
{
    std::vector<uint8_t> changed;
    std::vector<Xf> pose;
    for (int f = 0; f < frames; ++f)
    {
        pose = m.Ref;
        chain.Evaluate(m.Skel, pose, changed, component, dt, nullptr, env);
    }
    return pose;
}
static V3 TipOf(const Model& m, const std::vector<Xf>& pose) { return pose[static_cast<size_t>(m.Bone(L"Tip"))].T; }

static SkelCompat::KawaiiNode ParsedNode(const std::string& json, SkelCompat::Config* keep = nullptr)
{
    SkelCompat::Config cfg;
    const std::string text = R"({"schema": "RebirthSkelCompat/1", "kawaii": [{"model": "/Game/A/B.B", "nodes": [)" + json + "]}]}";
    CHECK(SkelCompat::AppendConfig(text, L"t.json", cfg));
    SkelCompat::FinishConfig(cfg, [](const std::wstring&) { return true; });
    if (keep) { *keep = cfg; }
    if (cfg.Kawaii.empty() || cfg.Kawaii[0].Nodes.empty()) { return HairNode(); }
    return cfg.Kawaii[0].Nodes[0];
}

static void TestForcesParse()
{
    SkelCompat::Config cfg;
    const auto n = ParsedNode(R"({"root_bone": "Hair1", "enable_wind": true, "wind_scale": 2, "wind_direction_noise_angle": 10, "alpha": 0.5,
        "kawaii_physics_tag": "Hair.Front",
        "external_forces": [
          {"type": "basic", "force_dir": [100, 0, 0], "interval": 0.5, "external_force_space": "component", "apply_bone_filter": ["Hair3"],
           "random_force_scale_range": [0.5, 1.5], "force_rate_by_bone_length_rate": [[0, 0], [1, 1]]},
          {"type": "gravity", "use_override_gravity_direction": true, "override_gravity_direction": [1, 0, 0], "use_character_gravity_scale": true},
          {"type": "curve", "force_curve": [[0, 0, 0, 0], [1, 100, 0, 0]], "curve_evaluate_type": "max", "substep_count": 4, "time_scale": 2},
          {"type": "wind", "wind_direction_noise_angle": 5, "ignore_bone_filter": ["Hair1"]},
          {"type": "procedural_wind", "wind_preset": "Storm", "sway_force": 3, "wind_direction": [0, 1, 0], "seed": 7, "wind_source": "auto",
           "shared_wind_tag": "KawaiiPhysics.Shared.Coat"},
          {"type": "nonsense"}, {"type": "procedural_wind", "wind_preset": "Nope"}
        ]})", &cfg);
    CHECK(n.EnableWind && n.WindScale == 2.0f && n.WindDirectionNoiseAngle == 10.0f && n.Alpha == 0.5f && n.Tag == L"Hair.Front");
    CHECK(n.ExternalForces.size() == 5);
    if (n.ExternalForces.size() == 5)
    {
        const auto& b = n.ExternalForces[0];
        CHECK(b.Type == SkelCompat::KawaiiForceType::Basic && b.ForceDir[0] == 100.0f && b.Interval == 0.5f && b.Space == SkelCompat::KawaiiForceSpace::Component);
        CHECK(b.ApplyBoneFilter.size() == 1 && b.RandomForceScaleRange[0] == 0.5f && b.RandomForceScaleRange[1] == 1.5f && b.ForceRateByBoneLengthRate.Keys.size() == 2);
        const auto& g = n.ExternalForces[1];
        CHECK(g.Type == SkelCompat::KawaiiForceType::Gravity && g.UseOverrideGravityDirection && g.UseCharacterGravityScale && g.Space == SkelCompat::KawaiiForceSpace::World);
        const auto& c = n.ExternalForces[2];
        CHECK(c.Type == SkelCompat::KawaiiForceType::Curve && c.ForceCurve.Keys.size() == 2 && c.CurveEvaluateType == SkelCompat::KawaiiCurveEvaluate::Max && c.SubstepCount == 4 && c.TimeScale == 2.0f);
        CHECK(Near(c.ForceCurve.Eval(0.5f)[0], 50.0f, 1e-4f));
        const auto& w = n.ExternalForces[3];
        CHECK(w.Type == SkelCompat::KawaiiForceType::Wind && w.WindDirectionNoiseAngle == 5.0f && w.IgnoreBoneFilter.size() == 1);
        const auto& p = n.ExternalForces[4];
        // the preset first (Storm: constant 15, random 6), the force's own settings over it (sway 3)
        CHECK(p.IsWind() && p.ConstantForce == 15.0f && p.RandomForce == 6.0f && p.SwayForce == 3.0f && p.WindDirection[1] == 1.0f && p.Seed == 7);
        CHECK(p.WindSource == SkelCompat::KawaiiWindSource::Auto && p.SharedWindTag == L"KawaiiPhysics.Shared.Coat");
    }
    CHECK(HasMessage(cfg, L"needs \"type\""));
    CHECK(HasMessage(cfg, L"wind_preset Nope is not one"));
    // tags
    CHECK(SkelCompat::Detail::KawaiiTagMatches(L"Hair.Front", L"Hair", false) && !SkelCompat::Detail::KawaiiTagMatches(L"Hair.Front", L"Hair", true));
    CHECK(SkelCompat::Detail::KawaiiTagMatches(L"Hair.Front", L"hair.front", true) && !SkelCompat::Detail::KawaiiTagMatches(L"HairFront", L"Hair", false));
    CHECK(SkelCompat::Detail::IsTagName(L"A.B_c-1") && !SkelCompat::Detail::IsTagName(L"A..B") && !SkelCompat::Detail::IsTagName(L"A B"));
}

static void TestBasicAndGravityForces()
{
    Model m;
    // a basic force along +X (world): the chain swings that way, the tip most
    SkelCompat::KawaiiNode cfg = HairNode();
    SkelCompat::KawaiiExternalForce f;
    f.Type = SkelCompat::KawaiiForceType::Basic;
    f.ForceDir[0] = 300.0f;
    cfg.ExternalForces = {f};
    Chain pushed({cfg});
    auto pose = Run(pushed, m, 120);
    CHECK(TipOf(m, pose).X > 3.0f);
    CHECK(LengthsKept(m, pose));
    // only on the bones its filter names (Hair5 and below it its own place: Hair1 not pushed)
    cfg.ExternalForces[0].ApplyBoneFilter = {L"Hair5"};
    Chain filtered({cfg});
    pose = Run(filtered, m, 120);
    const float onlyTip = pose[static_cast<size_t>(m.Bone(L"Hair5"))].T.X;
    CHECK(onlyTip > 0.5f);
    cfg.ExternalForces[0].ApplyBoneFilter = {L"Nothing"};
    Chain none({cfg});
    pose = Run(none, m, 120);
    CHECK(Near(TipOf(m, pose).X, 0.0f, 1e-3f));
    // an interval: pushed once every interval only (on average less than every step)
    cfg.ExternalForces[0].ApplyBoneFilter.clear();
    const auto meanX = [&](Chain& chain) {
        std::vector<uint8_t> changed;
        std::vector<Xf> p;
        float sum = 0.0f;
        for (int f = 0; f < 180; ++f)
        {
            p = m.Ref;
            chain.Evaluate(m.Skel, p, changed, Xf{}, 1.0f / 60.0f, nullptr);
            sum += TipOf(m, p).X;
        }
        return sum / 180.0f;
    };
    Chain steady({cfg});
    const float everyStep = meanX(steady);
    cfg.ExternalForces[0].Interval = 0.5f;
    Chain pulsed({cfg});
    const float everyHalfSecond = meanX(pulsed);
    CHECK(everyHalfSecond > 0.0f && everyHalfSecond < everyStep * 0.5f);
    // gravity toward +X (its override direction), 980 with the character's gravity scale
    SkelCompat::KawaiiNode g = HairNode();
    SkelCompat::KawaiiExternalForce gf;
    gf.Type = SkelCompat::KawaiiForceType::Gravity;
    gf.UseOverrideGravityDirection = true;
    gf.OverrideGravityDirection[0] = 1.0f;
    g.ExternalForces = {gf};
    Chain weak({g});
    const float weakX = TipOf(m, Run(weak, m, 120)).X;
    g.ExternalForces[0].UseCharacterGravityScale = true;
    Environment env;
    env.HasGravityZ = true;
    env.GravityZ = -980.0f;
    Chain strong({g});
    const float strongX = TipOf(m, Run(strong, m, 120, &env)).X;
    CHECK(weakX > 0.0f && strongX > weakX + 1.0f);
}

static void TestCurveForce()
{
    Model m;
    SkelCompat::KawaiiNode cfg = HairNode();
    SkelCompat::KawaiiExternalForce f;
    f.Type = SkelCompat::KawaiiForceType::Curve;
    f.ForceCurve.Keys = {{0.0f, 0.0f, 0.0f, 0.0f}, {0.5f, 400.0f, 0.0f, 0.0f}, {1.0f, 0.0f, 0.0f, 0.0f}};
    float x[4]{};
    const SkelCompat::KawaiiCurveEvaluate how[] = {SkelCompat::KawaiiCurveEvaluate::Single, SkelCompat::KawaiiCurveEvaluate::Average, SkelCompat::KawaiiCurveEvaluate::Max,
                                                   SkelCompat::KawaiiCurveEvaluate::Min};
    for (int k = 0; k < 4; ++k)
    {
        f.CurveEvaluateType = how[k];
        cfg.ExternalForces = {f};
        Chain chain({cfg});
        float sum = 0.0f;
        std::vector<uint8_t> changed;
        std::vector<Xf> pose;
        for (int frame = 0; frame < 180; ++frame)
        {
            pose = m.Ref;
            chain.Evaluate(m.Skel, pose, changed, Xf{}, 1.0f / 60.0f, nullptr);
            sum += TipOf(m, pose).X;
        }
        x[k] = sum / 180.0f;
    }
    CHECK(x[0] > 0.5f && x[1] > 0.5f && x[2] >= x[1] - 1e-3f && x[3] <= x[1] + 1e-3f);
}

static void TestWindForces()
{
    Model m;
    Environment env;
    env.Wind = [](V3, WindSample& out) {
        out.Direction = {0, 1, 0};
        out.Speed = 120.0f;
        return true;
    };
    // the level's wind through a "wind" force
    SkelCompat::KawaiiNode cfg = HairNode();
    SkelCompat::KawaiiExternalForce w;
    w.Type = SkelCompat::KawaiiForceType::Wind;
    cfg.ExternalForces = {w};
    Chain windy({cfg});
    CHECK(TipOf(m, Run(windy, m, 120, &env)).Y > 1.0f);
    Chain still({cfg});
    CHECK(Near(TipOf(m, Run(still, m, 120)).Y, 0.0f, 1e-3f));   // (no wind source: nothing)
    // the node's own wind (enable_wind)
    SkelCompat::KawaiiNode nw = HairNode();
    nw.EnableWind = true;
    Chain node({nw});
    CHECK(TipOf(m, Run(node, m, 120, &env)).Y > 0.5f);
    nw.WindScale = 0.0f;
    Chain off({nw});
    CHECK(Near(TipOf(m, Run(off, m, 120, &env)).Y, 0.0f, 1e-3f));
}

static void TestProceduralWind()
{
    // the sample: (constant + sway + ripple) * cycle + random + gust
    SkelCompat::KawaiiExternalForce f;
    f.Type = SkelCompat::KawaiiForceType::ProceduralWind;
    f.ConstantForce = 10.0f;
    f.SwayForce = 4.0f;
    f.SwayPeriod = 2.0f;
    f.RippleForce = 0.0f;
    WindGust none;
    auto s = Node::ComputeWindSample(f, 0.5f, 0.0f, none, 0.5f);   // sway at a quarter period: its peak
    CHECK(Near(s.Sway, 4.0f, 1e-4f) && Near(s.Cycle, 1.0f, 1e-6f) && Near(s.Total, 14.0f, 1e-3f));
    WindGust gust;
    gust.Active = true;
    gust.Strength = 6.0f;
    gust.RiseTime = 1.0f;
    gust.HoldTime = 1.0f;
    gust.DecayTime = 2.0f;
    CHECK(Near(Node::ComputeWindSample(f, 0.5f, 0.0f, gust, 0.5f).Gust, 3.0f, 1e-4f));   // half way up
    CHECK(Near(Node::ComputeWindSample(f, 3.0f, 0.0f, gust, 3.0f).Gust, 3.0f, 1e-4f));   // half way down
    CHECK(Near(Node::ComputeWindSample(f, 5.0f, 0.0f, gust, 5.0f).Gust, 0.0f, 1e-4f));
    // smooth noise: within -1 - 1, the same for the same seed
    CHECK(std::fabs(Node::SampleSmoothNoise(3.3f, 5, 0)) <= 1.0f && Node::SampleSmoothNoise(3.3f, 5, 0) == Node::SampleSmoothNoise(3.3f, 5, 0));
    // on a chain: along its direction (+Y, world)
    Model m;
    SkelCompat::KawaiiNode cfg = HairNode();
    f.WindDirection[0] = 0.0f;
    f.WindDirection[1] = 1.0f;
    f.ConstantForce = 30.0f;
    f.SwayForce = 0.0f;
    cfg.ExternalForces = {f};
    Chain chain({cfg});
    const float calm = TipOf(m, Run(chain, m, 120)).Y;
    CHECK(calm > 1.0f);
    // a gust on it: further
    Chain gusty({cfg});
    Run(gusty, m, 60);
    gusty.Nodes[0].RequestGust(400.0f, 0.1f, 1.0f, 0.5f, V3{});
    const float gusted = TipOf(m, Run(gusty, m, 40)).Y;
    CHECK(gusted > calm + 1.0f);
    // a shared wind: the node takes its settings and time (its own constant force 0)
    SkelCompat::KawaiiNode shared = HairNode();
    SkelCompat::KawaiiExternalForce mine;
    mine.Type = SkelCompat::KawaiiForceType::ProceduralWind;
    mine.WindSource = SkelCompat::KawaiiWindSource::Shared;
    shared.ExternalForces = {mine};
    SharedWindState state;
    state.Params = f;
    Environment env;
    env.SharedWind = [&](const std::wstring& tag) -> SharedWindState* { return tag == L"KawaiiPhysics.Shared.Default" ? &state : nullptr; };
    Chain consumer({shared});
    CHECK(TipOf(m, Run(consumer, m, 120, &env)).Y > 1.0f);
    Chain alone({shared});
    CHECK(Near(TipOf(m, Run(alone, m, 120)).Y, 0.0f, 1e-3f));   // (no shared wind: its own, none)
    // a preset on its winds
    Chain preset({cfg});
    preset.Nodes[0].ApplyWindPreset(SkelCompat::Detail::KawaiiBuiltInWindPresets()[0]);
    CHECK(TipOf(m, Run(preset, m, 120)).Y < calm);   // (Breeze: constant 2)
    // a gust's transient wind ends (rise + hold + decay, a little after)
    gusty.Nodes[0].RequestGust(10.0f, 0.1f, 0.1f, 0.1f, V3{});
    Run(gusty, m, 2);
    const size_t during = gusty.Nodes[0].ForceCount();
    Run(gusty, m, 180);
    CHECK(during >= 2 && gusty.Nodes[0].ForceCount() == 1);
}

static void TestMultiplierAndAlpha()
{
    CHECK(Near(Node::EnvelopeAlpha(1, 1, 2, 0.5f), 0.5f, 1e-6f) && Node::EnvelopeAlpha(1, 1, 2, 1.5f) == 1.0f && Near(Node::EnvelopeAlpha(1, 1, 2, 3.0f), 0.5f, 1e-6f));
    float r, h, d;
    Node::ResolveEnvelope(1.0f, 0.4f, 0.8f, r, h, d);   // (edges longer than the time: both scaled)
    CHECK(Near(r + h + d, 1.0f, 1e-5f) && h == 0.0f && Near(r, 1.0f / 3.0f, 1e-5f));
    Node::ResolveEnvelope(2.0f, 0.5f, 0.5f, r, h, d);
    CHECK(Near(h, 1.0f, 1e-6f));
    // a multiplier that takes the stiffness away: the chain lags further behind a move
    Model m;
    SkelCompat::KawaiiNode cfg = HairNode();
    cfg.WorldDampingLocation = 0.0f;
    cfg.Stiffness = 0.3f;
    Xf moving;
    const auto lag = [&](Chain& chain) {
        Xf c;
        std::vector<uint8_t> changed;
        std::vector<Xf> pose;
        float most = 0.0f;
        for (int f = 0; f < 30; ++f)
        {
            c.T.X += 5.0f;
            pose = m.Ref;
            chain.Evaluate(m.Skel, pose, changed, c, 1.0f / 60.0f, nullptr);
            most = std::max(most, -TipOf(m, pose).X);
        }
        return most;
    };
    Chain plain({cfg});
    Chain soft({cfg});
    SkelCompat::KawaiiSettingsScale scale;
    scale.Stiffness = 0.0f;
    soft.Nodes[0].StartSettingsMultiplier(1, scale, 0.0f, 10.0f, 0.0f, true);
    CHECK(soft.Nodes[0].HasSettingsMultipliers());
    const float a = lag(plain), b = lag(soft);
    CHECK(b > a + 0.5f);
    soft.Nodes[0].StopSettingsMultiplier(1, 0.0f);
    std::vector<uint8_t> changed;
    std::vector<Xf> pose = m.Ref;
    soft.Evaluate(m.Skel, pose, changed, Xf{}, 1.0f / 60.0f, nullptr);
    CHECK(!soft.Nodes[0].HasSettingsMultipliers());
    // a pushed one with a lease: gone after its evaluations
    soft.Nodes[0].PushSettingsMultiplier(2, scale, 1.0f, 2, 0.0f);
    for (int f = 0; f < 4; ++f)
    {
        pose = m.Ref;
        soft.Evaluate(m.Skel, pose, changed, Xf{}, 1.0f / 60.0f, nullptr);
    }
    CHECK(!soft.Nodes[0].HasSettingsMultipliers());
    // alpha: 0 does not run; 0.5 shows half way between the pose and the physics
    SkelCompat::KawaiiNode zero = HairNode();
    zero.Alpha = 0.0f;
    Chain z({zero});
    pose = m.Ref;
    CHECK(z.Evaluate(m.Skel, pose, changed, Xf{}, 1.0f / 60.0f, nullptr) == 0);
    SkelCompat::KawaiiNode full = HairNode(), half = HairNode();
    full.Gravity[0] = 2000.0f;
    half.Gravity[0] = 2000.0f;
    half.Alpha = 0.5f;
    Chain cf({full}), ch({half});
    const float xf = TipOf(m, Run(cf, m, 60)).X, xh = TipOf(m, Run(ch, m, 60)).X;
    CHECK(xf > 1.0f && Near(xh, xf * 0.5f, std::max(0.3f, xf * 0.1f)));
    // the trigger's override of it
    ch.Nodes[0].SetAlphaOverride(true, 1.0f);
    CHECK(ch.Nodes[0].CurrentAlpha() == 1.0f);
    ch.Nodes[0].SetAlphaOverride(false, 0.0f);
    CHECK(ch.Nodes[0].CurrentAlpha() == 0.5f);
}

// Two hanging chains, L_Hair1.. and R_Hair1.. (10 cm apart in Y), for the sets and the mirror.
struct TwoChains
{
    Skeleton Skel;
    std::vector<Xf> Ref;
    TwoChains()
    {
        Add(L"Root", -1, {0, 0, 0});
        Add(L"Spine", 0, {0, 0, 100});
        for (const wchar_t* side : {L"L_", L"R_"})
        {
            const float y = side[0] == L'L' ? -5.0f : 5.0f;
            int parent = 1;
            for (int i = 1; i <= 4; ++i)
            {
                Add(std::wstring(side) + L"Hair" + std::to_wstring(i), parent, {0, y, 100 - 10.0f * static_cast<float>(i)});
                parent = static_cast<int>(Skel.Names.size()) - 1;
            }
        }
        std::vector<Xf> cs = Ref;
        Skel.RefLocation.clear();
        Skel.RefRotation.clear();
        for (const auto& x : cs)
        {
            Skel.RefLocation.push_back(x.T);
            Skel.RefRotation.push_back(x.R);
        }
    }
    void Add(const std::wstring& name, int parent, V3 at)
    {
        Skel.Names.push_back(name);
        Skel.Parents.push_back(parent);
        Xf x;
        x.T = at;
        Ref.push_back(x);
        Skel.RefLength.push_back(parent >= 0 ? Size(at - Ref[static_cast<size_t>(parent)].T) : 0.0f);
    }
    std::vector<Xf> Run(Chain& chain, int frames, const Environment* env = nullptr)
    {
        std::vector<uint8_t> changed;
        std::vector<Xf> pose;
        for (int f = 0; f < frames; ++f)
        {
            pose = Ref;
            chain.Evaluate(Skel, pose, changed, Xf{}, 1.0f / 60.0f, nullptr, env);
        }
        return pose;
    }
    V3 At(const std::vector<Xf>& pose, const wchar_t* name) const { return pose[static_cast<size_t>(Skel.Find(name))].T; }
};

static void TestSetsAndMirror()
{
    // sets by name: shapes, bone constraints (and their regex patterns), presets
    SkelCompat::Config cfg;
    CHECK(SkelCompat::AppendConfig(R"({"schema": "RebirthSkelCompat/1",
        "kawaii_limits_sets": {"Body.Front": {"spheres": [{"bone": "Spine", "offset": [6, -5, -25], "radius": 5}]}},
        "kawaii_bone_constraints_sets": {"Strands": {"bone_constraints": [["L_Hair1", "R_Hair1"]], "regex_pattern_list": [["L_Hair[2-4]", "R_Hair[2-4]"]]}},
        "kawaii_presets": {"Soft": {"damping": 0.33, "stiffness": 0.2, "root_bone": "Ignored", "kawaii_physics_tag": "Hair.Preset"}},
        "kawaii_wind_presets": {"Gale": {"constant_force": 30, "random_force": 0}}})", L"sets.json", cfg));
    CHECK(SkelCompat::AppendConfig(R"({"schema": "RebirthSkelCompat/1", "kawaii": [{"model": "/Game/A/B.B", "nodes": [
        {"root_bone": "L_Hair1", "additional_root_bones": ["R_Hair1"], "preset": "Soft", "limits_data_asset": "Body.Front", "bone_constraints_data_asset": ["Strands"],
         "mirror_data_table_for_limits": {"axis": "y"}, "external_forces": [{"type": "procedural_wind", "wind_preset": "Gale"}]},
        {"root_bone": "L_Hair1", "limits_data_asset": "Missing"}]}]})", L"nodes.json", cfg));
    SkelCompat::FinishConfig(cfg, [](const std::wstring&) { return true; });
    CHECK(cfg.Kawaii.size() == 1 && cfg.Kawaii[0].Nodes.size() == 2);
    if (cfg.Kawaii.size() != 1 || cfg.Kawaii[0].Nodes.size() != 2) { return; }
    const auto& n = cfg.Kawaii[0].Nodes[0];
    CHECK(Near(n.Damping, 0.33f, 1e-6f) && Near(n.Stiffness, 0.2f, 1e-6f) && n.RootBone == L"L_Hair1" && n.Tag.empty());   // (no bone assignment, no tag)
    CHECK(n.DataSpheres.size() == 1 && n.DataBoneConstraints.size() == 1 && n.ConstraintPatterns.size() == 1 && n.SetsResolved);
    CHECK(n.MirrorLimits.Axis == SkelCompat::KawaiiMirrorAxis::Y && !n.MirrorLimits.Prefixes.empty());
    CHECK(n.ExternalForces.size() == 1 && n.ExternalForces[0].ConstantForce == 30.0f);
    CHECK(HasMessage(cfg, L"limits_data_asset Missing is in no file"));
    TwoChains t;
    Chain chain({n});
    auto pose = t.Run(chain, 60);
    // the constraints: the named pair and the three the patterns made
    CHECK(chain.Nodes[0].MergedConstraints() >= 4);
    // the mirror: the set's sphere on Spine has no mirror bone (Spine): none; its own shape count stays 1
    CHECK(chain.Nodes[0].ShapeCount() == 1);
    // a sphere on L_Hair2 mirrored onto R_Hair2 (offset y -> -y)
    SkelCompat::KawaiiNode mirrored = n;
    mirrored.DataSpheres.clear();
    mirrored.ExternalForces.clear();
    mirrored.BoneConstraints.clear();
    mirrored.DataBoneConstraints.clear();
    mirrored.ConstraintPatterns.clear();
    mirrored.RootBone = L"L_Hair3";
    mirrored.AdditionalRootBones.clear();
    SkelCompat::KawaiiRoot r;
    r.Bone = L"R_Hair3";
    mirrored.AdditionalRootBones.push_back(r);
    SkelCompat::KawaiiLimit s;   // (in front of L_Hair4, a little inward: (3, -4, 60))
    s.Bone = L"L_Hair2";
    s.Offset[0] = 3.0f;
    s.Offset[1] = 1.0f;
    s.Offset[2] = -20.0f;
    s.Radius = 4.0f;
    mirrored.Spheres = {s};
    Chain mc({mirrored});
    pose = t.Run(mc, 90);
    CHECK(mc.Nodes[0].ShapeCount() == 2);
    // both strands pushed back from the spheres in front of them (+X offset): the same, mirrored
    const V3 l = t.At(pose, L"L_Hair4"), rr = t.At(pose, L"R_Hair4");
    CHECK(l.X < -0.5f && l.Y < -5.0f && Near(l.X, rr.X, 0.05f) && Near(l.Y, -rr.Y, 0.05f) && Near(l.Z, rr.Z, 0.05f));
    // without the mirror: only the left one
    mirrored.MirrorLimits.Axis = SkelCompat::KawaiiMirrorAxis::None;
    Chain one({mirrored});
    pose = t.Run(one, 90);
    CHECK(one.Nodes[0].ShapeCount() == 1 && t.At(pose, L"L_Hair4").X < -0.5f && Near(t.At(pose, L"R_Hair4").X, 0.0f, 0.05f));
}

static void TestOutsideShapes()
{
    Model m;   // the tip hangs at z 48
    // the ground: a box whose top is at z 60 (the simple world collision's ground box): the chain rests on it
    SkelCompat::KawaiiNode cfg = HairNode();
    cfg.World.UseSimpleWorldCollision = true;
    std::vector<WorldShape> ground(1);
    ground[0].Kind = 3;
    ground[0].Location = {0, 0, 50};
    ground[0].Extent = {100, 100, 10};
    Environment env;
    env.Ground = &ground;
    Chain chain({cfg});
    auto pose = Run(chain, m, 60, &env);
    CHECK(chain.Nodes[0].OuterShapeCount() == 1);
    Chain free({cfg});
    const float hanging = TipOf(m, Run(free, m, 60)).Z;
    CHECK(hanging < 50.0f && TipOf(m, pose).Z > 60.0f);   // (the end folds up out of the box)
    // the ground alone ("ground_collision") does the same without the level's shapes
    SkelCompat::KawaiiNode only = HairNode();
    only.World.GroundOnly = true;
    std::vector<WorldShape> level(1);
    level[0].Kind = 0;
    level[0].Location = {0, 0, 75};
    level[0].Radius = 50.0f;
    env.LevelShapes = &level;
    Chain g({only});
    Run(g, m, 2, &env);
    CHECK(g.Nodes[0].OuterShapeCount() == 1);
    Chain both({cfg});
    Run(both, m, 2, &env);
    CHECK(both.Nodes[0].OuterShapeCount() == 2);
    // a convex (kind 5): a unit cube's planes, 20 cm, at the chain's middle: the bones are put out of it
    SkelCompat::KawaiiNode cx = HairNode();
    cx.World.UseSimpleWorldCollision = true;
    cx.World.GroundCollision = false;
    std::vector<WorldShape> convex(1);
    convex[0].Kind = 5;
    convex[0].Location = {6, 0, 70};
    convex[0].Planes = {{1, 0, 0, 5}, {-1, 0, 0, 5}, {0, 1, 0, 5}, {0, -1, 0, 5}, {0, 0, 1, 5}, {0, 0, -1, 5}};
    convex[0].BoundsMin = {-5, -5, -5};
    convex[0].BoundsMax = {5, 5, 5};
    Environment cenv;
    cenv.LevelShapes = &convex;
    Chain cc({cx});
    pose = Run(cc, m, 60, &cenv);
    const V3 mid = pose[static_cast<size_t>(m.Bone(L"Hair3"))].T;
    CHECK(mid.X < 6.0f - 5.0f - cx.Radius + 0.6f);
    // shared shapes: a consumer collides with them, a source does not take them
    SkelCompat::KawaiiNode user = HairNode();
    user.UseSharedCollision = true;
    std::vector<WorldShape> shared(1);
    shared[0].Kind = 0;
    shared[0].Location = {5, 0, 70};
    shared[0].Radius = 6.0f;
    Environment senv;
    senv.Shared = [&](const std::wstring& tag) -> const std::vector<WorldShape>* { return tag == L"KawaiiPhysics.Shared.Default" ? &shared : nullptr; };
    Chain consumer({user});
    pose = Run(consumer, m, 60, &senv);
    CHECK(consumer.Nodes[0].OuterShapeCount() == 1 && pose[static_cast<size_t>(m.Bone(L"Hair3"))].T.X < -0.5f);
    user.SharedCollisionSource = true;
    Chain source({user});
    Run(source, m, 2, &senv);
    CHECK(source.Nodes[0].OuterShapeCount() == 0);
    // what a source publishes: its shapes in the world
    SkelCompat::KawaiiNode pub = HairNode();
    SkelCompat::KawaiiLimit ball;
    ball.Bone = L"Spine";
    ball.Offset[0] = 3.0f;
    ball.Radius = 7.0f;
    pub.Spheres = {ball};
    Chain p({pub});
    Xf moved;
    moved.T = {100, 0, 0};
    Run(p, m, 2, nullptr, moved);
    std::vector<WorldShape> out;
    p.Nodes[0].PublishShapes(out);
    CHECK(out.size() == 1 && out.size() == 1 && Near(out[0].Location.X, 103.0f, 1e-3f) && Near(out[0].Location.Z, 100.0f, 1e-3f) && out[0].Radius == 7.0f);
}

static void TestWorldSweep()
{
    Model m;
    // a wall at x = 4 the sweeps stop the bones at (their radius in front of it); a budget of sweeps a frame
    SkelCompat::KawaiiNode cfg = HairNode();
    cfg.World.AllowWorldCollision = true;
    cfg.Gravity[0] = 3000.0f;
    int budget = 0;
    int calls = 0;
    Environment env;
    env.Sweep = [&](V3 start, V3 end, float radius, V3& hit) {
        ++calls;
        if (end.X + radius <= 4.0f) { return false; }
        hit = end;
        hit.X = std::min(start.X, 4.0f - radius);
        return true;
    };
    env.SweepBudget = &budget;
    Chain chain({cfg});
    std::vector<uint8_t> changed;
    std::vector<Xf> pose;
    for (int f = 0; f < 120; ++f)
    {
        budget = 1000;
        pose = m.Ref;
        chain.Evaluate(m.Skel, pose, changed, Xf{}, 1.0f / 60.0f, nullptr, &env);
    }
    CHECK(calls > 0 && TipOf(m, pose).X <= 4.0f - cfg.Radius + 0.6f);
    // a budget of 2 a frame: no more than 2 sweeps
    Chain few({cfg});
    calls = 0;
    budget = 2;
    pose = m.Ref;
    few.Evaluate(m.Skel, pose, changed, Xf{}, 1.0f / 60.0f, nullptr, &env);
    CHECK(calls <= 2 && few.Nodes[0].SweepsLastFrame() <= 2);
}

static void TestTriggersAndWorldWindParse()
{
    SkelCompat::Config cfg;
    CHECK(SkelCompat::AppendConfig(R"({"schema": "RebirthSkelCompat/1", "kawaii": [{"model": "/Game/A/B.B",
        "world_wind": {"direction": [0, 1, 0], "speed": 250, "max_gust_amount": 0.3},
        "shared_winds": [{"wind_preset": "Strong", "shared_wind_tag": "KawaiiPhysics.Shared.Coat"}],
        "animation_triggers": [
          {"type": "add_external_force", "montage": "/Game/M/AM_Attack01.AM_Attack01", "start": 0.2, "end": 0.6, "filter_tags": ["Hair"],
           "external_forces": [{"type": "basic", "force_dir": [0, 0, 500]}]},
          {"type": "add_external_force", "montage": ["AM_Jump*"], "at": 0.1, "external_forces": [{"type": "basic", "force_dir": [0, 0, 900]}]},
          {"type": "set_alpha", "montage": "AM_Cut", "curve_name": "KawaiiAlpha", "default_alpha_if_no_curve": 0.25},
          {"type": "settings_multiplier", "montage": "AM_Run", "at": 0.0, "duration": 1.5, "settings_scale": {"damping": 0.5, "stiffness": 2}},
          {"type": "trigger_gust", "montage": "AM_Spin", "at": 0.3, "strength": 40, "rise_time": 0.1, "hold_time": 0.2, "decay_time": 0.5, "gust_target": "shared_publisher"},
          {"type": "wind_preset", "montage": "AM_Storm", "preset": "Storm"},
          {"type": "set_alpha", "montage": "AM_X", "at": 1},
          {"type": "trigger_gust"}
        ],
        "nodes": [{"root_bone": "Hair1", "kawaii_physics_tag": "Hair.Front"}]}]})", L"trig.json", cfg));
    CHECK(cfg.Kawaii.size() == 1);
    if (cfg.Kawaii.empty()) { return; }
    const auto& set = cfg.Kawaii[0];
    CHECK(set.WorldWind.Enabled && set.WorldWind.Speed == 250.0f && set.WorldWind.Direction[1] == 1.0f && set.WorldWind.MaxGustAmount == 0.3f);
    CHECK(set.SharedWinds.size() == 1 && set.SharedWinds[0].Tag == L"KawaiiPhysics.Shared.Coat" && set.SharedWinds[0].Wind.ConstantForce == 8.0f);
    CHECK(set.Triggers.size() == 6);
    if (set.Triggers.size() == 6)
    {
        const auto& a = set.Triggers[0];
        CHECK(a.Kind == SkelCompat::KawaiiTriggerKind::AddExternalForce && !a.Pulse && a.Montages[0] == L"AM_Attack01" && a.Start == 0.2f && a.End == 0.6f);
        CHECK(a.FilterTags.size() == 1 && a.Forces.size() == 1 && a.Forces[0].ForceDir[2] == 500.0f);
        CHECK(set.Triggers[1].Pulse && set.Triggers[1].At == 0.1f && set.Triggers[1].Montages[0] == L"AM_Jump*");
        CHECK(set.Triggers[2].Kind == SkelCompat::KawaiiTriggerKind::SetAlpha && set.Triggers[2].AlphaFromCurve && set.Triggers[2].CurveName == L"KawaiiAlpha" &&
              set.Triggers[2].DefaultAlpha == 0.25f);
        CHECK(set.Triggers[3].Pulse && set.Triggers[3].Duration == 1.5f && set.Triggers[3].Scale.Damping == 0.5f && set.Triggers[3].Scale.Stiffness == 2.0f &&
              set.Triggers[3].BlendOutTime == 0.5f);
        CHECK(set.Triggers[4].Kind == SkelCompat::KawaiiTriggerKind::TriggerGust && set.Triggers[4].SharedPublisher && set.Triggers[4].Strength == 40.0f);
        CHECK(set.Triggers[5].Kind == SkelCompat::KawaiiTriggerKind::WindPreset && set.Triggers[5].Pulse && set.Triggers[5].Preset == L"Storm");
    }
    CHECK(HasMessage(cfg, L"set_alpha is a state"));
    CHECK(HasMessage(cfg, L"needs \"montage\""));
    // the nodes a trigger picks by tag
    Chain chain(set.Nodes);
    int picked = 0;
    chain.ForTagged({L"Hair"}, false, [&](Node&) { ++picked; });
    chain.ForTagged({L"Hair"}, true, [&](Node&) { ++picked; });
    chain.ForTagged({}, true, [&](Node&) { ++picked; });
    CHECK(picked == 2);
    // a trigger's forces added to a node and taken off by their owner
    Model m;
    SkelCompat::KawaiiNode cfgNode = HairNode();
    Chain added({cfgNode});
    added.Nodes[0].AddForces(set.Triggers[0].Forces, 77, false);
    CHECK(added.Nodes[0].ForceCount() == 1);
    added.Nodes[0].RemoveForces(77);
    CHECK(added.Nodes[0].ForceCount() == 0);
    added.Nodes[0].AddForces(set.Triggers[1].Forces, 0, true);   // a pulse: one step, then gone
    Run(added, m, 1);
    CHECK(added.Nodes[0].ForceCount() == 0);
}

static void TestJsonRoundTrip318()
{
    const auto n = ParsedNode(R"({"root_bone": "Hair1", "enable_wind": true, "wind_scale": 0.5, "alpha": 0.75, "kawaii_physics_tag": "Coat.Back",
        "external_forces": [{"type": "basic", "force_dir": [1, 2, 3], "interval": 0.25, "external_force_space": "bone"},
                            {"type": "procedural_wind", "constant_force": 4, "sway_force": 2, "wind_direction": [0, 1, 0], "seed": 3, "strength_cycle_range": [0.5, 1.5]},
                            {"type": "curve", "force_curve": [[0, 1, 2, 3], [2, 4, 5, 6]], "curve_evaluate_type": "average"}],
        "limits_data_asset": "A.B", "bone_constraints_data_asset": ["C.D", "E"], "physics_asset_for_limits": true,
        "mirror_data_table_for_limits": {"axis": "x", "pairs": [["L_A", "R_A"]]}, "shared_collision_source": true, "shared_collision_group_tag": "Shared.Body",
        "allow_world_collision": true, "world_collision_max_sweeps_per_frame": 20, "use_simple_world_collision": true, "simple_world_collision_gather_radius": 150,
        "override_simple_world_collision_gather_radius": true, "simple_world_collision_ground_collision": false, "ground_collision": true})");
    const std::wstring json = SkelCompat::KawaiiNodeJson(n);
    std::string narrow;
    for (wchar_t c : json) { narrow += static_cast<char>(c); }
    const auto back = ParsedNode(narrow);
    CHECK(back.EnableWind && back.WindScale == 0.5f && back.Alpha == 0.75f && back.Tag == L"Coat.Back");
    CHECK(back.ExternalForces.size() == 3);
    if (back.ExternalForces.size() == 3)
    {
        CHECK(back.ExternalForces[0].ForceDir[2] == 3.0f && back.ExternalForces[0].Interval == 0.25f && back.ExternalForces[0].Space == SkelCompat::KawaiiForceSpace::Bone);
        CHECK(back.ExternalForces[1].ConstantForce == 4.0f && back.ExternalForces[1].Seed == 3 && back.ExternalForces[1].StrengthCycleRange[1] == 1.5f &&
              back.ExternalForces[1].WindDirection[1] == 1.0f);
        CHECK(back.ExternalForces[2].ForceCurve.Keys.size() == 2 && back.ExternalForces[2].CurveEvaluateType == SkelCompat::KawaiiCurveEvaluate::Average);
    }
    CHECK(back.LimitsSets.size() == 1 && back.BoneConstraintsSets.size() == 2 && back.PhysicsAssetForLimits && back.PhysicsAssetPath.empty());
    CHECK(back.MirrorLimits.Axis == SkelCompat::KawaiiMirrorAxis::X && back.MirrorLimits.Pairs.size() == 1);
    CHECK(back.SharedCollisionSource && back.SharedCollisionGroupTag == L"Shared.Body");
    CHECK(back.World.AllowWorldCollision && back.World.MaxSweepsPerFrame == 20 && back.World.UseSimpleWorldCollision && back.World.GatherRadius == 150.0f &&
          back.World.OverrideGatherRadius && !back.World.GroundCollision && back.World.GroundOnly);
    // defaults write nothing new
    const std::wstring plain = SkelCompat::KawaiiNodeJson(HairNode());
    CHECK(plain.find(L"external_forces") == std::wstring::npos && plain.find(L"enable_wind") == std::wstring::npos && plain.find(L"alpha") == std::wstring::npos);
}

// (3.18.0) An entry's triggers, shared winds and world wind written (the End editor's Export For Game) and read back.
static void TestEntryJsonRoundTrip318()
{
    const char* source = R"({"schema": "RebirthSkelCompat/1", "kawaii": [{"model": "/Game/A/B.B",
        "world_wind": {"direction": [0, 1, 0], "speed": 250, "strength": 2, "max_gust_amount": 0.3, "only_without_level_wind": false},
        "shared_winds": [{"wind_preset": "Strong", "shared_wind_tag": "KawaiiPhysics.Shared.Coat", "seed": 4}],
        "animation_triggers": [
          {"type": "add_external_force", "montage": "AM_Attack01", "start": 0.2, "end": 0.6, "filter_tags": ["Hair"], "filter_exact_match": true,
           "external_forces": [{"type": "basic", "force_dir": [0, 0, 500]}, {"type": "gravity", "use_character_gravity_scale": true}]},
          {"type": "add_external_force", "montage": ["AM_Jump*", "AM_Leap"], "at": 0.1, "external_forces": [{"type": "basic", "force_dir": [0, 0, 900]}]},
          {"type": "set_alpha", "montage": "AM_Cut", "curve_name": "KawaiiAlpha", "default_alpha_if_no_curve": 0.25},
          {"type": "set_alpha", "montage": "AM_Cut2", "constant_alpha": 0.4, "start": 0.5},
          {"type": "settings_multiplier", "montage": "AM_Run", "at": 0.0, "duration": 1.5, "settings_scale": {"damping": 0.5, "stiffness": 2}, "blend_in_time": 0.1},
          {"type": "settings_multiplier", "montage": "AM_Walk", "weight_source": "curve", "curve_name": "W", "blend_out_time": 0.7, "settings_scale": {"radius": 3}},
          {"type": "trigger_gust", "montage": "AM_Spin", "at": 0.3, "strength": 40, "rise_time": 0.1, "hold_time": 0.2, "decay_time": 0.5,
           "gust_direction": [1, 0, 0], "gust_target": "shared_publisher", "shared_wind_tag": "KawaiiPhysics.Shared.Coat"},
          {"type": "wind_preset", "montage": "AM_Storm", "preset": "Storm", "start": 0.4}
        ],
        "nodes": [{"root_bone": "Hair1"}]}]})";
    SkelCompat::Config first;
    CHECK(SkelCompat::AppendConfig(source, L"entry.json", first));
    CHECK(first.Kawaii.size() == 1);
    if (first.Kawaii.empty()) { return; }
    const auto& a = first.Kawaii[0];
    std::wstring triggers;
    for (size_t i = 0; i < a.Triggers.size(); ++i) { triggers += (i ? L", " : L"") + SkelCompat::KawaiiTriggerJson(a.Triggers[i]); }
    std::wstring winds;
    for (size_t i = 0; i < a.SharedWinds.size(); ++i) { winds += (i ? L", " : L"") + SkelCompat::KawaiiSharedWindJson(a.SharedWinds[i]); }
    const std::wstring text = L"{\"schema\": \"RebirthSkelCompat/1\", \"kawaii\": [{\"model\": \"/Game/A/B.B\", \"world_wind\": " + SkelCompat::KawaiiWorldWindJson(a.WorldWind) +
                              L", \"shared_winds\": [" + winds + L"], \"animation_triggers\": [" + triggers + L"], \"nodes\": [{\"root_bone\": \"Hair1\"}]}]}";
    std::string narrow;
    for (wchar_t c : text) { narrow += static_cast<char>(c); }
    SkelCompat::Config second;
    CHECK(SkelCompat::AppendConfig(narrow, L"entry2.json", second));
    CHECK(second.Messages.empty());
    for (const auto& m : second.Messages) { std::printf("  message: %ls\n", m.c_str()); }
    CHECK(second.Kawaii.size() == 1);
    if (second.Kawaii.empty()) { return; }
    const auto& b = second.Kawaii[0];
    CHECK(b.WorldWind.Enabled && b.WorldWind.Speed == 250.0f && b.WorldWind.Strength == 2.0f && b.WorldWind.Direction[1] == 1.0f && b.WorldWind.MaxGustAmount == 0.3f &&
          !b.WorldWind.OnlyWithoutLevelWind);
    CHECK(b.SharedWinds.size() == 1 && b.SharedWinds[0].Tag == L"KawaiiPhysics.Shared.Coat" && b.SharedWinds[0].Wind.ConstantForce == 8.0f && b.SharedWinds[0].Wind.Seed == 4);
    CHECK(b.Triggers.size() == a.Triggers.size() && b.Triggers.size() == 8);
    for (size_t i = 0; i < std::min(a.Triggers.size(), b.Triggers.size()); ++i)
    {
        const auto& x = a.Triggers[i];
        const auto& y = b.Triggers[i];
        const bool same = x.Kind == y.Kind && x.Montages == y.Montages && x.Pulse == y.Pulse && (x.Pulse ? x.At == y.At : x.Start == y.Start && x.End == y.End) &&
                          x.FilterTags == y.FilterTags && x.FilterExactMatch == y.FilterExactMatch && x.Forces.size() == y.Forces.size() &&
                          x.AlphaFromCurve == y.AlphaFromCurve && x.CurveName == y.CurveName && x.ConstantAlpha == y.ConstantAlpha && x.DefaultAlpha == y.DefaultAlpha &&
                          x.Scale.Damping == y.Scale.Damping && x.Scale.Stiffness == y.Scale.Stiffness && x.Scale.Radius == y.Scale.Radius &&
                          x.WeightFromCurve == y.WeightFromCurve && x.Duration == y.Duration && x.BlendInTime == y.BlendInTime && x.BlendOutTime == y.BlendOutTime &&
                          x.Strength == y.Strength && x.RiseTime == y.RiseTime && x.HoldTime == y.HoldTime && x.DecayTime == y.DecayTime &&
                          x.GustDirection[0] == y.GustDirection[0] && x.SharedPublisher == y.SharedPublisher && x.SharedWindTag == y.SharedWindTag && x.Preset == y.Preset;
        if (!same) { std::printf("  trigger %zu differs after the round trip\n", i); }
        CHECK(same);
    }
    CHECK(b.Triggers[0].Forces.size() == 2 && b.Triggers[0].Forces[1].UseCharacterGravityScale);
    // no world wind: nothing written
    CHECK(SkelCompat::KawaiiWorldWindJson(SkelCompat::KawaiiWorldWind{}).empty());
}

int main()
{
    TestMath();
    TestAtRest();
    TestInertia();
    TestTeleport();
    TestGravity();
    TestSphere();
    TestShapes();
    TestExcludeAndSkip();
    TestBoneConstraints();
    TestSubdivision();
    TestWorldAndBaseSpace();
    TestSubsteps();
    TestWarmUp();
    TestConfig();
    TestSyncBones();
    TestFastShapes();
    TestJsonRoundTrip();
    TestForcesParse();
    TestBasicAndGravityForces();
    TestCurveForce();
    TestWindForces();
    TestProceduralWind();
    TestMultiplierAndAlpha();
    TestSetsAndMirror();
    TestOutsideShapes();
    TestWorldSweep();
    TestTriggersAndWorldWindParse();
    TestJsonRoundTrip318();
    TestEntryJsonRoundTrip318();
    if (Failures == 0) { std::printf("all kawaii tests passed\n"); }
    else { std::printf("%d failure(s)\n", Failures); }
    return Failures == 0 ? 0 : 1;
}
