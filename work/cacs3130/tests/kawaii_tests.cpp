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
    CHECK(HasMessage(cfg, L"enable_wind is not run in the game"));
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
    if (Failures == 0) { std::printf("all kawaii tests passed\n"); }
    else { std::printf("%d failure(s)\n", Failures); }
    return Failures == 0 ? 0 : 1;
}
