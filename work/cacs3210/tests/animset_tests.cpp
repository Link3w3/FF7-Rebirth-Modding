// (3.20.0) Tests of a Kawaii Dynamic Motions node's "pose_animset": the config, the motion picked for what the character
// plays, and the solver playing set motions (additive from the first frame or a reference pose, cross-fades, loops and
// held ends, back to the node's own pose animation). g++ -std=c++20 -I../src animset_tests.cpp
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

static bool NearQ(Q4 a, Q4 b, float tolerance = 1e-3f)
{
    const float d = std::fabs(a.X * b.X + a.Y * b.Y + a.Z * b.Z + a.W * b.W);
    return d >= 1.0f - tolerance;
}

// "Root", "Wing1" above it with "Wing2" and "WingTip" along +X (10 cm each), every rotation the identity.
struct Model
{
    Skeleton Skel;
    std::vector<Xf> Ref;
    Model()
    {
        Add(L"Root", -1, {0, 0, 0});
        Add(L"Wing1", 0, {0, 0, 100});
        Add(L"Wing2", 1, {10, 0, 100});
        Add(L"WingTip", 2, {20, 0, 100});
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

static SkelCompat::Config Parse(const std::string& node)
{
    SkelCompat::Config cfg;
    const std::string text = R"({"schema": "RebirthSkelCompat/1", "kawaii": [{"model": "/Game/A/B.B", "nodes": [)" + node + "]}]}";
    CHECK(SkelCompat::AppendConfig(text, L"t.json", cfg));
    SkelCompat::FinishConfig(cfg, [](const std::wstring&) { return true; });
    return cfg;
}

static void TestParse()
{
    const SkelCompat::Config cfg = Parse(R"({"root_bone": "Wing1", "pose_animset": {"sets": ["/Game/Motion/Summon/SU2050_NeoBahamut/Battle00.Battle00",
        "/Game/Motion/Summon/SU2050_NeoBahamut/Neutral00"], "motions": {"B_NAttack*": "B_AtkBladeCombo01_0", "N_Run??_1": "B_Walk01_1", "B_Item*": ""},
        "idle": "N_Idle01_1", "battle_idle": "B_Idle01_1", "moving": "B_Walk01_1", "moving_speed": 50, "blend_seconds": 0.4, "speed": 0.5, "weight": 0.8,
        "additive_base": "reference_pose", "loop": false, "same_names": false, "preview": "B_AtkSpinSlash01"}})");
    CHECK(cfg.Messages.empty());
    CHECK(cfg.Kawaii.size() == 1 && cfg.Kawaii[0].Nodes.size() == 1);
    if (cfg.Kawaii.empty() || cfg.Kawaii[0].Nodes.empty()) { return; }
    const SkelCompat::KawaiiNode& n = cfg.Kawaii[0].Nodes[0];
    const SkelCompat::KawaiiPoseAnimSet& a = n.PoseAnimSet;
    CHECK(a.Sets.size() == 2 && a.Sets[0] == L"/Game/Motion/Summon/SU2050_NeoBahamut/Battle00.Battle00");
    CHECK(a.Sets[1] == L"/Game/Motion/Summon/SU2050_NeoBahamut/Neutral00.Neutral00");   // (a package path: its object)
    CHECK(a.Motions.size() == 3 && a.Motions[0].From == L"B_NAttack*" && a.Motions[0].To == L"B_AtkBladeCombo01_0" && a.Motions[2].To.empty());
    CHECK(a.Idle == L"N_Idle01_1" && a.BattleIdle == L"B_Idle01_1" && a.Moving == L"B_Walk01_1" && a.BattleMoving.empty());
    CHECK(a.MovingSpeed == 50.0f && a.BlendSeconds == 0.4f && a.Speed == 0.5f && a.Weight == 0.8f);
    CHECK(a.FromReference && a.Additive && a.Loop == 0 && !a.SameNames && a.Preview == L"B_AtkSpinSlash01");
    CHECK(n.Animated());
    // round trip through the node's JSON
    const std::wstring json = SkelCompat::KawaiiNodeJson(n);
    CHECK(json.find(L"\"pose_animset\"") != std::wstring::npos);
    const SkelCompat::Config again = Parse(SkelCompat::Narrow(json));
    CHECK(again.Messages.empty());
    if (!again.Kawaii.empty() && !again.Kawaii[0].Nodes.empty())
    {
        const SkelCompat::KawaiiPoseAnimSet& b = again.Kawaii[0].Nodes[0].PoseAnimSet;
        CHECK(b.Sets == a.Sets && b.Motions.size() == a.Motions.size() && b.Idle == a.Idle && b.BattleIdle == a.BattleIdle && b.Moving == a.Moving);
        CHECK(b.MovingSpeed == a.MovingSpeed && b.BlendSeconds == a.BlendSeconds && b.Speed == a.Speed && b.Weight == a.Weight);
        CHECK(b.FromReference == a.FromReference && b.Loop == a.Loop && b.SameNames == a.SameNames && b.Preview == a.Preview);
        for (size_t k = 0; k < b.Motions.size() && k < a.Motions.size(); ++k) { CHECK(b.Motions[k].From == a.Motions[k].From && b.Motions[k].To == a.Motions[k].To); }
    }
    // the defaults, one set as a string
    const SkelCompat::Config one = Parse(R"({"root_bone": "Wing1", "pose_animset": {"sets": "/Game/X/Battle00.Battle00"}})");
    CHECK(one.Messages.empty() && !one.Kawaii.empty() && one.Kawaii[0].Nodes[0].PoseAnimSet.Sets.size() == 1);
    if (!one.Kawaii.empty())
    {
        const auto& d = one.Kawaii[0].Nodes[0].PoseAnimSet;
        CHECK(d.SameNames && d.Additive && !d.FromReference && d.Loop == -1 && d.BlendSeconds == 0.25f && d.Weight == 1.0f);
        CHECK(SkelCompat::KawaiiNodeJson(one.Kawaii[0].Nodes[0]).find(L"\"pose_animset\": {\"sets\": [\"/Game/X/Battle00.Battle00\"]}") != std::wstring::npos);
    }
    // bad ones: said and left out
    for (const char* bad : {R"({"root_bone": "Wing1", "pose_animset": {"sets": []}})", R"({"root_bone": "Wing1", "pose_animset": {"sets": ["Battle00"]}})",
                            R"({"root_bone": "Wing1", "pose_animset": {"sets": ["/Game/X/B.B"], "additive_base": "middle"}})",
                            R"({"root_bone": "Wing1", "pose_animset": {"sets": ["/Game/X/B.B"], "motions": {"A": "a b"}}})",
                            R"({"root_bone": "Wing1", "pose_animset": {"sets": ["/Game/X/B.B"], "blend_seconds": 9}})",
                            R"({"root_bone": "Wing1", "pose_animset": {"sets": ["/Game/X/B.B"], "loop": "sometimes"}})"})
    {
        const SkelCompat::Config c = Parse(bad);
        CHECK(!c.Messages.empty());
        CHECK(!c.Kawaii.empty() && !c.Kawaii[0].Nodes.empty() && !c.Kawaii[0].Nodes[0].PoseAnimSet.Active());
    }
}

static void TestWildcards()
{
    using SkelCompat::WildcardMatchFolded;
    CHECK(WildcardMatchFolded(L"B_NAttack01_0", L"B_NAttack*"));
    CHECK(WildcardMatchFolded(L"b_nattack01_0", L"B_NATTACK*"));
    CHECK(WildcardMatchFolded(L"N_Run01_1", L"N_Run??_1"));
    CHECK(!WildcardMatchFolded(L"N_Run01_1_L180", L"N_Run??_1"));
    CHECK(WildcardMatchFolded(L"B_Walk01_0_L90", L"*Walk*"));
    CHECK(WildcardMatchFolded(L"anything", L"*"));
    CHECK(WildcardMatchFolded(L"B_DmgF01", L"B_Dmg*01"));
    CHECK(!WildcardMatchFolded(L"B_DmgF02", L"B_Dmg*01"));
    CHECK(WildcardMatchFolded(L"exact", L"Exact"));
    CHECK(!WildcardMatchFolded(L"exactly", L"exact"));
    CHECK(WildcardMatchFolded(L"", L"*"));
    CHECK(!WildcardMatchFolded(L"", L"?"));
}

static void TestPick()
{
    SkelCompat::KawaiiPoseAnimSet a;
    a.Sets = {L"/Game/S/Battle00.Battle00"};
    a.Motions = {{L"B_NAttack*", L"B_AtkBladeCombo01_0"}, {L"B_Missing*", L"B_NotThere"}, {L"B_Missing*", L"B_AtkSpinSlash01"}, {L"B_Item*", L""}};
    a.Idle = L"N_Idle01_1";
    a.BattleIdle = L"B_Idle01_1";
    a.Moving = L"B_Walk01_1";
    const std::vector<std::wstring> names = {L"B_AtkBladeCombo01_0", L"B_AtkSpinSlash01", L"N_Idle01_1", L"B_Idle01_1", L"B_Walk01_1", L"B_DmgF01"};
    const auto has = [&](const std::wstring& n) {
        for (const auto& x : names)
        {
            if (SkelCompat::NameEquals(x, n)) { return true; }
        }
        return false;
    };
    using SkelCompat::KawaiiAnimSetMotion;
    CHECK(KawaiiAnimSetMotion(a, L"B_NAttack02_0", true, false, has) == L"B_AtkBladeCombo01_0");
    CHECK(KawaiiAnimSetMotion(a, L"B_Missing01", true, false, has) == L"B_AtkSpinSlash01");   // (a pair whose motion the sets lack: the next)
    CHECK(KawaiiAnimSetMotion(a, L"B_Item01", true, true, has).empty());                     // ("": none)
    CHECK(KawaiiAnimSetMotion(a, L"B_DmgF01", true, false, has) == L"B_DmgF01");             // (the same name)
    CHECK(KawaiiAnimSetMotion(a, L"B_Other", true, false, has) == L"B_Idle01_1");
    CHECK(KawaiiAnimSetMotion(a, L"", false, false, has) == L"N_Idle01_1");
    CHECK(KawaiiAnimSetMotion(a, L"", true, true, has) == L"B_Walk01_1");
    CHECK(KawaiiAnimSetMotion(a, L"", false, true, has) == L"B_Walk01_1");
    a.SameNames = false;
    CHECK(KawaiiAnimSetMotion(a, L"B_DmgF01", true, false, has) == L"B_Idle01_1");
    a.BattleMoving = L"B_AtkSpinSlash01";
    CHECK(KawaiiAnimSetMotion(a, L"", true, true, has) == L"B_AtkSpinSlash01");
    CHECK(KawaiiAnimSetMotion(a, L"", false, true, has) == L"B_Walk01_1");
    a.Idle.clear();
    a.BattleIdle.clear();
    CHECK(KawaiiAnimSetMotion(a, L"", false, false, has).empty());
}

// A node on Wing1 whose motions turn Wing2 (its first simulated bone's parent is Wing1: Wing2 and WingTip move)
static SkelCompat::KawaiiNode WingNode(bool fromReference, bool additive = true)
{
    SkelCompat::KawaiiNode n;
    n.Name = L"wing";
    n.RootBone = L"Wing1";
    n.Stiffness = 1.0f;        // (the bones held to their pose: the pose is what the test reads)
    n.Damping = 1.0f;
    n.LimitAngle = 0.0f;
    n.WorldDampingLocation = 1.0f;
    n.WorldDampingRotation = 1.0f;
    n.PoseAnimSet.Sets = {L"/Game/S/Battle00.Battle00"};
    n.PoseAnimSet.Additive = additive;
    n.PoseAnimSet.FromReference = fromReference;
    n.PoseAnimSet.BlendSeconds = 0.0f;
    return n;
}

static std::shared_ptr<const Node::Motion> MakeMotion(const std::vector<Q4>& keys, bool loop, const Q4* base = nullptr, const wchar_t* bone = L"Wing2")
{
    auto tracks = std::make_shared<std::vector<SkelCompat::KawaiiKeyTrack>>();
    SkelCompat::KawaiiKeyTrack t;
    t.Bone = bone;
    for (const Q4& q : keys) { t.Keys.push_back({q.X, q.Y, q.Z, q.W}); }
    if (base)
    {
        t.Base = {base->X, base->Y, base->Z, base->W};
        t.HasBase = true;
    }
    tracks->push_back(std::move(t));
    auto m = std::make_shared<Node::Motion>();
    m->Tracks = tracks;
    m->Fps = 10.0f;
    m->Loop = loop;
    m->Name = L"test";
    return m;
}

// Wing2's local rotation in the pose the node made (its parent Wing1 kept)
static Q4 Wing2Local(const Model& m, const std::vector<Xf>& pose)
{
    const Xf& w1 = pose[static_cast<size_t>(m.Bone(L"Wing1"))];
    const Xf& w2 = pose[static_cast<size_t>(m.Bone(L"Wing2"))];
    return Normalized(Inverse(w1.R) * w2.R);
}

static std::vector<Xf> Step(Node& node, const Model& m, float dt)
{
    std::vector<Xf> pose = m.Ref;
    std::vector<uint8_t> changed(pose.size(), 0);
    node.Evaluate(m.Skel, pose, changed, Xf{}, dt);
    return pose;
}

static void TestSolver()
{
    const Model m;
    const Q4 yaw30 = FromAxisAngle({0, 0, 1}, DegreesToRadians(30.0f));
    const Q4 yaw60 = FromAxisAngle({0, 0, 1}, DegreesToRadians(60.0f));
    const Q4 yaw90 = FromAxisAngle({0, 0, 1}, DegreesToRadians(90.0f));
    const Q4 id{0, 0, 0, 1};
    // additive from the first frame: a motion 30 -> 90 degrees turns the bone 0 -> 60 from its pose
    {
        Node node(WingNode(false));
        Step(node, m, 1.0f / 60.0f);   // (the node's bones made)
        node.PlayMotion(MakeMotion({yaw30, yaw60, yaw90}, false), 0.0f);
        // a step of 0.1 s: frame 1 of 2 (10 fps), the turn 30 degrees
        std::vector<Xf> pose = Step(node, m, 0.1f);
        CHECK(NearQ(Wing2Local(m, pose), yaw30));
        pose = Step(node, m, 0.1f);   // frame 2: 60
        CHECK(NearQ(Wing2Local(m, pose), yaw60));
        pose = Step(node, m, 0.5f);   // past its end: held (no loop)
        CHECK(NearQ(Wing2Local(m, pose), yaw60));
        CHECK(node.PlayingMotion() && node.PlayingMotion()->Name == L"test");
    }
    // additive from a reference pose: the motion's own pose (here: its base 0, so its keys as they are)
    {
        Node node(WingNode(true));
        Step(node, m, 1.0f / 60.0f);
        node.PlayMotion(MakeMotion({yaw30, yaw60, yaw90}, false, &id), 0.0f);
        std::vector<Xf> pose = Step(node, m, 0.1f);
        CHECK(NearQ(Wing2Local(m, pose), yaw60));   // (frame 1: 60 from the reference 0)
        // a base of 30: the turn from it
        Node other(WingNode(true));
        Step(other, m, 1.0f / 60.0f);
        other.PlayMotion(MakeMotion({yaw30, yaw60, yaw90}, false, &yaw30), 0.0f);
        pose = Step(other, m, 0.0f);
        CHECK(NearQ(Wing2Local(m, pose), id));   // (frame 0: 30 less 30)
    }
    // absolute
    {
        Node node(WingNode(false, false));
        Step(node, m, 1.0f / 60.0f);
        node.PlayMotion(MakeMotion({yaw90, yaw90}, false), 0.0f);
        const std::vector<Xf> pose = Step(node, m, 0.05f);
        CHECK(NearQ(Wing2Local(m, pose), yaw90));
    }
    // a loop wraps from its last key to its second: 0, 30, 60, 0 (its last its first again), 10 fps
    {
        Node node(WingNode(false));
        Step(node, m, 1.0f / 60.0f);
        node.PlayMotion(MakeMotion({id, yaw30, yaw60, id}, true), 0.0f);
        std::vector<Xf> pose = Step(node, m, 0.3f);   // frame 3 == frame 0
        CHECK(NearQ(Wing2Local(m, pose), id));
        pose = Step(node, m, 0.1f);                   // frame 4 -> 1 (30)
        CHECK(NearQ(Wing2Local(m, pose), yaw30));
    }
    // a cross-fade: halfway (smoothstep 0.5 = 0.5) between two still motions of 0 and 60 degrees is 30
    {
        SkelCompat::KawaiiNode cfg = WingNode(false, false);
        Node node(cfg);
        Step(node, m, 1.0f / 60.0f);
        node.PlayMotion(MakeMotion({id}, true), 0.0f);
        Step(node, m, 0.1f);
        node.PlayMotion(MakeMotion({yaw60}, true), 1.0f);
        std::vector<Xf> pose = Step(node, m, 0.5f);
        CHECK(NearQ(Wing2Local(m, pose), yaw30, 2e-3f));
        pose = Step(node, m, 0.6f);   // done
        CHECK(NearQ(Wing2Local(m, pose), yaw60));
        // back to none: the bone's own pose again (the node has no pose_animation)
        node.PlayMotion(nullptr, 0.0f);
        pose = Step(node, m, 0.1f);
        CHECK(NearQ(Wing2Local(m, pose), id));
        CHECK(node.PlayingMotion() == nullptr);
    }
    // the node's own pose animation waits while a set's motion plays, and comes back after
    {
        SkelCompat::KawaiiNode cfg = WingNode(false, false);
        auto own = std::make_shared<std::vector<SkelCompat::KawaiiKeyTrack>>();
        SkelCompat::KawaiiKeyTrack t;
        t.Bone = L"Wing2";
        t.Keys.push_back({yaw90.X, yaw90.Y, yaw90.Z, yaw90.W});
        own->push_back(t);
        cfg.PoseAnimation.Tracks = own;
        cfg.PoseAnimation.Additive = false;
        Node node(cfg);
        std::vector<Xf> pose = Step(node, m, 1.0f / 60.0f);
        CHECK(NearQ(Wing2Local(m, pose), yaw90));
        node.PlayMotion(MakeMotion({yaw30}, true), 0.0f);
        pose = Step(node, m, 0.1f);
        CHECK(NearQ(Wing2Local(m, pose), yaw30));
        node.PlayMotion(nullptr, 0.0f);
        pose = Step(node, m, 0.1f);
        CHECK(NearQ(Wing2Local(m, pose), yaw90));
    }
    // a motion without a track for the bone leaves its pose; the same motion again does not restart it
    {
        Node node(WingNode(false, false));
        Step(node, m, 1.0f / 60.0f);
        auto other = MakeMotion({yaw90}, true, nullptr, L"Elsewhere");
        node.PlayMotion(other, 0.0f);
        std::vector<Xf> pose = Step(node, m, 0.1f);
        CHECK(NearQ(Wing2Local(m, pose), id));
        auto moving = MakeMotion({id, yaw30, yaw60}, false);
        node.PlayMotion(moving, 0.0f);
        Step(node, m, 0.1f);
        node.PlayMotion(moving, 0.0f);   // (again: kept, not restarted)
        pose = Step(node, m, 0.1f);
        CHECK(NearQ(Wing2Local(m, pose), yaw60));
        CHECK(node.PlayingMotionTime() > 0.15);
    }
}

// sync: the time set from the character's; the pick says whether it was for what the character plays
static void TestSync()
{
    SkelCompat::KawaiiPoseAnimSet a;
    a.Sets = {L"/Game/S/Battle00.Battle00"};
    a.Motions = {{L"B_NAttack*", L"B_AtkBladeCombo01_0"}};
    a.Idle = L"N_Idle01_1";
    const auto has = [](const std::wstring& n) { return n == L"B_AtkBladeCombo01_0" || n == L"N_Idle01_1" || n == L"B_Idle01_1"; };
    bool forPlaying = true;
    CHECK(SkelCompat::KawaiiAnimSetMotion(a, L"B_NAttack01_0", true, false, has, &forPlaying) == L"B_AtkBladeCombo01_0" && forPlaying);
    CHECK(SkelCompat::KawaiiAnimSetMotion(a, L"B_Idle01_1", true, false, has, &forPlaying) == L"B_Idle01_1" && forPlaying);
    CHECK(SkelCompat::KawaiiAnimSetMotion(a, L"N_Walk01_1", false, false, has, &forPlaying) == L"N_Idle01_1" && !forPlaying);
    const SkelCompat::Config cfg = Parse(R"({"root_bone": "Wing1", "pose_animset": {"sets": ["/Game/X/B.B"], "sync": true}})");
    CHECK(cfg.Messages.empty() && !cfg.Kawaii.empty() && cfg.Kawaii[0].Nodes[0].PoseAnimSet.Sync);
    if (!cfg.Kawaii.empty()) { CHECK(SkelCompat::KawaiiNodeJson(cfg.Kawaii[0].Nodes[0]).find(L"\"sync\": true") != std::wstring::npos); }
    // the solver: a motion of 0, 30, 60, 90 degrees at 10 fps put at 0.2 s shows 60
    const Model m;
    Node node(WingNode(false, false));
    Step(node, m, 1.0f / 60.0f);
    const Q4 id{0, 0, 0, 1};
    const Q4 yaw30 = FromAxisAngle({0, 0, 1}, DegreesToRadians(30.0f));
    const Q4 yaw60 = FromAxisAngle({0, 0, 1}, DegreesToRadians(60.0f));
    const Q4 yaw90 = FromAxisAngle({0, 0, 1}, DegreesToRadians(90.0f));
    node.PlayMotion(MakeMotion({id, yaw30, yaw60, yaw90}, false), 0.0f);
    node.SetMotionTime(0.2);
    std::vector<Xf> pose = Step(node, m, 0.0f);
    CHECK(NearQ(Wing2Local(m, pose), yaw60));
    node.SetMotionTime(0.05);   // (back: the character started it again)
    pose = Step(node, m, 0.0f);
    CHECK(NearQ(Wing2Local(m, pose), Slerp(id, yaw30, 0.5f)));
}

// a solid floor ("one_sided" plane): a chain the pose sends under it lies on it, its lengths kept; a KawaiiPhysics plane
// leaves a bone the pose takes deep under there
static void TestFloor()
{
    const Model m;   // (Wing1 at 100 cm, Wing2 and WingTip along +X)
    for (int oneSided = 0; oneSided < 2; ++oneSided)
    {
        SkelCompat::KawaiiNode cfg = WingNode(false, false);
        cfg.Radius = 1.0f;
        SkelCompat::KawaiiLimit floor;
        floor.Offset[2] = 95.0f;   // (5 cm under Wing1)
        floor.OneSided = oneSided != 0;
        cfg.Planes.push_back(floor);
        Node node(cfg);
        Step(node, m, 1.0f / 60.0f);
        // the pose: Wing2 pitched 60 degrees down (its tip 17 cm under Wing1's height: under the floor)
        const Q4 down = FromAxisAngle({0, 1, 0}, DegreesToRadians(60.0f));
        node.PlayMotion(MakeMotion({down}, true), 0.0f);
        std::vector<Xf> pose;
        for (int f = 0; f < 120; ++f) { pose = Step(node, m, 1.0f / 60.0f); }
        const V3 w2 = pose[static_cast<size_t>(m.Bone(L"Wing2"))].T, tip = pose[static_cast<size_t>(m.Bone(L"WingTip"))].T;
        if (oneSided)
        {
            CHECK(tip.Z >= 95.0f + 1.0f - 0.05f);   // (on the floor: its radius above it)
            CHECK(std::fabs(Size(tip - w2) - 10.0f) < 0.05f);
        }
        else
        {
            CHECK(tip.Z < 94.0f);   // (KawaiiPhysics' plane: the pose took it under in one go, it stays under)
        }
    }
}

int main()
{
    TestParse();
    TestWildcards();
    TestPick();
    TestSolver();
    TestSync();
    TestFloor();
    if (Failures)
    {
        std::printf("%d animset test(s) FAILED\n", Failures);
        return 1;
    }
    std::printf("all animset tests passed\n");
    return 0;
}
