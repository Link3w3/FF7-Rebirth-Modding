// KawaiiSolver.hpp - KawaiiPhysics' simulation, ported to plain C++ (Create a Character System 3.14.0).
//
// KawaiiPhysics is pafuhana1213's (https://github.com/pafuhana1213/KawaiiPhysics), MIT License:
//   Copyright (c) 2019-2026 pafuhana1213
//   Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
//   documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
//   rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
//   persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice
//   and this permission notice shall be included in all copies or substantial portions of the Software. THE SOFTWARE IS
//   PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
//   MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
//   HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
//   ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
//
// This is the simulation of its 1.21 AnimNode_KawaiiPhysics (AnimNode_KawaiiPhysics*.cpp), step for step, on a model's
// component-space bone transforms with UE 4.26's math (float FVector / FQuat / FTransform, their formulas), so that the
// game mod (main.dll: on the mesh right after the game animates it) and the End editor's node (its preview) move the bones
// the same way. Not here (the game has none of them to run on): wind from the scene, world collision traces, the shared
// and simple world collision subsystems, transient forces and settings multipliers and external force objects.
// (3.17.0) Sync bones (AnimNode_KawaiiPhysicsSyncBone.cpp): here, but for one thing: a bone the sync moved is turned
// toward its child from its pose's direction before the sync (ApplySimulateResult).
#pragma once

#include "SkelCompatCore.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace Kawaii
{
using SkelCompat::KawaiiAxis;
using SkelCompat::KawaiiCompliance;
using SkelCompat::KawaiiCurve;
using SkelCompat::KawaiiLimit;
using SkelCompat::KawaiiNode;
using SkelCompat::KawaiiPlanar;
using SkelCompat::KawaiiSpace;
using SkelCompat::KawaiiSyncBone;
using SkelCompat::KawaiiSyncDirection;
using SkelCompat::KawaiiSyncTarget;

inline constexpr float SmallNumber = 1.e-8f;        // UE's SMALL_NUMBER
inline constexpr float KindaSmallNumber = 1.e-4f;   // UE's KINDA_SMALL_NUMBER
inline constexpr float Pi = 3.1415926535897932f;

// ---- math: UE 4.26's ---------------------------------------------------------------------------------------------------
struct V3
{
    float X = 0, Y = 0, Z = 0;
    float& operator[](int i) { return i == 0 ? X : (i == 1 ? Y : Z); }
    float operator[](int i) const { return i == 0 ? X : (i == 1 ? Y : Z); }
};
inline V3 operator+(V3 a, V3 b) { return {a.X + b.X, a.Y + b.Y, a.Z + b.Z}; }
inline V3 operator-(V3 a, V3 b) { return {a.X - b.X, a.Y - b.Y, a.Z - b.Z}; }
inline V3 operator-(V3 a) { return {-a.X, -a.Y, -a.Z}; }
inline V3 operator*(V3 a, float s) { return {a.X * s, a.Y * s, a.Z * s}; }
inline V3 operator*(float s, V3 a) { return {a.X * s, a.Y * s, a.Z * s}; }
inline V3 operator/(V3 a, float s) { const float r = 1.0f / s; return {a.X * r, a.Y * r, a.Z * r}; }
inline V3& operator+=(V3& a, V3 b) { a = a + b; return a; }
inline V3& operator-=(V3& a, V3 b) { a = a - b; return a; }
inline V3& operator*=(V3& a, float s) { a = a * s; return a; }
inline bool operator==(V3 a, V3 b) { return a.X == b.X && a.Y == b.Y && a.Z == b.Z; }
inline bool operator!=(V3 a, V3 b) { return !(a == b); }
inline V3 Mul(V3 a, V3 b) { return {a.X * b.X, a.Y * b.Y, a.Z * b.Z}; }
inline float Dot(V3 a, V3 b) { return a.X * b.X + a.Y * b.Y + a.Z * b.Z; }
inline V3 Cross(V3 a, V3 b) { return {a.Y * b.Z - a.Z * b.Y, a.Z * b.X - a.X * b.Z, a.X * b.Y - a.Y * b.X}; }
inline float SizeSq(V3 v) { return v.X * v.X + v.Y * v.Y + v.Z * v.Z; }
inline float Size(V3 v) { return std::sqrt(SizeSq(v)); }
inline V3 SafeNormal(V3 v, float tolerance = SmallNumber)
{
    const float sq = SizeSq(v);
    if (sq == 1.0f) { return v; }
    if (sq < tolerance) { return {}; }
    const float scale = 1.0f / std::sqrt(sq);
    return {v.X * scale, v.Y * scale, v.Z * scale};
}
inline bool NearlyZero(V3 v, float tolerance = KindaSmallNumber)
{
    return std::fabs(v.X) <= tolerance && std::fabs(v.Y) <= tolerance && std::fabs(v.Z) <= tolerance;
}
inline V3 Lerp(V3 a, V3 b, float t) { return a + (b - a) * t; }
inline float Lerp(float a, float b, float t) { return a + (b - a) * t; }
inline V3 Abs(V3 v) { return {std::fabs(v.X), std::fabs(v.Y), std::fabs(v.Z)}; }
inline float Clamp(float v, float lo, float hi) { return v < lo ? lo : (v < hi ? v : hi); }
inline float RadiansToDegrees(float r) { return r * (180.0f / Pi); }
inline float DegreesToRadians(float d) { return d * (Pi / 180.0f); }
inline float Acos(float v) { return std::acos(v < -1.0f ? -1.0f : (v < 1.0f ? v : 1.0f)); }

// FVector::RotateAngleAxis
inline V3 RotateAngleAxis(V3 v, float angleDeg, V3 axis)
{
    const float s = std::sin(DegreesToRadians(angleDeg));
    const float c = std::cos(DegreesToRadians(angleDeg));
    const float xx = axis.X * axis.X, yy = axis.Y * axis.Y, zz = axis.Z * axis.Z;
    const float xy = axis.X * axis.Y, yz = axis.Y * axis.Z, zx = axis.Z * axis.X;
    const float xs = axis.X * s, ys = axis.Y * s, zs = axis.Z * s;
    const float omc = 1.0f - c;
    return {(omc * xx + c) * v.X + (omc * xy - zs) * v.Y + (omc * zx + ys) * v.Z,
            (omc * xy + zs) * v.X + (omc * yy + c) * v.Y + (omc * yz - xs) * v.Z,
            (omc * zx - ys) * v.X + (omc * yz + xs) * v.Y + (omc * zz + c) * v.Z};
}

// FMath::ClosestPointOnSegment / PointDistToSegmentSquared
inline V3 ClosestPointOnSegment(V3 point, V3 start, V3 end)
{
    const V3 segment = end - start;
    const V3 toPoint = point - start;
    const float dot1 = Dot(toPoint, segment);
    if (dot1 <= 0.0f) { return start; }
    const float dot2 = Dot(segment, segment);
    if (dot2 <= dot1) { return end; }
    return start + segment * (dot1 / dot2);
}
inline float PointDistToSegmentSquared(V3 point, V3 start, V3 end) { return SizeSq(point - ClosestPointOnSegment(point, start, end)); }

// FPlane: a normal and W (the plane holds the points p with Dot(p, normal) == W)
struct Plane
{
    V3 N;
    float W = 0;
    static Plane Through(V3 base, V3 normal) { return {normal, Dot(base, normal)}; }
    float PlaneDot(V3 p) const { return Dot(p, N) - W; }
};
inline V3 PointPlaneProject(V3 point, const Plane& plane) { return point - plane.N * plane.PlaneDot(point); }
// FMath::SegmentPlaneIntersection (through GetTForSegmentPlaneIntersect)
inline bool SegmentPlaneIntersection(V3 start, V3 end, const Plane& plane, V3& out)
{
    const float t = (plane.W - Dot(start, plane.N)) / Dot(end - start, plane.N);
    if (t > -KindaSmallNumber && t < 1.0f + KindaSmallNumber)
    {
        out = start + (end - start) * t;
        return true;
    }
    return false;
}

struct Q4
{
    float X = 0, Y = 0, Z = 0, W = 1;
};
inline Q4 operator*(Q4 a, Q4 b)   // (a * b).Rotate(v) == a.Rotate(b.Rotate(v))
{
    return {a.W * b.X + a.X * b.W + a.Y * b.Z - a.Z * b.Y, a.W * b.Y - a.X * b.Z + a.Y * b.W + a.Z * b.X,
            a.W * b.Z + a.X * b.Y - a.Y * b.X + a.Z * b.W, a.W * b.W - a.X * b.X - a.Y * b.Y - a.Z * b.Z};
}
inline V3 Rotate(Q4 q, V3 v)
{
    const V3 qv{q.X, q.Y, q.Z};
    const V3 t = Cross(qv, v) * 2.0f;
    return v + t * q.W + Cross(qv, t);
}
inline V3 Unrotate(Q4 q, V3 v)
{
    const V3 qv{-q.X, -q.Y, -q.Z};
    const V3 t = Cross(qv, v) * 2.0f;
    return v + t * q.W + Cross(qv, t);
}
inline Q4 Inverse(Q4 q) { return {-q.X, -q.Y, -q.Z, q.W}; }
inline Q4 Normalized(Q4 q, float tolerance = SmallNumber)
{
    const float sq = q.X * q.X + q.Y * q.Y + q.Z * q.Z + q.W * q.W;
    if (sq < tolerance) { return {}; }
    const float scale = 1.0f / std::sqrt(sq);
    return {q.X * scale, q.Y * scale, q.Z * scale, q.W * scale};
}
inline float Angle(Q4 q) { return 2.0f * Acos(q.W); }
inline V3 AxisX(Q4 q) { return Rotate(q, {1, 0, 0}); }
inline V3 AxisY(Q4 q) { return Rotate(q, {0, 1, 0}); }
inline V3 AxisZ(Q4 q) { return Rotate(q, {0, 0, 1}); }
// FQuat(Axis, AngleRad)
inline Q4 FromAxisAngle(V3 axis, float angle)
{
    const float half = 0.5f * angle;
    const float s = std::sin(half);
    return {s * axis.X, s * axis.Y, s * axis.Z, std::cos(half)};
}
// FQuat::FindBetweenVectors
inline Q4 FindBetweenVectors(V3 a, V3 b)
{
    const float normAB = std::sqrt(SizeSq(a) * SizeSq(b));
    float w = normAB + Dot(a, b);
    Q4 result;
    if (w >= 1e-6f * normAB) { result = {a.Y * b.Z - a.Z * b.Y, a.Z * b.X - a.X * b.Z, a.X * b.Y - a.Y * b.X, w}; }
    else
    {
        w = 0.0f;
        result = std::fabs(a.X) > std::fabs(a.Y) ? Q4{-a.Z, 0.0f, a.X, w} : Q4{0.0f, -a.Z, a.Y, w};
    }
    return Normalized(result);
}
// FQuat::Slerp (normalized)
inline Q4 Slerp(Q4 a, Q4 b, float t)
{
    const float rawCosom = a.X * b.X + a.Y * b.Y + a.Z * b.Z + a.W * b.W;
    const float cosom = rawCosom >= 0.0f ? rawCosom : -rawCosom;
    float scale0, scale1;
    if (cosom < 0.9999f)
    {
        const float omega = Acos(cosom);
        const float invSin = 1.0f / std::sin(omega);
        scale0 = std::sin((1.0f - t) * omega) * invSin;
        scale1 = std::sin(t * omega) * invSin;
    }
    else
    {
        scale0 = 1.0f - t;
        scale1 = t;
    }
    scale1 = rawCosom >= 0.0f ? scale1 : -scale1;
    return Normalized({scale0 * a.X + scale1 * b.X, scale0 * a.Y + scale1 * b.Y, scale0 * a.Z + scale1 * b.Z, scale0 * a.W + scale1 * b.W});
}
// FRotator(Pitch, Yaw, Roll).Quaternion()
inline Q4 FromRotator(float pitch, float yaw, float roll)
{
    const float half = Pi / 180.0f / 2.0f;
    const float p = std::fmod(pitch, 360.0f) * half, y = std::fmod(yaw, 360.0f) * half, r = std::fmod(roll, 360.0f) * half;
    const float sp = std::sin(p), cp = std::cos(p), sy = std::sin(y), cy = std::cos(y), sr = std::sin(r), cr = std::cos(r);
    return {cr * sp * sy - sr * cp * cy, -cr * sp * cy - sr * cp * sy, cr * cp * sy - sr * sp * cy, cr * cp * cy + sr * sp * sy};
}

inline float SafeReciprocal(float v) { return std::fabs(v) <= SmallNumber ? 0.0f : 1.0f / v; }
inline V3 SafeScaleReciprocal(V3 s) { return {SafeReciprocal(s.X), SafeReciprocal(s.Y), SafeReciprocal(s.Z)}; }

// FTransform (no negative scales: KawaiiPhysics' bones have none)
struct Xf
{
    Q4 R;
    V3 T;
    V3 S{1, 1, 1};
};
inline V3 TransformPosition(const Xf& x, V3 p) { return Rotate(x.R, Mul(x.S, p)) + x.T; }
inline V3 TransformVector(const Xf& x, V3 v) { return Rotate(x.R, Mul(x.S, v)); }
inline V3 InverseTransformPosition(const Xf& x, V3 p) { return Mul(Unrotate(x.R, p - x.T), SafeScaleReciprocal(x.S)); }
inline V3 InverseTransformVector(const Xf& x, V3 v) { return Mul(Unrotate(x.R, v), SafeScaleReciprocal(x.S)); }
inline Q4 TransformRotation(const Xf& x, Q4 q) { return x.R * q; }
inline Q4 InverseTransformRotation(const Xf& x, Q4 q) { return Inverse(x.R) * q; }
// a * b: a, then b
inline Xf Multiply(const Xf& a, const Xf& b) { return {b.R * a.R, Rotate(b.R, Mul(b.S, a.T)) + b.T, Mul(a.S, b.S)}; }
inline Xf InverseOf(const Xf& x)
{
    const Q4 r = Inverse(x.R);
    const V3 s = SafeScaleReciprocal(x.S);
    return {r, Rotate(r, Mul(s, -x.T)), s};
}
// a.GetRelativeTransform(other): a * other^-1
inline Xf Relative(const Xf& a, const Xf& other)
{
    const V3 s = SafeScaleReciprocal(other.S);
    const Q4 inv = Inverse(other.R);
    return {inv * a.R, Mul(Rotate(inv, a.T - other.T), s), Mul(a.S, s)};
}

// ---- the model ---------------------------------------------------------------------------------------------------------
struct Skeleton
{
    std::vector<std::wstring> Names;
    std::vector<int> Parents;        // -1: a root; a parent's index is always below its children's (UE's reference skeleton)
    std::vector<float> RefLength;    // the length of each bone's reference-pose translation (its offset from its parent)
    std::vector<V3> RefLocation;     // (3.17.0) each bone's reference-pose place in the component's space (the sync bones'
                                     // start; none: a sync bone starts from its place in the first pose the node sees)

    int Count() const { return static_cast<int>(Names.size()); }
    // Case-insensitive like an FName; the first bone of the name wins. (Indexed on first use: a node looks its bones up
    // every frame.)
    int Find(std::wstring_view name) const
    {
        if (IndexedCount != Names.size())
        {
            Index.clear();
            Index.reserve(Names.size());
            for (size_t i = Names.size(); i-- > 0;) { Index[SkelCompat::FoldedKey(Names[i])] = static_cast<int>(i); }
            IndexedCount = Names.size();
        }
        const auto it = Index.find(SkelCompat::FoldedKey(name));
        return it == Index.end() ? -1 : it->second;
    }

private:
    mutable std::unordered_map<std::wstring, int> Index;
    mutable size_t IndexedCount = static_cast<size_t>(-1);
};

// The bones a node set carried to their children (they keep their local transforms), as the game's pose does after a
// skeletal control: `before` the pose the node read, `pose` the one it wrote (`changed` for its bones; set here for the
// children carried too).
inline void CarryToChildren(const Skeleton& skel, const std::vector<Xf>& before, std::vector<Xf>& pose, std::vector<uint8_t>& changed,
                            const std::vector<uint8_t>& setByNode)
{
    const int n = std::min<int>(skel.Count(), static_cast<int>(pose.size()));
    std::vector<uint8_t> moved(static_cast<size_t>(n), 0);
    for (int b = 0; b < n; ++b)
    {
        if (setByNode[static_cast<size_t>(b)])
        {
            moved[static_cast<size_t>(b)] = 1;
            continue;
        }
        const int p = skel.Parents[static_cast<size_t>(b)];
        if (p < 0 || p >= b || !moved[static_cast<size_t>(p)]) { continue; }
        const Xf local = Relative(before[static_cast<size_t>(b)], before[static_cast<size_t>(p)]);
        pose[static_cast<size_t>(b)] = Multiply(local, pose[static_cast<size_t>(p)]);
        moved[static_cast<size_t>(b)] = 1;
        changed[static_cast<size_t>(b)] = 1;
    }
}

// ---- one node ----------------------------------------------------------------------------------------------------------
class Node
{
public:
    explicit Node(const KawaiiNode& settings) : Cfg(settings)
    {
        DeltaTimeOld = 1.0f / static_cast<float>(Framerate());
        NeedWarmUp = Cfg.NeedWarmUp;
    }

    const KawaiiNode& Settings() const { return Cfg; }

    // (the End editor's live edits) New settings that make the same chains (the caller checks that: the same bones, dummy
    // points, inserted points, space and bone constraints) take effect at the next evaluation without starting the
    // bones again: the physics values, curves, forces, limits and shapes are read from them from then on.
    void Retune(const KawaiiNode& settings)
    {
        Cfg = settings;
        InitPhysicsSettings = false;
        AnimPrepared = static_cast<size_t>(-1);   // (3.15.0) its key animation's tracks found again for the bones
        SyncPrepared = false;                     // (3.17.0) its sync bones' targets found again
    }

    // ETeleportType::ResetPhysics: the bones start again from the pose at the next evaluation
    void ResetPhysics()
    {
        Bones.clear();
        ShapesJumped = true;
        TeleportRequested = false;
        InitPhysicsSettings = false;
        SubstepAccumulator = 0.0f;
        SubstepPoseInitialized = false;
        if (Cfg.UseWarmUpWhenResetDynamics) { NeedWarmUp = true; }
    }

    // ETeleportType::TeleportPhysics: the mesh's move of this frame is not felt (as a move over the teleport threshold)
    void Teleport()
    {
        TeleportRequested = true;
        ShapesJumped = true;
        if (Cfg.UseWarmUpWhenResetDynamics) { NeedWarmUp = true; }
        SubstepAccumulator = 0.0f;
        SubstepPoseInitialized = false;
    }

    // One evaluation: `pose` holds the component-space transform of every bone of the model; the node's bones are written
    // in it and marked in `changed` (their children are not moved: CarryToChildren). `component` is the mesh's world
    // transform, `delta` the game time since the last evaluation (s). `skip` (optional, per bone): bones left out of the
    // chains, with the bones below them (another physics' bones). False when nothing was done (Problem says why).
    bool Evaluate(const Skeleton& skel, std::vector<Xf>& pose, std::vector<uint8_t>& changed, const Xf& component, float delta,
                  const std::vector<uint8_t>* skip = nullptr)
    {
        Problem.clear();
        Skel = &skel;
        Pose = &pose;
        Skip = Cfg.SkipBonamikBones ? skip : nullptr;   // ("skip_bonamik_bones": false keeps them in its chains)
        ComponentToWorld = component;
        DeltaTime = delta;
        if (static_cast<int>(pose.size()) < skel.Count())
        {
            Problem = L"the pose has fewer bones than the model";
            return false;
        }
        const int root = skel.Find(Cfg.RootBone);
        if (root < 0)
        {
            Problem = L"the model has no bone " + Cfg.RootBone;
            return false;
        }
        for (const auto& extra : Cfg.AdditionalRootBones)
        {
            if (skel.Find(extra.Bone) < 0)
            {
                Problem = L"the model has no bone " + extra.Bone;
                return false;
            }
        }
        BaseBone = Cfg.SimulationSpace == KawaiiSpace::BaseBone ? skel.Find(Cfg.SimulationBaseBone) : -1;
        // the simulation space as this evaluation sees it (the base bone's of the frame before kept first)
        if (Cfg.SimulationSpace == KawaiiSpace::BaseBone) { PrevBaseToComponent = HaveSpaceCache ? SimCache.TargetToComponent : BoneCS(BaseBone); }
        SimCache = BuildCache(Cfg.SimulationSpace);
        WorldCache = BuildCache(KawaiiSpace::World);
        HaveSpaceCache = true;
        TeleportPhysics = TeleportRequested;
        TeleportRequested = false;

        if (Bones.empty())
        {
            InitModifyBones();
            InitBoneConstraints();
            PreSkelCompTransform = ComponentToWorld;
            InitPhysicsSettings = false;
            SyncPrepared = false;
            SideKnown.clear();
        }
        if (Bones.empty())
        {
            Problem = L"no bone of the chain from " + Cfg.RootBone + L" is simulated";
            return false;
        }
        if (!InitPhysicsSettings)
        {
            UpdatePhysicsSettingsOfModifyBones();
            InitPhysicsSettings = true;
        }
        // (3.15.0) the node's own animation: its bones' pose turned by its waves and key animation, before the physics
        // pulls the bones toward it
        if (Cfg.Animated())
        {
            AnimTime += static_cast<double>(delta);
            AnimatePose(pose);
        }
        UpdateLimits();
        UpdateModifyBonesPoseTransform();
        // (3.17.0) the sync bones: the chains' pose follows their moves (KawaiiPhysics' ApplySyncBones)
        if (!SyncPrepared) { InitSyncBones(); }
        for (auto& bone : Bones) { bone.UnsyncedPoseLocation = bone.PoseLocation; }
        ApplySyncBones();
        UpdateSkelCompMove();
        if (NeedWarmUp && Cfg.WarmUpFrames > 0)
        {
            WarmUp();
            NeedWarmUp = false;
        }
        if (Cfg.SimulationSpace == KawaiiSpace::World && TeleportPhysics)
        {
            // (a teleport in world space: the bones go along with it, nothing simulated this frame)
            for (auto& bone : Bones)
            {
                const V3 prevCS = InverseTransformPosition(PreSkelCompTransform, bone.PrevLocation);
                bone.Location = ConvertLocationSpace(KawaiiSpace::Component, Cfg.SimulationSpace, prevCS);
                bone.PrevLocation = bone.Location;
            }
            SubstepAccumulator = 0.0f;
            SubstepPoseInitialized = false;
            ConsumeFraction = 1.0f;
            ShapesJumped = true;
        }
        else
        {
            SimulateModifyBones();
        }
        ApplySimulateResult(changed);
        AdvancePreSkelCompTransform(TeleportPhysics);
        TeleportPhysics = false;
        return true;
    }

    std::wstring Problem;
    size_t SimulatedBones() const { return Bones.size(); }
    size_t MergedConstraints() const { return Constraints.size(); }

    // For the End editor's drawing: the simulated bones of the last evaluation (dummies and inserted points too), in the
    // component's space; `Parent` indexes this list.
    struct DebugBone
    {
        V3 Location, PoseLocation;
        float Radius = 0, LimitAngle = 0;
        float LengthRate = 0;   // its place along its chain (0: the root, 1: the end)
        int Parent = -1;
        bool Dummy = false;
    };
    void Debug(std::vector<DebugBone>& out) const
    {
        out.clear();
        out.reserve(Bones.size());
        for (const auto& b : Bones)
        {
            DebugBone d;
            d.Location = ConvertLocationSpace(Cfg.SimulationSpace, KawaiiSpace::Component, b.Location);
            d.PoseLocation = ConvertLocationSpace(Cfg.SimulationSpace, KawaiiSpace::Component, b.PoseLocation);
            d.Radius = b.Radius;
            d.LimitAngle = b.LimitAngle;
            d.LengthRate = b.LengthRateFromRoot;
            d.Parent = b.Parent;
            d.Dummy = b.Dummy || b.MeshIndex < 0;
            out.push_back(d);
        }
    }

private:
    struct Bone
    {
        int MeshIndex = -1;           // the model's bone (-1: a dummy)
        int Index = -1;
        int Parent = -1;
        std::vector<int> Children;
        float Damping = 0, Stiffness = 0, WorldDampingLocation = 0, WorldDampingRotation = 0, Radius = 0, LimitAngle = 0;
        V3 Location, PrevLocation;
        Q4 PrevRotation;
        V3 PoseLocation;
        Q4 PoseRotation;
        V3 PrevPoseLocation;
        V3 StepPoseLocation;          // (fixed substeps) its pose at the last step: a frame with no step carries it from there
        Q4 PrevPoseRotation;
        V3 CurrentPoseLocation;
        Q4 CurrentPoseRotation;
        V3 PoseScale{1, 1, 1};
        V3 UnsyncedPoseLocation;      // (3.17.0) its pose's place before the sync bones moved it (the frame's)
        float BoneLength = 0;
        float LengthFromRoot = 0;
        float LengthRateFromRoot = 0;
        bool Dummy = false;
        bool InterBoneDummy = false;
        int InterBoneRealChild = -1;
        int InterBoneRealParent = -1;
        float InterBoneAlpha = 0;
        bool BridgeDummy = false;
        bool SkipSimulate = false;
        bool HasParent() const { return Parent >= 0; }
    };

    struct Constraint
    {
        int Bone1 = -1, Bone2 = -1;   // indices in Bones
        std::wstring Name1, Name2;
        bool OverrideCompliance = false;
        KawaiiCompliance Compliance = KawaiiCompliance::Leather;
        bool ExcludeFromSubdivision = false;
        float Length = -1.0f;
        bool IsDummy = false;
        float Lambda = 0.0f;
        bool IsValid() const { return Length > 0.0f; }
        bool IsBoneReferenceValid() const { return Bone1 >= 0 && Bone2 >= 0; }
    };

    // a collision shape as it is now (in the simulation space)
    struct Shape
    {
        KawaiiLimit L;
        int Kind = 0;                 // 0 sphere, 1 capsule, 2 tapered capsule, 3 box, 4 plane
        int DrivingBone = -1;
        V3 Location;
        Q4 R;
        bool Enable = true;
        Plane P;                      // planes
        V3 Start, End, Segment, FallbackPushDir, Normal;
        float SegmentSizeSq = 0;
        Xf Box;
        // (3.17.0) where it was at the last frame's end, for its place in each fixed step between that and this frame's
        // (as the bones' pose is): a leg kicking out no longer jumps past the cloth in one step
        V3 PrevLocation, FrameLocation;
        Q4 PrevR, FrameR;
        bool HavePrev = false;
    };

    struct Cache
    {
        Xf ComponentToTarget;         // component -> the space
        Xf TargetToComponent;         // the space -> component
    };

    KawaiiNode Cfg;   // (its own copy: a node outlives nothing it was made from)
    const Skeleton* Skel = nullptr;
    std::vector<Xf>* Pose = nullptr;
    const std::vector<uint8_t>* Skip = nullptr;
    std::vector<Bone> Bones;
    std::vector<Constraint> Constraints;
    std::vector<Shape> Shapes;
    Xf ComponentToWorld;
    Xf PreSkelCompTransform;
    Xf PrevBaseToComponent;
    Cache SimCache, WorldCache;
    bool HaveSpaceCache = false;
    int BaseBone = -1;
    float DeltaTime = 0, DeltaTimeOld = 0, FrameDeltaTime = 0, StepDeltaTime = 0;
    bool InSubstep = false;
    float SubstepAccumulator = 0;
    bool SubstepPoseInitialized = false;
    float ConsumeFraction = 1.0f;
    std::vector<V3> Shown;   // (ApplySimulateResult's: where each bone is shown this frame)
    // (3.15.0) the node's animation: its time (s), and per bone its steps from its root, its chain's number, its key track
    double AnimTime = 0.0;
    std::vector<int> AnimDepth, AnimRoot, AnimTrack, MeshToBone;
    std::vector<Xf> AnimOriginal;
    size_t AnimPrepared = static_cast<size_t>(-1);
    V3 SkelCompMoveVector;
    Q4 SkelCompMoveRotation;
    V3 GravityInSimSpace, SimpleExternalForceInSimSpace;
    bool TeleportPhysics = false, TeleportRequested = false;
    bool NeedWarmUp = false;
    bool InitPhysicsSettings = false;
    std::vector<V3> FeedbackPush;
    std::vector<float> FeedbackWeight;
    // (3.17.0) the sync bones as found on the bones: per sync bone (Cfg.SyncBones' order) the model's bone, its start and
    // its targets (indices in Bones, each with its scale by its place below its target root)
    struct SyncTarget
    {
        int Bone = -1;
        float Scale = 1.0f;
    };
    struct SyncRoot
    {
        SyncTarget Root;
        std::vector<SyncTarget> Children;
    };
    struct SyncFound
    {
        int Mesh = -1;
        V3 Start;
        std::vector<SyncRoot> Roots;
    };
    std::vector<SyncFound> Syncs;
    bool SyncPrepared = false;
    bool ShapesJumped = false;   // (3.17.0) the shapes start again where they are (a reset, a teleport): no sweep from before

    int Framerate() const { return std::max(1, Cfg.TargetFramerate); }
    float StepDt() const { return InSubstep ? StepDeltaTime : DeltaTime; }

    Xf BoneCS(int meshIndex) const
    {
        return meshIndex >= 0 && static_cast<size_t>(meshIndex) < Pose->size() ? (*Pose)[static_cast<size_t>(meshIndex)] : Xf{};
    }

    Cache BuildCache(KawaiiSpace space) const
    {
        Cache c;
        if (space == KawaiiSpace::World)
        {
            c.ComponentToTarget = ComponentToWorld;
            c.TargetToComponent = InverseOf(ComponentToWorld);
        }
        else if (space == KawaiiSpace::BaseBone && BaseBone >= 0)
        {
            c.TargetToComponent = BoneCS(BaseBone);
            c.ComponentToTarget = InverseOf(c.TargetToComponent);
        }
        return c;
    }
    const Cache& CacheFor(KawaiiSpace space) const
    {
        static const Cache component{};
        if (space == KawaiiSpace::Component) { return component; }
        if (space == Cfg.SimulationSpace) { return SimCache; }
        return WorldCache;
    }
    static Xf ConvertTransform(const Cache& from, const Cache& to, const Xf& x) { return Multiply(Multiply(x, from.TargetToComponent), to.ComponentToTarget); }
    static V3 ConvertVector(const Cache& from, const Cache& to, V3 v) { return TransformVector(to.ComponentToTarget, TransformVector(from.TargetToComponent, v)); }
    static V3 ConvertLocation(const Cache& from, const Cache& to, V3 p) { return TransformPosition(to.ComponentToTarget, TransformPosition(from.TargetToComponent, p)); }
    static Q4 ConvertRotation(const Cache& from, const Cache& to, Q4 q) { return TransformRotation(to.ComponentToTarget, TransformRotation(from.TargetToComponent, q)); }
    Xf BoneInSimSpace(int meshIndex) const { return ConvertTransform(Cache{}, SimCache, BoneCS(meshIndex)); }
    V3 ConvertVectorSpace(KawaiiSpace from, KawaiiSpace to, V3 v) const { return from == to ? v : ConvertVector(CacheFor(from), CacheFor(to), v); }
    V3 ConvertLocationSpace(KawaiiSpace from, KawaiiSpace to, V3 p) const { return from == to ? p : ConvertLocation(CacheFor(from), CacheFor(to), p); }
    Q4 ConvertRotationSpace(KawaiiSpace from, KawaiiSpace to, Q4 q) const { return from == to ? q : ConvertRotation(CacheFor(from), CacheFor(to), q); }
    Xf ConvertTransformSpace(KawaiiSpace from, KawaiiSpace to, const Xf& x) const { return from == to ? x : ConvertTransform(CacheFor(from), CacheFor(to), x); }

    V3 BoneForwardVector(Q4 rotation) const
    {
        switch (Cfg.BoneForwardAxis)
        {
        default:
        case KawaiiAxis::XPositive: return AxisX(rotation);
        case KawaiiAxis::XNegative: return -AxisX(rotation);
        case KawaiiAxis::YPositive: return AxisY(rotation);
        case KawaiiAxis::YNegative: return -AxisY(rotation);
        case KawaiiAxis::ZPositive: return AxisZ(rotation);
        case KawaiiAxis::ZNegative: return -AxisZ(rotation);
        }
    }

    // ---- the chains (AnimNode_KawaiiPhysicsModifyBones.cpp) ----
    static bool Lists(const std::vector<std::wstring>& names, std::wstring_view name)
    {
        return std::any_of(names.begin(), names.end(), [&](const std::wstring& n) { return SkelCompat::NameEquals(n, name); });
    }

    void InitModifyBones()
    {
        Bones.clear();
        auto initRoot = [&](const std::wstring& rootName, const std::vector<std::wstring>& excludes) {
            std::vector<Bone> bones;
            AddModifyBone(bones, Skel->Find(rootName), excludes);
            if (bones.empty()) { return; }
            float total = 0.0f;
            CalcBoneLength(bones[0], bones, total);
            const int offset = static_cast<int>(Bones.size());
            for (auto& b : bones)
            {
                if (b.LengthFromRoot > 0.0f) { b.LengthRateFromRoot = b.LengthFromRoot / total; }
                b.Index += offset;
                if (b.Parent >= 0) { b.Parent += offset; }
                for (auto& c : b.Children) { c += offset; }
                if (b.InterBoneRealParent >= 0) { b.InterBoneRealParent += offset; }
                if (b.InterBoneRealChild >= 0) { b.InterBoneRealChild += offset; }
            }
            Bones.insert(Bones.end(), bones.begin(), bones.end());
        };
        initRoot(Cfg.RootBone, Cfg.ExcludeBones);
        for (const auto& extra : Cfg.AdditionalRootBones) { initRoot(extra.Bone, extra.OverrideExcludeBones ? extra.ExcludeBones : Cfg.ExcludeBones); }
    }

    int AddModifyBone(std::vector<Bone>& bones, int meshIndex, const std::vector<std::wstring>& excludes)
    {
        if (meshIndex < 0 || meshIndex >= Skel->Count()) { return -1; }
        if (Lists(excludes, Skel->Names[static_cast<size_t>(meshIndex)])) { return -1; }
        if (Skip && static_cast<size_t>(meshIndex) < Skip->size() && (*Skip)[static_cast<size_t>(meshIndex)]) { return -1; }
        const Xf ref = BoneInSimSpace(meshIndex);
        Bone added;
        added.MeshIndex = meshIndex;
        added.Location = ref.T;
        added.PrevLocation = added.Location;
        added.PoseLocation = added.Location;
        added.PrevRotation = ref.R;
        added.PoseRotation = added.PrevRotation;
        added.PoseScale = ref.S;
        const int index = static_cast<int>(bones.size());
        bones.push_back(added);
        bones[static_cast<size_t>(index)].Index = index;

        bool addedChild = false;
        for (int child = meshIndex + 1; child < Skel->Count(); ++child)
        {
            if (Skel->Parents[static_cast<size_t>(child)] != meshIndex) { continue; }
            std::vector<int> inserted;
            const int effectiveParent = InsertInterBoneDummyBones(bones, index, child, inserted);
            const int childIndex = AddModifyBone(bones, child, excludes);
            if (childIndex >= 0)
            {
                bones[static_cast<size_t>(effectiveParent)].Children.push_back(childIndex);
                bones[static_cast<size_t>(childIndex)].Parent = effectiveParent;
                addedChild = true;
                for (int d : inserted) { bones[static_cast<size_t>(d)].InterBoneRealChild = childIndex; }
            }
            else if (!inserted.empty())
            {
                // (the child is excluded: the dummies put in for it go)
                for (int k = static_cast<int>(inserted.size()) - 1; k >= 0; --k)
                {
                    if (inserted[static_cast<size_t>(k)] == static_cast<int>(bones.size()) - 1) { bones.pop_back(); }
                }
                auto& kids = bones[static_cast<size_t>(index)].Children;
                kids.erase(std::remove_if(kids.begin(), kids.end(), [&](int i) { return std::find(inserted.begin(), inserted.end(), i) != inserted.end(); }), kids.end());
            }
        }
        if (!addedChild && Cfg.DummyBoneLength > 0.0f)
        {
            const Bone self = bones[static_cast<size_t>(index)];
            const V3 tip = self.Location + BoneForwardVector(self.PrevRotation) * Cfg.DummyBoneLength;
            std::vector<int> inserted;
            const int effectiveParent = InsertInterBoneDummyBonesCore(bones, index, tip, self.PrevRotation, ref.S, Cfg.DummyBoneLength, inserted);
            Bone dummy;
            dummy.Dummy = true;
            dummy.Location = tip;
            dummy.PrevLocation = tip;
            dummy.PoseLocation = tip;
            dummy.PrevRotation = self.PrevRotation;
            dummy.PoseRotation = dummy.PrevRotation;
            dummy.PoseScale = ref.S;
            if (!inserted.empty())
            {
                dummy.InterBoneRealParent = index;
                dummy.BoneLength = Cfg.DummyBoneLength / static_cast<float>(inserted.size() + 1);
            }
            const int dummyIndex = static_cast<int>(bones.size());
            bones.push_back(dummy);
            bones[static_cast<size_t>(effectiveParent)].Children.push_back(dummyIndex);
            bones[static_cast<size_t>(dummyIndex)].Index = dummyIndex;
            bones[static_cast<size_t>(dummyIndex)].Parent = effectiveParent;
            for (int d : inserted) { bones[static_cast<size_t>(d)].InterBoneRealChild = dummyIndex; }
        }
        return index;
    }

    int InsertInterBoneDummyBones(std::vector<Bone>& bones, int parentIndex, int childMesh, std::vector<int>& inserted)
    {
        inserted.clear();
        if (Cfg.BoneSubdivisionCount <= 0) { return parentIndex; }
        const Xf child = BoneInSimSpace(childMesh);
        const float distance = Size(child.T - bones[static_cast<size_t>(parentIndex)].Location);
        return InsertInterBoneDummyBonesCore(bones, parentIndex, child.T, child.R, child.S, distance, inserted);
    }

    static int CoverageCount(float distance, float averageRadius)
    {
        if (distance <= KindaSmallNumber || averageRadius <= KindaSmallNumber) { return 0; }
        return std::max(static_cast<int>(std::ceil(distance / (2.0f * averageRadius))) - 1, 0);
    }

    int InsertInterBoneDummyBonesCore(std::vector<Bone>& bones, int parentIndex, V3 childLocation, Q4 childRotation, V3 childScale, float distance,
                                      std::vector<int>& inserted) const
    {
        inserted.clear();
        int effectiveParent = parentIndex;
        if (Cfg.BoneSubdivisionCount <= 0) { return effectiveParent; }
        int count = distance > KindaSmallNumber ? std::clamp(Cfg.BoneSubdivisionCount, 0, 10) : 0;
        if (Cfg.BoneSubdivisionDensifyByRadius && distance > KindaSmallNumber)
        {
            float minScale = std::min(Cfg.RadiusCurve.Eval(0.0f), Cfg.RadiusCurve.Eval(1.0f));
            for (const auto& [t, v] : Cfg.RadiusCurve.Keys)
            {
                if (t >= 0.0f && t <= 1.0f) { minScale = std::min(minScale, v); }
            }
            count = std::max(count, CoverageCount(distance, Cfg.Radius * std::max(minScale, 0.0f)));
        }
        count = std::min(count, 50);
        const V3 parentLocation = bones[static_cast<size_t>(parentIndex)].Location;
        const Q4 parentRotation = bones[static_cast<size_t>(parentIndex)].PrevRotation;
        const V3 parentScale = bones[static_cast<size_t>(parentIndex)].PoseScale;
        for (int j = 0; j < count; ++j)
        {
            const float alpha = static_cast<float>(j + 1) / static_cast<float>(count + 1);
            Bone dummy;
            dummy.Dummy = true;
            dummy.InterBoneDummy = true;
            dummy.InterBoneAlpha = alpha;
            dummy.InterBoneRealParent = parentIndex;
            dummy.Location = Lerp(parentLocation, childLocation, alpha);
            dummy.PrevLocation = dummy.Location;
            dummy.PoseLocation = dummy.Location;
            dummy.PrevRotation = Slerp(parentRotation, childRotation, alpha);
            dummy.PoseRotation = dummy.PrevRotation;
            dummy.PoseScale = Lerp(parentScale, childScale, alpha);
            dummy.BoneLength = distance / static_cast<float>(count + 1);
            const int index = static_cast<int>(bones.size());
            bones.push_back(dummy);
            bones[static_cast<size_t>(index)].Index = index;
            bones[static_cast<size_t>(effectiveParent)].Children.push_back(index);
            bones[static_cast<size_t>(index)].Parent = effectiveParent;
            effectiveParent = index;
            inserted.push_back(index);
        }
        return effectiveParent;
    }

    void CalcBoneLength(Bone& bone, std::vector<Bone>& bones, float& total) const
    {
        if (bone.Parent < 0)
        {
            bone.LengthFromRoot = 0.0f;
            bone.BoneLength = 0.0f;
        }
        else
        {
            const Bone& parent = bones[static_cast<size_t>(bone.Parent)];
            if (!bone.Dummy)
            {
                if (parent.InterBoneDummy) { bone.BoneLength = parent.BoneLength; }
                else
                {
                    bone.BoneLength = bone.MeshIndex >= 0 && static_cast<size_t>(bone.MeshIndex) < Skel->RefLength.size()
                                          ? Skel->RefLength[static_cast<size_t>(bone.MeshIndex)]
                                          : 0.0f;
                }
            }
            else if (!bone.InterBoneDummy)
            {
                if (!parent.InterBoneDummy) { bone.BoneLength = Cfg.DummyBoneLength; }
            }
            bone.LengthFromRoot = parent.LengthFromRoot + bone.BoneLength;
            total = std::max(total, bone.LengthFromRoot);
        }
        for (const int child : bone.Children) { CalcBoneLength(bones[static_cast<size_t>(child)], bones, total); }
    }

    void UpdatePhysicsSettingsOfModifyBones()
    {
        for (auto& bone : Bones)
        {
            const float rate = bone.LengthRateFromRoot;
            bone.Damping = Clamp(Cfg.Damping * Cfg.DampingCurve.Eval(rate), 0.0f, 1.0f);
            bone.WorldDampingLocation = Clamp(Cfg.WorldDampingLocation * Cfg.WorldDampingLocationCurve.Eval(rate), 0.0f, 1.0f);
            bone.WorldDampingRotation = Clamp(Cfg.WorldDampingRotation * Cfg.WorldDampingRotationCurve.Eval(rate), 0.0f, 1.0f);
            bone.Stiffness = Clamp(Cfg.Stiffness * Cfg.StiffnessCurve.Eval(rate), 0.0f, 1.0f);
            bone.Radius = std::max(Cfg.Radius * Cfg.RadiusCurve.Eval(rate), 0.0f);
            const float baseLimit = std::max(Cfg.LimitAngle * Cfg.LimitAngleCurve.Eval(rate), 0.0f);
            bone.LimitAngle = baseLimit > 0.0f ? std::max(baseLimit, KindaSmallNumber) : 0.0f;
        }
    }

    // (3.15.0) The node's bones' places along their chains for the animation: each one's steps from its root (dummies and
    // the points put between bones not counted), its chain's number (root_bone 0, then the additional roots in order),
    // its key animation track, and the model's bones that are the node's.
    void PrepareAnimation()
    {
        const size_t n = Bones.size();
        AnimDepth.assign(n, 0);
        AnimRoot.assign(n, 0);
        AnimTrack.assign(n, -1);
        MeshToBone.assign(static_cast<size_t>(Skel->Count()), -1);
        int roots = 0;
        for (size_t i = 0; i < n; ++i)
        {
            const Bone& b = Bones[i];
            const bool real = b.MeshIndex >= 0 && !b.Dummy && !b.InterBoneDummy && !b.BridgeDummy;
            if (b.Parent < 0)
            {
                AnimRoot[i] = roots++;
                AnimDepth[i] = 0;
            }
            else
            {
                AnimRoot[i] = AnimRoot[static_cast<size_t>(b.Parent)];
                AnimDepth[i] = AnimDepth[static_cast<size_t>(b.Parent)] + (real ? 1 : 0);
            }
            if (real && b.MeshIndex < Skel->Count()) { MeshToBone[static_cast<size_t>(b.MeshIndex)] = static_cast<int>(i); }
        }
        if (const auto& tracks = Cfg.PoseAnimation.Tracks)
        {
            for (size_t i = 0; i < n; ++i)
            {
                const int mesh = Bones[i].MeshIndex;
                if (mesh < 0 || Bones[i].Dummy) { continue; }
                for (size_t t = 0; t < tracks->size(); ++t)
                {
                    if (SkelCompat::NameEquals((*tracks)[t].Bone, Skel->Names[static_cast<size_t>(mesh)]))
                    {
                        AnimTrack[i] = static_cast<int>(t);
                        break;
                    }
                }
            }
        }
        AnimPrepared = n;
    }

    // (3.15.0) A key animation track's rotation at `frame` (looping, between its two nearest keys).
    Q4 KeyRotation(const SkelCompat::KawaiiKeyTrack& track, double frame) const
    {
        const auto& keys = track.Keys;
        const auto at = [&](size_t k) { return Q4{keys[k][0], keys[k][1], keys[k][2], keys[k][3]}; };
        if (keys.size() == 1) { return at(0); }
        const double count = static_cast<double>(keys.size());
        double f = std::fmod(frame, count);
        if (f < 0.0) { f += count; }
        const size_t k0 = static_cast<size_t>(f) % keys.size();
        const size_t k1 = (k0 + 1) % keys.size();
        return Slerp(at(k0), at(k1), static_cast<float>(f - std::floor(f)));
    }

    // (3.15.0) The node's bones' pose turned by its animation, parents first: each bone's local transform as the pose has
    // it (under its parent as the pose had that), its key animation applied and its waves' turns added (about the
    // model's axes at the bone), put under its parent as that is now (turned already when it is one of the node's).
    void AnimatePose(std::vector<Xf>& pose)
    {
        if (AnimPrepared != Bones.size() || MeshToBone.size() != static_cast<size_t>(Skel->Count())) { PrepareAnimation(); }
        AnimOriginal.resize(Bones.size());
        for (size_t i = 0; i < Bones.size(); ++i)
        {
            const int mesh = Bones[i].MeshIndex;
            if (mesh >= 0 && !Bones[i].Dummy) { AnimOriginal[i] = pose[static_cast<size_t>(mesh)]; }
        }
        const auto& anim = Cfg.PoseAnimation;
        const bool keyed = anim.Active();
        const double frame = AnimTime * static_cast<double>(anim.Fps) * static_cast<double>(anim.Speed);
        for (size_t i = 0; i < Bones.size(); ++i)
        {
            const Bone& bone = Bones[i];
            const int mesh = bone.MeshIndex;
            if (mesh < 0 || bone.Dummy || bone.BridgeDummy || bone.InterBoneDummy) { continue; }
            const int parent = Skel->Parents[static_cast<size_t>(mesh)];
            Xf local = AnimOriginal[i];
            if (parent >= 0)
            {
                const int pb = MeshToBone[static_cast<size_t>(parent)];
                const Xf& parentBefore = pb >= 0 ? AnimOriginal[static_cast<size_t>(pb)] : pose[static_cast<size_t>(parent)];
                local = Relative(AnimOriginal[i], parentBefore);
            }
            if (keyed && AnimTrack[i] >= 0)
            {
                const auto& track = (*anim.Tracks)[static_cast<size_t>(AnimTrack[i])];
                const Q4 key = KeyRotation(track, frame);
                if (anim.Additive)
                {
                    const Q4 first{track.Keys[0][0], track.Keys[0][1], track.Keys[0][2], track.Keys[0][3]};
                    const Q4 turn = Normalized(Inverse(first) * key);
                    local.R = Normalized(local.R * (anim.Weight >= 1.0f ? turn : Slerp(Q4{0, 0, 0, 1}, turn, anim.Weight)));
                }
                else
                {
                    local.R = anim.Weight >= 1.0f ? key : Normalized(Slerp(local.R, key, anim.Weight));
                }
            }
            for (const auto& w : Cfg.PoseWaves)
            {
                const float part = w.DegreesCurve.Empty() ? 1.0f : w.DegreesCurve.Eval(bone.LengthRateFromRoot);
                const size_t chain = static_cast<size_t>(AnimRoot[i]);
                const double phase = 360.0 * AnimTime / static_cast<double>(w.Seconds) + w.Phase - w.PhasePerBone * AnimDepth[i] - w.PhasePerRoot * AnimRoot[i] -
                                     (chain < w.RootPhases.size() ? w.RootPhases[chain] : 0.0f);
                const float degrees = w.Degrees * part * static_cast<float>(std::sin(phase * (static_cast<double>(Pi) / 180.0)));
                if (degrees == 0.0f) { continue; }
                V3 axis{w.Axis[0], w.Axis[1], w.Axis[2]};
                if (!w.LocalAxis) { axis = Unrotate(AnimOriginal[i].R, axis); }   // (the model's axis, in the bone's own space)
                local.R = Normalized(local.R * FromAxisAngle(SafeNormal(axis), DegreesToRadians(degrees)));
            }
            pose[static_cast<size_t>(mesh)] = parent >= 0 ? Multiply(local, pose[static_cast<size_t>(parent)]) : local;
        }
    }

    void UpdateModifyBonesPoseTransform()
    {
        for (auto& bone : Bones)
        {
            if (bone.BridgeDummy || bone.InterBoneDummy) { continue; }
            if (bone.Dummy)
            {
                const int ancestor = bone.InterBoneRealParent >= 0 ? bone.InterBoneRealParent : bone.Parent;
                if (ancestor < 0) { continue; }
                const Bone& real = Bones[static_cast<size_t>(ancestor)];
                bone.PoseLocation = real.PoseLocation + BoneForwardVector(real.PoseRotation) * Cfg.DummyBoneLength;
                bone.PoseRotation = real.PoseRotation;
                bone.PoseScale = real.PoseScale;
                continue;
            }
            const Xf x = BoneInSimSpace(bone.MeshIndex);
            bone.PoseLocation = x.T;
            bone.PoseRotation = x.R;
            bone.PoseScale = x.S;
        }
        for (auto& bone : Bones)
        {
            if (!bone.InterBoneDummy || bone.InterBoneRealParent < 0 || bone.InterBoneRealChild < 0) { continue; }
            const Bone& realParent = Bones[static_cast<size_t>(bone.InterBoneRealParent)];
            const Bone& realChild = Bones[static_cast<size_t>(bone.InterBoneRealChild)];
            bone.PoseLocation = Lerp(realParent.PoseLocation, realChild.PoseLocation, bone.InterBoneAlpha);
            bone.PoseRotation = Slerp(realParent.PoseRotation, realChild.PoseRotation, bone.InterBoneAlpha);
            bone.PoseScale = Lerp(realParent.PoseScale, realChild.PoseScale, bone.InterBoneAlpha);
        }
    }

    // ---- sync bones (AnimNode_KawaiiPhysicsSyncBone.cpp, KawaiiPhysicsSyncBone.cpp) ----
    void InitSyncBones()
    {
        Syncs.clear();
        Syncs.resize(Cfg.SyncBones.size());
        for (size_t s = 0; s < Cfg.SyncBones.size(); ++s)
        {
            const KawaiiSyncBone& sync = Cfg.SyncBones[s];
            SyncFound& found = Syncs[s];
            found.Mesh = Skel->Find(sync.Bone);
            if (found.Mesh < 0) { continue; }   // (KawaiiPhysics: its start zero, and it is skipped)
            found.Start = static_cast<size_t>(found.Mesh) < Skel->RefLocation.size() ? Skel->RefLocation[static_cast<size_t>(found.Mesh)] : BoneCS(found.Mesh).T;
            for (const KawaiiSyncTarget& target : sync.Targets)
            {
                const int mesh = Skel->Find(target.Bone);
                if (mesh < 0) { continue; }   // (KawaiiPhysics leaves out a target root the model lacks)
                SyncRoot root;
                for (size_t i = 0; i < Bones.size(); ++i)
                {
                    if (Bones[i].MeshIndex == mesh && !Bones[i].Dummy)
                    {
                        root.Root.Bone = static_cast<int>(i);
                        break;
                    }
                }
                if (root.Root.Bone >= 0 && target.IncludeChildBones) { CollectSyncChildTargets(root, target.ScaleCurve); }
                found.Roots.push_back(std::move(root));
            }
        }
        SyncPrepared = true;
    }

    // CollectSyncBoneChildTargets: the bones below a target root (the points put between bones and the end points past
    // them left out: placed again after the sync), parents first, each with its place below the root (by the length from
    // the chain's root) and the scale its curve gives there.
    void CollectSyncChildTargets(SyncRoot& root, const KawaiiCurve& curve)
    {
        root.Children.clear();
        const float start = Bones[static_cast<size_t>(root.Root.Bone)].LengthFromRoot;
        float longest = start;
        std::vector<int> stack = Bones[static_cast<size_t>(root.Root.Bone)].Children;
        while (!stack.empty())
        {
            const int i = stack.back();
            stack.pop_back();
            if (i < 0 || static_cast<size_t>(i) >= Bones.size()) { continue; }
            const Bone& b = Bones[static_cast<size_t>(i)];
            const bool hidden = b.InterBoneDummy || (b.Dummy && b.InterBoneRealParent >= 0);
            if (!hidden && std::none_of(root.Children.begin(), root.Children.end(), [&](const SyncTarget& t) { return t.Bone == i; }))
            {
                root.Children.push_back(SyncTarget{i, 1.0f});
                longest = std::max(longest, b.LengthFromRoot);
            }
            stack.insert(stack.end(), b.Children.begin(), b.Children.end());
        }
        if (curve.Empty()) { return; }
        const float range = longest - start;
        root.Root.Scale = curve.Eval(0.0f);
        for (auto& t : root.Children)
        {
            const float rate = range > KindaSmallNumber ? (Bones[static_cast<size_t>(t.Bone)].LengthFromRoot - start) / range : 0.0f;
            t.Scale = curve.Eval(rate);
        }
    }

    // FKawaiiPhysicsSyncTarget::Apply: the target's pose moved, kept at its length from its parent (from the real parent
    // when the parent is a point put between them, whose own place comes after)
    void ApplySyncTarget(const SyncTarget& target, V3 translation)
    {
        if (target.Bone < 0 || static_cast<size_t>(target.Bone) >= Bones.size()) { return; }
        Bone& bone = Bones[static_cast<size_t>(target.Bone)];
        // (a chain's root follows its animation: KawaiiPhysics skips it too once it has simulated a frame, its roots
        // marked then; on its first frame it moved the root, which jumped for that frame)
        if (bone.SkipSimulate || bone.Parent < 0 || static_cast<size_t>(bone.Parent) >= Bones.size()) { return; }
        const V3 scaled = translation * target.Scale;
        const Bone& parent = Bones[static_cast<size_t>(bone.Parent)];
        const V3 moved = bone.PoseLocation + scaled;
        if (parent.InterBoneDummy)
        {
            const float oneMinusAlpha = 1.0f - parent.InterBoneAlpha;
            const int grand = parent.InterBoneRealParent;
            if (oneMinusAlpha > KindaSmallNumber && grand >= 0 && static_cast<size_t>(grand) < Bones.size())
            {
                const Bone& g = Bones[static_cast<size_t>(grand)];
                const float length = bone.BoneLength / oneMinusAlpha;
                V3 dir = SafeNormal(moved - g.PoseLocation);
                if (NearlyZero(dir)) { dir = SafeNormal(bone.PoseLocation - g.PoseLocation); }
                bone.PoseLocation = NearlyZero(dir) ? moved : dir * length + g.PoseLocation;
            }
            else { bone.PoseLocation = moved; }
            return;
        }
        V3 dir = SafeNormal(moved - parent.PoseLocation);
        if (NearlyZero(dir)) { dir = SafeNormal(bone.PoseLocation - parent.PoseLocation); }
        bone.PoseLocation = NearlyZero(dir) ? moved : dir * bone.BoneLength + parent.PoseLocation;
    }

    void ApplySyncBones()
    {
        if (Cfg.SyncBones.empty() || Syncs.size() != Cfg.SyncBones.size()) { return; }
        for (size_t s = 0; s < Syncs.size(); ++s)
        {
            const KawaiiSyncBone& sync = Cfg.SyncBones[s];
            const SyncFound& found = Syncs[s];
            if (found.Mesh < 0) { continue; }
            const V3 here = BoneCS(found.Mesh).T;
            V3 delta = here - found.Start;
            if (!sync.ScaleCurveByDeltaDistance.Empty()) { delta *= sync.ScaleCurveByDeltaDistance.Eval(Size(delta)); }
            delta = Mul(delta, V3{sync.GlobalScale[0], sync.GlobalScale[1], sync.GlobalScale[2]});
            const auto passes = [](float v, KawaiiSyncDirection d) {
                return d == KawaiiSyncDirection::Both || (d == KawaiiSyncDirection::Positive && v > 0.0f) || (d == KawaiiSyncDirection::Negative && v < 0.0f);
            };
            V3 filtered{passes(delta.X, sync.Direction[0]) ? delta.X : 0.0f, passes(delta.Y, sync.Direction[1]) ? delta.Y : 0.0f,
                        passes(delta.Z, sync.Direction[2]) ? delta.Z : 0.0f};
            if (NearlyZero(filtered)) { continue; }
            filtered = ConvertVectorSpace(KawaiiSpace::Component, Cfg.SimulationSpace, filtered);
            const V3 syncInSim = ConvertLocationSpace(KawaiiSpace::Component, Cfg.SimulationSpace, here);
            const auto attenuation = [&](float distance) {
                if (!sync.DistanceAttenuation) { return 1.0f; }
                const float inner = sync.AttenuationInnerRadius;
                const float outer = std::max(sync.AttenuationOuterRadius, inner);
                float amount;
                if (distance <= inner) { amount = 0.0f; }
                else if (distance >= outer) { amount = sync.MaxAttenuationRate; }
                else
                {
                    const float span = outer - inner;
                    amount = (span > KindaSmallNumber ? (distance - inner) / span : 1.0f) * sync.MaxAttenuationRate;
                }
                return std::max(0.0f, 1.0f - amount);
            };
            const auto apply = [&](const SyncTarget& t) {
                if (t.Bone >= 0 && static_cast<size_t>(t.Bone) < Bones.size())
                {
                    ApplySyncTarget(t, filtered * attenuation(Size(syncInSim - Bones[static_cast<size_t>(t.Bone)].Location)));
                }
            };
            for (const SyncRoot& root : found.Roots)
            {
                apply(root.Root);
                for (const SyncTarget& t : root.Children) { apply(t); }
            }
        }
        UpdateSubdivisionDummyPoseAfterSyncBones();
    }

    // the end points put past bones subdivided (from their real bone), then the points between bones (between their two
    // ends as the sync left them)
    void UpdateSubdivisionDummyPoseAfterSyncBones()
    {
        for (auto& bone : Bones)
        {
            if (!bone.Dummy || bone.InterBoneDummy || bone.InterBoneRealParent < 0) { continue; }
            const Bone& real = Bones[static_cast<size_t>(bone.InterBoneRealParent)];
            bone.PoseLocation = real.PoseLocation + BoneForwardVector(real.PoseRotation) * Cfg.DummyBoneLength;
            bone.PoseRotation = real.PoseRotation;
            bone.PoseScale = real.PoseScale;
        }
        for (auto& bone : Bones)
        {
            if (!bone.InterBoneDummy || bone.InterBoneRealParent < 0 || bone.InterBoneRealChild < 0) { continue; }
            const Bone& realParent = Bones[static_cast<size_t>(bone.InterBoneRealParent)];
            const Bone& realChild = Bones[static_cast<size_t>(bone.InterBoneRealChild)];
            bone.PoseLocation = Lerp(realParent.PoseLocation, realChild.PoseLocation, bone.InterBoneAlpha);
            bone.PoseRotation = Slerp(realParent.PoseRotation, realChild.PoseRotation, bone.InterBoneAlpha);
            bone.PoseScale = Lerp(realParent.PoseScale, realChild.PoseScale, bone.InterBoneAlpha);
        }
    }

    void UpdateSkelCompMove()
    {
        SkelCompMoveVector = InverseTransformPosition(ComponentToWorld, PreSkelCompTransform.T);
        SkelCompMoveVector = Mul(SkelCompMoveVector, {Cfg.SkelCompMoveScale[0], Cfg.SkelCompMoveScale[1], Cfg.SkelCompMoveScale[2]});
        SkelCompMoveRotation = InverseTransformRotation(ComponentToWorld, PreSkelCompTransform.R);
        if (Cfg.TeleportDistanceThreshold > 0.0f && SizeSq(SkelCompMoveVector) > Cfg.TeleportDistanceThreshold * Cfg.TeleportDistanceThreshold)
        {
            TeleportPhysics = true;
        }
        if (Cfg.TeleportRotationThreshold > 0.0f && RadiansToDegrees(Angle(SkelCompMoveRotation)) > Cfg.TeleportRotationThreshold) { TeleportPhysics = true; }
    }

    void AdvancePreSkelCompTransform(bool teleported)
    {
        if (teleported) { ConsumeFraction = 1.0f; }
        const float fraction = Clamp(ConsumeFraction, 0.0f, 1.0f);
        if (fraction >= 1.0f - KindaSmallNumber)
        {
            PreSkelCompTransform = ComponentToWorld;
            return;
        }
        PreSkelCompTransform.T = Lerp(PreSkelCompTransform.T, ComponentToWorld.T, fraction);
        PreSkelCompTransform.R = Slerp(PreSkelCompTransform.R, ComponentToWorld.R, fraction);
        PreSkelCompTransform.S = Lerp(PreSkelCompTransform.S, ComponentToWorld.S, fraction);
    }

    // ---- collision shapes (AnimNode_KawaiiPhysicsCollision.cpp) ----
    void UpdateLimits()
    {
        if (Shapes.empty())
        {
            const std::pair<const std::vector<KawaiiLimit>*, int> lists[] = {{&Cfg.Spheres, 0}, {&Cfg.Capsules, 1}, {&Cfg.TaperedCapsules, 2}, {&Cfg.Boxes, 3}, {&Cfg.Planes, 4}};
            for (const auto& [list, kind] : lists)
            {
                for (const auto& limit : *list)
                {
                    Shape s;
                    s.L = limit;
                    s.Kind = kind;
                    s.DrivingBone = limit.Bone.empty() ? -1 : Skel->Find(limit.Bone);
                    Shapes.push_back(s);
                }
            }
        }
        for (auto& s : Shapes)
        {
            const KawaiiLimit& l = s.L;
            const Q4 offsetRotation = FromRotator(l.Rotation[0], l.Rotation[1], l.Rotation[2]);
            const V3 offset{l.Offset[0], l.Offset[1], l.Offset[2]};
            if (s.DrivingBone >= 0)
            {
                // (the offset in the bone's space: ConvertCSTransformToBoneSpace / ConvertBoneSpaceTransformToCS)
                const Xf bone = BoneCS(s.DrivingBone);
                const Xf local{offsetRotation, offset, {1, 1, 1}};
                const Xf placed = ConvertTransformSpace(KawaiiSpace::Component, Cfg.SimulationSpace, Multiply(local, bone));
                s.Location = placed.T;
                s.R = placed.R;
                if (s.Kind == 4)
                {
                    s.R = Normalized(s.R);
                    s.P = Plane::Through(s.Location, AxisZ(s.R));
                }
                s.Enable = true;
            }
            else if (s.Kind == 4 && l.Bone.empty())
            {
                // (a floor: in the component's space)
                const Xf placed = ConvertTransformSpace(KawaiiSpace::Component, Cfg.SimulationSpace, Xf{offsetRotation, offset, {1, 1, 1}});
                s.Location = placed.T;
                s.R = Normalized(placed.R);
                s.P = Plane::Through(s.Location, AxisZ(s.R));
                s.Enable = true;
            }
            else
            {
                s.Enable = false;
            }
            if (!s.HavePrev || ShapesJumped)
            {
                s.PrevLocation = s.Location;
                s.PrevR = s.R;
                s.HavePrev = true;
            }
        }
        if (ShapesJumped) { std::fill(SideKnown.begin(), SideKnown.end(), static_cast<uint8_t>(0)); }
        ShapesJumped = false;
    }

    // (3.17.0) the shapes at `alpha` of the way from the last frame's end to this frame's (a fixed step's)
    void PlaceShapesBetween(float alpha)
    {
        for (auto& s : Shapes)
        {
            if (!s.Enable) { continue; }
            s.Location = Lerp(s.PrevLocation, s.FrameLocation, alpha);
            s.R = Normalized(Slerp(s.PrevR, s.FrameR, alpha));
            if (s.Kind == 4) { s.P = Plane::Through(s.Location, AxisZ(s.R)); }
        }
    }

    void PrepareCollisionShapeCaches()
    {
        for (auto& s : Shapes)
        {
            if (!s.Enable) { continue; }
            const KawaiiLimit& l = s.L;
            switch (s.Kind)
            {
            case 1:
                s.Start = s.Location + AxisZ(s.R) * (l.Length * 0.5f);
                s.End = s.Location + AxisZ(s.R) * (l.Length * -0.5f);
                s.FallbackPushDir = AxisX(s.R);
                break;
            case 2:
            {
                const V3 axis = AxisZ(s.R);
                s.Start = s.Location + axis * (l.Length * 0.5f);
                s.End = s.Location - axis * (l.Length * 0.5f);
                s.Segment = s.End - s.Start;
                s.SegmentSizeSq = SizeSq(s.Segment);
                s.FallbackPushDir = AxisX(s.R);
                break;
            }
            case 3: s.Box = Xf{s.R, s.Location, {1, 1, 1}}; break;
            case 4: s.Normal = AxisZ(s.R); break;
            default: break;
            }
        }
    }

    // (3.17.0) The side of each shape each bone was on ("keep_collision_side"): per bone and shape, the direction from the
    // shape (its axis for a capsule, its middle for a sphere or a box) to the bone in the shape's own space, while the
    // bone is near it. A bone found inside a shape on the other side of its axis than that (the shape moved past it in a
    // step: a kicking leg past the cloth) is put back out on the side it was on, not pushed on through.
    std::vector<V3> SideDir;
    std::vector<uint8_t> SideKnown;

    // `push` (world): the way out of the shape for a bone found inside it; turned to the side the bone was on when that
    // is the other way. Its side remembered for the next step when near.
    V3 KeptSide(size_t memory, const Shape& s, V3 push) const
    {
        if (!Cfg.KeepCollisionSide || memory >= SideKnown.size() || !SideKnown[memory]) { return push; }
        const V3 was = Rotate(s.R, SideDir[memory]);
        return Dot(push, was) < 0.0f || NearlyZero(push) ? was : push;
    }
    void RememberSide(size_t memory, const Shape& s, V3 away, float distance, float limit)
    {
        if (!Cfg.KeepCollisionSide || memory >= SideKnown.size()) { return; }
        const V3 dir = SafeNormal(away);
        if (distance < limit + std::max(3.0f, 0.5f * limit) && !NearlyZero(dir))
        {
            SideDir[memory] = Unrotate(s.R, dir);
            SideKnown[memory] = 1;
        }
        else { SideKnown[memory] = 0; }
    }

    void AdjustByCollisions(Bone& bone, size_t boneIndex)
    {
        if (Cfg.KeepCollisionSide && SideKnown.size() != Bones.size() * Shapes.size())
        {
            SideDir.assign(Bones.size() * Shapes.size(), V3{});
            SideKnown.assign(Bones.size() * Shapes.size(), 0);
        }
        for (size_t k = 0; k < Shapes.size(); ++k)
        {
            const Shape& s = Shapes[k];
            if (!s.Enable) { continue; }
            const size_t memory = boneIndex * Shapes.size() + k;
            const KawaiiLimit& l = s.L;
            switch (s.Kind)
            {
            case 0:
            {
                if (l.Radius <= 0.0f) { break; }
                const V3 delta = bone.Location - s.Location;
                const float distSq = SizeSq(delta);
                if (!l.Inner)
                {
                    const float limit = l.Radius + bone.Radius;
                    if (distSq <= limit * limit)
                    {
                        const float dist = std::sqrt(distSq);
                        const V3 out = KeptSide(memory, s, dist > KindaSmallNumber ? delta / dist : V3{});
                        if (!NearlyZero(out)) { bone.Location = s.Location + out * limit; }
                    }
                    RememberSide(memory, s, bone.Location - s.Location, Size(bone.Location - s.Location), limit);
                }
                else
                {
                    const float limit = std::max(l.Radius - bone.Radius, 0.0f);
                    if (distSq < limit * limit) { break; }
                    const float dist = std::sqrt(distSq);
                    bone.Location = dist > KindaSmallNumber ? s.Location + (delta / dist) * limit : s.Location;
                }
                break;
            }
            case 1:
            {
                if (l.Radius <= 0.0f || l.Length <= 0.0f) { break; }
                const float distSq = PointDistToSegmentSquared(bone.Location, s.Start, s.End);
                const float limit = bone.Radius + l.Radius;
                V3 closest = ClosestPointOnSegment(bone.Location, s.Start, s.End);
                if (distSq < limit * limit)
                {
                    V3 push = SafeNormal(bone.Location - closest);
                    if (NearlyZero(push)) { push = s.FallbackPushDir; }
                    bone.Location = closest + KeptSide(memory, s, push) * limit;
                    closest = ClosestPointOnSegment(bone.Location, s.Start, s.End);
                }
                RememberSide(memory, s, bone.Location - closest, Size(bone.Location - closest), limit);
                break;
            }
            case 2:
            {
                if (l.Radius0 <= 0.0f && l.Radius1 <= 0.0f) { break; }
                const float r0 = std::max(l.Radius0, 0.0f), r1 = std::max(l.Radius1, 0.0f), length = std::max(l.Length, 0.0f);
                V3 closest = s.Location;
                float radius = std::max(r0, r1);
                if (length <= std::fabs(r0 - r1) + KindaSmallNumber)
                {
                    closest = s.Location + AxisZ(s.R) * (length * 0.5f * (r0 >= r1 ? 1.0f : -1.0f));   // (one end sphere holds the other)
                }
                else
                {
                    const float t = Clamp(Dot(bone.Location - s.Start, s.Segment) / s.SegmentSizeSq, 0.0f, 1.0f);
                    closest = s.Start + s.Segment * t;
                    radius = std::max(Lerp(l.Radius0, l.Radius1, t), 0.0f);
                }
                const float limit = bone.Radius + radius;
                if (SizeSq(bone.Location - closest) < limit * limit)
                {
                    V3 push = SafeNormal(bone.Location - closest);
                    if (NearlyZero(push)) { push = s.FallbackPushDir; }
                    bone.Location = closest + KeptSide(memory, s, push) * limit;
                }
                RememberSide(memory, s, bone.Location - closest, Size(bone.Location - closest), limit);
                break;
            }
            case 3:
            {
                const float radius = bone.Radius;
                const V3 local = InverseTransformPosition(s.Box, bone.Location);
                const V3 extent{l.Extent[0], l.Extent[1], l.Extent[2]};
                // FMath::SphereAABBIntersection
                float distSq = 0.0f;
                for (int a = 0; a < 3; ++a)
                {
                    if (local[a] < -extent[a]) { distSq += (local[a] + extent[a]) * (local[a] + extent[a]); }
                    else if (local[a] > extent[a]) { distSq += (local[a] - extent[a]) * (local[a] - extent[a]); }
                }
                const float boxSize = std::max(extent.X, std::max(extent.Y, extent.Z));
                if (distSq > radius * radius)
                {
                    // (its side remembered: the box's middle to it, in the box's space, near it)
                    RememberSide(memory, s, TransformVector(s.Box, local), std::sqrt(distSq) + boxSize, boxSize + radius);
                    break;
                }
                V3 closest = local;
                for (int a = 0; a < 3; ++a) { closest[a] = Clamp(closest[a], -extent[a], extent[a]); }
                const V3 pushOut = local - closest;
                const float distance = Size(pushOut);
                const bool inside = (local.X >= -extent.X && local.X <= extent.X && local.Y >= -extent.Y && local.Y <= extent.Y && local.Z >= -extent.Z &&
                                     local.Z <= extent.Z) ||
                                    distance <= KindaSmallNumber;
                if (inside)
                {
                    const V3 penetration = extent - Abs(local);
                    int axis = 2;
                    if (penetration.X <= penetration.Y && penetration.X <= penetration.Z) { axis = 0; }
                    else if (penetration.Y <= penetration.Z) { axis = 1; }
                    float sign = local[axis] >= 0.0f ? 1.0f : -1.0f;
                    if (Cfg.KeepCollisionSide && memory < SideKnown.size() && SideKnown[memory] && Dot(local, SideDir[memory]) < 0.0f)
                    {
                        // (it came through from the other side: out of the face it was beyond)
                        const V3 was = SideDir[memory];
                        axis = std::fabs(was.X) >= std::fabs(was.Y) && std::fabs(was.X) >= std::fabs(was.Z) ? 0 : (std::fabs(was.Y) >= std::fabs(was.Z) ? 1 : 2);
                        sign = was[axis] >= 0.0f ? 1.0f : -1.0f;
                    }
                    V3 moved = local;
                    moved[axis] = sign * (extent[axis] + radius);
                    bone.Location = TransformPosition(s.Box, moved);
                    RememberSide(memory, s, TransformVector(s.Box, moved), 0.0f, boxSize + radius);
                    break;
                }
                if (distance <= radius) { bone.Location = TransformPosition(s.Box, closest + SafeNormal(pushOut) * radius); }
                RememberSide(memory, s, TransformVector(s.Box, InverseTransformPosition(s.Box, bone.Location)), 0.0f, boxSize + radius);
                break;
            }
            case 4:
            {
                const V3 onPlane = PointPlaneProject(bone.Location, s.P);
                const float distSq = SizeSq(bone.Location - onPlane);
                V3 crossing;
                if (distSq < bone.Radius * bone.Radius || SegmentPlaneIntersection(bone.Location, bone.PrevLocation, s.P, crossing))
                {
                    bone.Location = onPlane + s.Normal * bone.Radius;
                }
                break;
            }
            default: break;
            }
        }
    }

    void AdjustByAngleLimit(Bone& bone, const Bone& parent) const
    {
        if (bone.LimitAngle == 0.0f) { return; }
        V3 boneDir = SafeNormal(bone.Location - parent.Location);
        const V3 poseDir = SafeNormal(bone.PoseLocation - parent.PoseLocation);
        const V3 axis = Cross(poseDir, boneDir);
        const float angle = std::atan2(Size(axis), Dot(poseDir, boneDir));
        const float over = RadiansToDegrees(angle) - bone.LimitAngle;
        if (over > 0.0f)
        {
            V3 rotationAxis = SafeNormal(axis);
            if (NearlyZero(rotationAxis)) { rotationAxis = AxisX(parent.PoseRotation); }
            boneDir = RotateAngleAxis(boneDir, -over, rotationAxis);
            bone.Location = boneDir * Size(bone.Location - parent.Location) + parent.Location;
        }
    }

    void AdjustByPlanarConstraint(Bone& bone, const Bone& parent) const
    {
        if (Cfg.PlanarConstraint == KawaiiPlanar::None) { return; }
        V3 normal = Cfg.PlanarConstraint == KawaiiPlanar::X ? AxisX(parent.PoseRotation)
                    : Cfg.PlanarConstraint == KawaiiPlanar::Y ? AxisY(parent.PoseRotation)
                                                              : AxisZ(parent.PoseRotation);
        bone.Location = PointPlaneProject(bone.Location, Plane::Through(parent.Location, normal));
    }

    // ---- bone constraints (XPBD) ----
    static float ComplianceOf(KawaiiCompliance c)
    {
        static constexpr float values[] = {0.00000000004f, 0.00000000016f, 0.000000001f, 0.000000002f, 0.0000001f, 0.00002f, 0.0001f};
        return values[std::clamp(static_cast<int>(c), 0, 6)];
    }

    void AdjustByBoneConstraints()
    {
        for (auto& c : Constraints)
        {
            if (!c.IsValid() || c.Bone1 < 0 || c.Bone2 < 0 || c.Bone1 >= static_cast<int>(Bones.size()) || c.Bone2 >= static_cast<int>(Bones.size())) { continue; }
            Bone& b1 = Bones[static_cast<size_t>(c.Bone1)];
            Bone& b2 = Bones[static_cast<size_t>(c.Bone2)];
            V3 delta = b2.Location - b1.Location;
            const float length = Size(delta);
            if (length <= 0.0f) { continue; }
            const float constraint = length - c.Length;
            float compliance = ComplianceOf(c.OverrideCompliance ? c.Compliance : Cfg.BoneConstraintGlobalCompliance);
            const float dt = std::max(StepDt(), KindaSmallNumber);
            compliance /= dt * dt;
            const float deltaLambda = (constraint - compliance * c.Lambda) / (2.0f + compliance);
            delta = (delta / length) * deltaLambda;
            b1.Location += delta;
            b2.Location -= delta;
            c.Lambda += deltaLambda;
        }
    }

    int BoneByName(const std::wstring& name) const
    {
        for (size_t i = 0; i < Bones.size(); ++i)
        {
            if (Bones[i].MeshIndex >= 0 && SkelCompat::NameEquals(Skel->Names[static_cast<size_t>(Bones[i].MeshIndex)], name)) { return static_cast<int>(i); }
        }
        return -1;
    }

    void InitBoneConstraints()
    {
        Constraints.clear();
        for (const auto& c : Cfg.BoneConstraints)
        {
            Constraint one;
            one.Name1 = c.Bone1;
            one.Name2 = c.Bone2;
            one.OverrideCompliance = c.OverrideCompliance;
            one.Compliance = c.Compliance;
            one.ExcludeFromSubdivision = c.ExcludeFromSubdivision;
            Constraints.push_back(one);
        }
        std::vector<Constraint> dummies;
        for (auto& c : Constraints)
        {
            c.Bone1 = BoneByName(c.Name1);
            if (c.Bone1 < 0) { continue; }
            c.Bone2 = BoneByName(c.Name2);
            if (c.Bone2 < 0) { continue; }
            c.Length = Size(Bones[static_cast<size_t>(c.Bone1)].Location - Bones[static_cast<size_t>(c.Bone2)].Location);
            if (!Cfg.AutoAddChildDummyBoneConstraint) { continue; }
            auto tipDummy = [&](int b) {
                for (int i : Bones[static_cast<size_t>(b)].Children)
                {
                    if (i >= 0 && Bones[static_cast<size_t>(i)].Dummy && !Bones[static_cast<size_t>(i)].InterBoneDummy) { return i; }
                }
                return -1;
            };
            const int d1 = tipDummy(c.Bone1), d2 = tipDummy(c.Bone2);
            if (d1 >= 0 && d2 >= 0)
            {
                Constraint d;
                d.Bone1 = d1;
                d.Bone2 = d2;
                d.Length = Size(Bones[static_cast<size_t>(d1)].Location - Bones[static_cast<size_t>(d2)].Location);
                d.IsDummy = true;
                d.ExcludeFromSubdivision = c.ExcludeFromSubdivision;
                dummies.push_back(d);
            }
            auto interBoneDummies = [&](int b) {
                std::vector<int> out;
                for (int child : Bones[static_cast<size_t>(b)].Children)
                {
                    if (child < 0 || !Bones[static_cast<size_t>(child)].InterBoneDummy) { continue; }
                    int i = child;
                    while (i >= 0 && Bones[static_cast<size_t>(i)].InterBoneDummy)
                    {
                        out.push_back(i);
                        int next = -1;
                        for (int k : Bones[static_cast<size_t>(i)].Children)
                        {
                            if (k >= 0 && Bones[static_cast<size_t>(k)].InterBoneDummy)
                            {
                                next = k;
                                break;
                            }
                        }
                        i = next;
                    }
                    if (!out.empty())
                    {
                        for (int k : Bones[static_cast<size_t>(out.back())].Children)
                        {
                            if (k >= 0 && Bones[static_cast<size_t>(k)].Dummy && !Bones[static_cast<size_t>(k)].InterBoneDummy)
                            {
                                out.push_back(k);
                                break;
                            }
                        }
                    }
                    break;
                }
                return out;
            };
            const std::vector<int> list1 = interBoneDummies(c.Bone1), list2 = interBoneDummies(c.Bone2);
            for (size_t k = 0; k < std::min(list1.size(), list2.size()); ++k)
            {
                Constraint d;
                d.Bone1 = list1[k];
                d.Bone2 = list2[k];
                d.Length = Size(Bones[static_cast<size_t>(list1[k])].Location - Bones[static_cast<size_t>(list2[k])].Location);
                d.IsDummy = true;
                d.ExcludeFromSubdivision = c.ExcludeFromSubdivision;
                dummies.push_back(d);
            }
        }
        Constraints.insert(Constraints.end(), dummies.begin(), dummies.end());
        InsertBridgeDummies();
    }

    void InsertBridgeDummies()
    {
        if (Cfg.BoneConstraintSubdivisionCount <= 0) { return; }
        const size_t count = Constraints.size();
        for (size_t k = 0; k < count; ++k)
        {
            const Constraint c = Constraints[k];
            if (c.ExcludeFromSubdivision || !c.IsBoneReferenceValid() || c.Bone1 >= static_cast<int>(Bones.size()) || c.Bone2 >= static_cast<int>(Bones.size())) { continue; }
            const Bone a = Bones[static_cast<size_t>(c.Bone1)];
            const Bone b = Bones[static_cast<size_t>(c.Bone2)];
            const float dist = Size(b.Location - a.Location);
            const float r1 = Cfg.Radius * std::max(Cfg.RadiusCurve.Eval(a.LengthRateFromRoot), 0.0f);
            const float r2 = Cfg.Radius * std::max(Cfg.RadiusCurve.Eval(b.LengthRateFromRoot), 0.0f);
            if (dist <= std::max(r1 + r2, KindaSmallNumber)) { continue; }
            const int n = Cfg.BoneConstraintSubdivisionCount;
            for (int j = 0; j < n; ++j)
            {
                const float alpha = static_cast<float>(j + 1) / static_cast<float>(n + 1);
                Bone bridge;
                bridge.Dummy = true;
                bridge.BridgeDummy = true;
                bridge.InterBoneRealParent = c.Bone1;
                bridge.InterBoneRealChild = c.Bone2;
                bridge.InterBoneAlpha = alpha;
                bridge.Location = Lerp(a.Location, b.Location, alpha);
                bridge.PrevLocation = bridge.Location;
                bridge.PoseLocation = bridge.Location;
                bridge.PrevRotation = Slerp(a.PrevRotation, b.PrevRotation, alpha);
                bridge.PoseRotation = bridge.PrevRotation;
                bridge.PoseScale = Lerp(a.PoseScale, b.PoseScale, alpha);
                bridge.Parent = -1;
                bridge.BoneLength = dist / static_cast<float>(n + 1);
                bridge.LengthRateFromRoot = 0.5f * (a.LengthRateFromRoot + b.LengthRateFromRoot);
                bridge.Index = static_cast<int>(Bones.size());
                Bones.push_back(bridge);
            }
        }
        // (their settings as their first end's, their radius the two ends' average: UpdatePhysicsSettingsOfModifyBones runs
        // after this, from their length rate, as KawaiiPhysics' does every frame)
    }

    void ApplyBridgeDummyCollisionFeedback()
    {
        if (Cfg.BoneConstraintSubdivisionCount <= 0 || Cfg.BoneConstraintSubdivisionFeedbackScale <= 0.0f) { return; }
        const size_t n = Bones.size();
        FeedbackPush.assign(n, V3{});
        FeedbackWeight.assign(n, 0.0f);
        for (const auto& bone : Bones)
        {
            if (!bone.BridgeDummy || bone.SkipSimulate || bone.InterBoneRealParent < 0 || bone.InterBoneRealChild < 0) { continue; }
            const V3 push = bone.Location - bone.PoseLocation;
            if (NearlyZero(push)) { continue; }
            auto add = [&](int endpoint, float weight) {
                const Bone& e = Bones[static_cast<size_t>(endpoint)];
                if (Cfg.BoneSubdivisionCollisionOnly && e.InterBoneDummy)
                {
                    if (e.InterBoneRealParent < 0 || e.InterBoneRealChild < 0) { return; }
                    const float pw = weight * (1.0f - e.InterBoneAlpha), cw = weight * e.InterBoneAlpha;
                    FeedbackPush[static_cast<size_t>(e.InterBoneRealParent)] += push * pw;
                    FeedbackWeight[static_cast<size_t>(e.InterBoneRealParent)] += pw;
                    FeedbackPush[static_cast<size_t>(e.InterBoneRealChild)] += push * cw;
                    FeedbackWeight[static_cast<size_t>(e.InterBoneRealChild)] += cw;
                }
                else
                {
                    FeedbackPush[static_cast<size_t>(endpoint)] += push * weight;
                    FeedbackWeight[static_cast<size_t>(endpoint)] += weight;
                }
            };
            add(bone.InterBoneRealParent, 1.0f - bone.InterBoneAlpha);
            add(bone.InterBoneRealChild, bone.InterBoneAlpha);
        }
        for (size_t i = 0; i < n; ++i)
        {
            if (FeedbackWeight[i] > 0.0f) { Bones[i].Location += (FeedbackPush[i] / std::max(1.0f, FeedbackWeight[i])) * Cfg.BoneConstraintSubdivisionFeedbackScale; }
        }
    }

    // ---- the simulation (AnimNode_KawaiiPhysicsSimulation.cpp) ----
    void SimulateModifyBones()
    {
        if (DeltaTime <= 0.0f) { return; }
        FrameDeltaTime = DeltaTime;
        for (auto& bone : Bones)
        {
            if (bone.BridgeDummy)
            {
                bone.SkipSimulate = false;
                continue;
            }
            if (bone.MeshIndex < 0 && !bone.Dummy)
            {
                bone.SkipSimulate = true;
                continue;
            }
            bone.SkipSimulate = bone.Parent < 0;   // (a root: it follows the pose, in SimulateOnce)
        }
        const V3 gravity{Cfg.Gravity[0], Cfg.Gravity[1], Cfg.Gravity[2]};
        GravityInSimSpace = ConvertVectorSpace(Cfg.UseWorldSpaceGravity ? KawaiiSpace::World : KawaiiSpace::Component, Cfg.SimulationSpace, gravity);
        if (Cfg.UseDefaultGravityZ) { GravityInSimSpace *= 980.0f; }
        const V3 force{Cfg.SimpleExternalForce[0], Cfg.SimpleExternalForce[1], Cfg.SimpleExternalForce[2]};
        SimpleExternalForceInSimSpace =
            NearlyZero(force) ? V3{} : (Cfg.UseWorldSpaceSimpleExternalForce ? ConvertVectorSpace(KawaiiSpace::World, Cfg.SimulationSpace, force) : force);
        for (auto& bone : Bones)
        {
            bone.CurrentPoseLocation = bone.PoseLocation;
            bone.CurrentPoseRotation = bone.PoseRotation;
            if (!SubstepPoseInitialized)
            {
                bone.StepPoseLocation = bone.PoseLocation;
                bone.PrevPoseLocation = bone.PoseLocation;
                bone.PrevPoseRotation = bone.PoseRotation;
            }
        }
        SubstepPoseInitialized = true;
        // (3.17.0) the shapes' places this frame, and whether the fixed steps place them between the last frame's and these
        for (auto& sh : Shapes)
        {
            sh.FrameLocation = sh.Location;
            sh.FrameR = sh.R;
        }
        const bool sweep = Cfg.InterpolateLimitsInSubsteps && !(TeleportPhysics && Cfg.SimulationSpace != KawaiiSpace::Component);
        if (!Cfg.UseFixedSubstepping)
        {
            InSubstep = false;
            SimulateOnce();
            for (auto& bone : Bones) { bone.StepPoseLocation = bone.PoseLocation; }
            DeltaTimeOld = DeltaTime;
            ConsumeFraction = 1.0f;
        }
        else
        {
            const float fixedDt = 1.0f / static_cast<float>(Framerate());
            const float raw = std::max(SubstepAccumulator + FrameDeltaTime, KindaSmallNumber);
            SubstepAccumulator = std::min(raw, static_cast<float>(std::max(1, Cfg.MaxSubsteps)) * fixedDt);
            const float dropped = raw - SubstepAccumulator;
            const int steps = static_cast<int>(std::floor(SubstepAccumulator / fixedDt));
            SubstepAccumulator -= static_cast<float>(steps) * fixedDt;
            const float moveFraction = fixedDt / raw;
            ConsumeFraction = Clamp((static_cast<float>(steps) * fixedDt + dropped) / raw, 0.0f, 1.0f);
            const V3 fullMove = SkelCompMoveVector;
            const Q4 fullTurn = SkelCompMoveRotation;
            InSubstep = true;
            StepDeltaTime = fixedDt;
            DeltaTimeOld = fixedDt;
            for (int step = 0; step < steps; ++step)
            {
                const float alpha = static_cast<float>(step + 1) / static_cast<float>(steps);
                for (auto& bone : Bones)
                {
                    bone.PoseLocation = Lerp(bone.PrevPoseLocation, bone.CurrentPoseLocation, alpha);
                    bone.PoseRotation = Normalized(Slerp(bone.PrevPoseRotation, bone.CurrentPoseRotation, alpha));
                }
                SkelCompMoveVector = fullMove * moveFraction;
                SkelCompMoveRotation = Normalized(Slerp(Q4{}, fullTurn, moveFraction));
                if (sweep) { PlaceShapesBetween(alpha); }
                SimulateOnce();
                for (auto& bone : Bones) { bone.StepPoseLocation = bone.PoseLocation; }
            }
            InSubstep = false;
            SkelCompMoveVector = fullMove;
            SkelCompMoveRotation = fullTurn;
            for (auto& sh : Shapes)
            {
                sh.Location = sh.FrameLocation;
                sh.R = sh.FrameR;
                if (sh.Kind == 4 && sh.Enable) { sh.P = Plane::Through(sh.Location, AxisZ(sh.R)); }
            }
            for (auto& bone : Bones)
            {
                bone.PoseLocation = bone.CurrentPoseLocation;
                bone.PoseRotation = bone.CurrentPoseRotation;
            }
        }
        for (auto& bone : Bones)
        {
            bone.PrevPoseLocation = bone.CurrentPoseLocation;
            bone.PrevPoseRotation = bone.CurrentPoseRotation;
        }
        for (auto& sh : Shapes)
        {
            sh.PrevLocation = sh.FrameLocation;
            sh.PrevR = sh.FrameR;
        }
    }

    void SimulateOnce()
    {
        for (auto& bone : Bones)
        {
            if (bone.Parent < 0 && !bone.BridgeDummy && !(bone.MeshIndex < 0 && !bone.Dummy))
            {
                bone.PrevLocation = bone.Location;
                bone.Location = bone.PoseLocation;
            }
        }
        const float exponent = static_cast<float>(Framerate()) * StepDt();
        for (auto& bone : Bones)
        {
            if (bone.SkipSimulate || (bone.InterBoneDummy && Cfg.BoneSubdivisionCollisionOnly) || bone.BridgeDummy) { continue; }
            Simulate(bone, exponent);
        }
        if (Cfg.BoneSubdivisionCollisionOnly)
        {
            for (auto& bone : Bones)
            {
                if (!bone.InterBoneDummy || bone.InterBoneRealParent < 0 || bone.InterBoneRealChild < 0) { continue; }
                bone.PrevLocation = bone.Location;
                bone.Location = Lerp(Bones[static_cast<size_t>(bone.InterBoneRealParent)].Location, Bones[static_cast<size_t>(bone.InterBoneRealChild)].Location,
                                     bone.InterBoneAlpha);
            }
        }
        for (auto& bone : Bones)
        {
            if (!bone.BridgeDummy || bone.InterBoneRealParent < 0 || bone.InterBoneRealChild < 0) { continue; }
            bone.PrevLocation = bone.Location;
            bone.Location = Lerp(Bones[static_cast<size_t>(bone.InterBoneRealParent)].Location, Bones[static_cast<size_t>(bone.InterBoneRealChild)].Location,
                                 bone.InterBoneAlpha);
            bone.PoseLocation = bone.Location;
        }
        PrepareCollisionShapeCaches();
        if (Cfg.BoneConstraintIterationsBeforeCollision > 0)
        {
            for (auto& c : Constraints) { c.Lambda = 0.0f; }
            for (int i = 0; i < Cfg.BoneConstraintIterationsBeforeCollision; ++i) { AdjustByBoneConstraints(); }
        }
        for (size_t i = 0; i < Bones.size(); ++i)
        {
            if (Bones[i].SkipSimulate) { continue; }
            AdjustByCollisions(Bones[i], i);
        }
        ApplyBridgeDummyCollisionFeedback();
        if (Cfg.BoneConstraintIterationsAfterCollision > 0)
        {
            for (auto& c : Constraints) { c.Lambda = 0.0f; }
            for (int i = 0; i < Cfg.BoneConstraintIterationsAfterCollision; ++i) { AdjustByBoneConstraints(); }
        }
        RestoreBoneLengthsAndLimits();
    }

    void Simulate(Bone& bone, float exponent)
    {
        const Bone& parent = Bones[static_cast<size_t>(bone.Parent)];
        // ComputeVerletStepVelocity
        V3 velocity = (bone.Location - bone.PrevLocation) / std::max(DeltaTimeOld, KindaSmallNumber);
        bone.PrevLocation = bone.Location;
        velocity *= (1.0f - bone.Damping);
        const float dt = StepDt();
        if (!Cfg.UseLegacyGravity) { velocity += GravityInSimSpace * dt; }
        else { bone.Location += GravityInSimSpace * (0.5f * dt * dt); }
        // IntegrateVerletStepPosition, ApplySimpleExternalForce
        bone.Location += velocity * dt;
        if (!NearlyZero(SimpleExternalForceInSimSpace)) { bone.Location += SimpleExternalForceInSimSpace * dt; }
        // follow the mesh's move
        if (Cfg.SimulationSpace == KawaiiSpace::BaseBone && !TeleportPhysics)
        {
            const V3 moveBase = ConvertVectorSpace(KawaiiSpace::Component, KawaiiSpace::BaseBone, SkelCompMoveVector);
            bone.Location += moveBase * (1.0f - bone.WorldDampingLocation);
            const V3 prevCS = TransformPosition(PrevBaseToComponent, bone.PrevLocation);
            const V3 rotatedCS = Rotate(SkelCompMoveRotation, prevCS);
            const V3 rotatedBase = ConvertLocation(Cache{}, SimCache, rotatedCS);
            bone.Location += (rotatedBase - bone.PrevLocation) * (1.0f - bone.WorldDampingRotation);
        }
        else if (Cfg.SimulationSpace != KawaiiSpace::World && !TeleportPhysics)
        {
            bone.Location += SkelCompMoveVector * (1.0f - bone.WorldDampingLocation);
            bone.Location += (Rotate(SkelCompMoveRotation, bone.PrevLocation) - bone.PrevLocation) * (1.0f - bone.WorldDampingRotation);
        }
        // ApplyStiffnessPull
        const V3 base = parent.Location + (bone.PoseLocation - parent.PoseLocation);
        bone.Location += (base - bone.Location) * (1.0f - std::pow(1.0f - bone.Stiffness, exponent));
    }

    void RestoreBoneLengthsAndLimits()
    {
        for (auto& bone : Bones)
        {
            if (bone.SkipSimulate || bone.BridgeDummy || (Cfg.BoneSubdivisionCollisionOnly && bone.InterBoneDummy)) { continue; }
            int parentIndex = bone.Parent;
            if (Cfg.BoneSubdivisionCollisionOnly)
            {
                while (parentIndex >= 0 && Bones[static_cast<size_t>(parentIndex)].InterBoneDummy) { parentIndex = Bones[static_cast<size_t>(parentIndex)].Parent; }
            }
            if (parentIndex < 0) { continue; }
            const Bone& parent = Bones[static_cast<size_t>(parentIndex)];
            AdjustByAngleLimit(bone, parent);
            AdjustByPlanarConstraint(bone, parent);
            const float length = Size(bone.PoseLocation - parent.PoseLocation);
            bone.Location = SafeNormal(bone.Location - parent.Location) * length + parent.Location;
        }
        if (Cfg.BoneSubdivisionCollisionOnly)
        {
            for (auto& bone : Bones)
            {
                if (bone.InterBoneDummy && bone.InterBoneRealParent >= 0 && bone.InterBoneRealChild >= 0)
                {
                    bone.Location = Lerp(Bones[static_cast<size_t>(bone.InterBoneRealParent)].Location, Bones[static_cast<size_t>(bone.InterBoneRealChild)].Location,
                                         bone.InterBoneAlpha);
                }
            }
        }
    }

    void WarmUp()
    {
        const float savedDelta = DeltaTime;
        const float savedAccumulator = SubstepAccumulator;
        if (Cfg.UseFixedSubstepping)
        {
            DeltaTime = 1.0f / static_cast<float>(Framerate());
            SubstepAccumulator = 0.0f;
        }
        for (int i = 0; i < Cfg.WarmUpFrames; ++i) { SimulateModifyBones(); }
        if (Cfg.UseFixedSubstepping)
        {
            DeltaTime = savedDelta;
            SubstepAccumulator = savedAccumulator;
        }
    }

    void ApplySimulateResult(std::vector<uint8_t>& changed)
    {
        const KawaiiSpace sim = Cfg.SimulationSpace, component = KawaiiSpace::Component;
        // (3.14.2) with fixed substeps, a frame shorter than a step runs none: the bones are shown carried by their pose's
        // move since the last step (else they stay where the step left them while the animation moves on: above the
        // step rate the chains shook as they caught up with every step). The simulation itself keeps its own places.
        Shown.resize(Bones.size());
        for (size_t i = 0; i < Bones.size(); ++i)
        {
            Shown[i] = Cfg.UseFixedSubstepping ? Bones[i].Location + (Bones[i].PoseLocation - Bones[i].StepPoseLocation) : Bones[i].Location;
        }
        std::vector<Xf> out(Bones.size());
        for (size_t i = 0; i < Bones.size(); ++i)
        {
            out[i] = ConvertTransformSpace(sim, component, Xf{Bones[i].PoseRotation, Bones[i].PoseLocation, Bones[i].PoseScale});
        }
        for (size_t i = 0; i < Bones.size(); ++i)
        {
            Bone& bone = Bones[i];
            if (!bone.HasParent()) { continue; }
            Bone& parent = Bones[static_cast<size_t>(bone.Parent)];
            // (KawaiiPhysics `continue`s here when the bone points the way its pose does, which also skips writing the
            // bone's location below: a bone lying exactly along its pose's direction, but moved (a chain resting flat on
            // a floor plane), snapped back to its pose. Only the parent's rotation is skipped here.)
            // (3.17.0) The parent is turned from its pose's direction before the sync bones moved the pose: its pose's
            // rotation points that way. (KawaiiPhysics turns it from the moved pose's direction, which left a chain the
            // sync moved far kinked: its bones' places moved, their rotations as animated.)
            const V3 shown = Shown[i], parentShown = Shown[static_cast<size_t>(bone.Parent)];
            const V3 bonePose = Syncs.empty() ? bone.PoseLocation : bone.UnsyncedPoseLocation;
            const V3 parentPose = Syncs.empty() ? parent.PoseLocation : parent.UnsyncedPoseLocation;
            if (parent.Children.size() <= 1 && parent.MeshIndex >= 0 && SafeNormal(bonePose - parentPose) != SafeNormal(shown - parentShown))
            {
                V3 poseVector = bonePose - parentPose;
                V3 simulateVector = shown - parentShown;
                if (Cfg.BoneForwardAxis == KawaiiAxis::XNegative || Cfg.BoneForwardAxis == KawaiiAxis::YNegative || Cfg.BoneForwardAxis == KawaiiAxis::ZNegative)
                {
                    poseVector = -poseVector;
                    simulateVector = -simulateVector;
                }
                Q4 rotation = FindBetweenVectors(poseVector, simulateVector) * parent.PoseRotation;
                parent.PrevRotation = rotation;
                out[static_cast<size_t>(bone.Parent)].R = ConvertRotationSpace(sim, component, rotation);
            }
            if (bone.MeshIndex >= 0 && !bone.Dummy) { out[i].T = ConvertLocationSpace(sim, component, shown); }
        }
        for (size_t i = 0; i < Bones.size(); ++i)
        {
            const int mesh = Bones[i].MeshIndex;
            if (mesh < 0 || Bones[i].Dummy || static_cast<size_t>(mesh) >= Pose->size()) { continue; }
            (*Pose)[static_cast<size_t>(mesh)] = out[i];
            changed[static_cast<size_t>(mesh)] = 1;
        }
    }
};

// Every node of an entry on one mesh, in order (each sees the pose the ones before it left, as in an AnimGraph).
struct Chain
{
    std::vector<Node> Nodes;
    std::vector<Xf> Before;
    std::vector<uint8_t> Set;

    explicit Chain(const std::vector<KawaiiNode>& nodes)
    {
        Nodes.reserve(nodes.size());
        for (const auto& n : nodes) { Nodes.emplace_back(n); }
    }

    void ResetPhysics()
    {
        for (auto& n : Nodes) { n.ResetPhysics(); }
    }
    void Teleport()
    {
        for (auto& n : Nodes) { n.Teleport(); }
    }

    // `changed` (out): the bones whose transforms the nodes changed (theirs and the bones below them). Returns how many
    // nodes ran.
    int Evaluate(const Skeleton& skel, std::vector<Xf>& pose, std::vector<uint8_t>& changed, const Xf& component, float delta, const std::vector<uint8_t>* skip)
    {
        int ran = 0;
        changed.assign(pose.size(), 0);
        for (auto& node : Nodes)
        {
            Before = pose;
            Set.assign(pose.size(), 0);
            if (!node.Evaluate(skel, pose, Set, component, delta, skip)) { continue; }
            ++ran;
            for (size_t i = 0; i < Set.size(); ++i)
            {
                if (Set[i]) { changed[i] = 1; }
            }
            CarryToChildren(skel, Before, pose, changed, Set);
        }
        return ran;
    }
};
} // namespace Kawaii
