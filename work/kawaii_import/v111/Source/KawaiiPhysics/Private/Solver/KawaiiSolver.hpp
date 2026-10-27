// KawaiiSolver.hpp - KawaiiPhysics' simulation, ported to plain C++ (Create a Character System 3.14.0; 3.18.0: all of 1.21).
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
// the same way.
// (3.17.0) Sync bones (AnimNode_KawaiiPhysicsSyncBone.cpp): here, but for one thing: a bone the sync moved is turned
// toward its child from its pose's direction before the sync (ApplySimulateResult).
// (3.18.0) The rest of 1.21 (AnimNode_KawaiiPhysicsCollision.cpp, AnimNode_KawaiiPhysicsSimulation.cpp, ExternalForces/,
// the AnimNotifies' node calls in KawaiiPhysicsLibrary.cpp): external forces (Basic, Gravity, Curve, Wind, Procedural Wind
// with its gusts, presets and shared winds), the node's wind, settings multipliers, transient forces, the alpha blend, the
// reusable sets (limits; bone constraints with their regex patterns), mirrored shapes, the physics asset's shapes (put in
// the node's Data* lists by the game), the shapes from outside the node (the floor, the level's simple collision with its
// convex hulls, other meshes' shared shapes) and world collision sweeps. The world itself (Environment) is the game's
// (KawaiiRt::World in main.dll); the End editor's preview has none of it but a wind of its own. Where this differs from
// 1.21:
//   * the Gravity force's use_character_gravity_scale: times the size of the character's GravityZ (1.21 multiplies by the
//     signed value, which turns a normal world's pull upward); use_character_gravity_direction: down (UE 4.26 has no
//     custom gravity);
//   * the random numbers (procedural wind, random force scales, the wind's noise): UE 5's FRandomStream, each node seeded
//     by its root bone's name (the same numbers in the game and in the editor's preview);
//   * external forces are a list of types and their settings (UE 4.26 has no instanced structs);
//   * the shared collision subsystem's own gathering (the simple world, the family's members) is not here: the game hands
//     the shapes in (Environment::Ground, LevelShapes, Shared).
#pragma once

#include "SkelCompatCore.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <functional>
#include <memory>
#include <regex>
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
using SkelCompat::KawaiiCurveEvaluate;
using SkelCompat::KawaiiExternalForce;
using SkelCompat::KawaiiForceSpace;
using SkelCompat::KawaiiForceType;
using SkelCompat::KawaiiSettingsScale;
using SkelCompat::KawaiiWindSource;

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

// (3.18.0) FQuat::FindBetweenNormals
inline Q4 FindBetweenNormals(V3 a, V3 b)
{
    float w = 1.0f + Dot(a, b);
    Q4 result;
    if (w >= 1e-6f) { result = {a.Y * b.Z - a.Z * b.Y, a.Z * b.X - a.X * b.Z, a.X * b.Y - a.Y * b.X, w}; }
    else
    {
        w = 0.0f;
        result = std::fabs(a.X) > std::fabs(a.Y) ? Q4{-a.Z, 0.0f, a.X, w} : Q4{0.0f, -a.Z, a.Y, w};
    }
    return Normalized(result);
}
// FVector::FindBestAxisVectors
inline void FindBestAxisVectors(V3 v, V3& axis1, V3& axis2)
{
    const float nx = std::fabs(v.X), ny = std::fabs(v.Y), nz = std::fabs(v.Z);
    axis1 = (nz > nx && nz > ny) ? V3{1, 0, 0} : V3{0, 0, 1};
    axis1 = SafeNormal(axis1 - v * Dot(axis1, v));
    axis2 = Cross(axis1, v);
}
// FRotator from a direction (FVector::Rotation): its yaw and pitch (degrees)
inline void DirectionRotator(V3 v, float& pitch, float& yaw)
{
    yaw = RadiansToDegrees(std::atan2(v.Y, v.X));
    pitch = RadiansToDegrees(std::atan2(v.Z, std::sqrt(v.X * v.X + v.Y * v.Y)));
}
// FAnimationRuntime::MirrorVector / MirrorQuat (axis 0 none, 1 X, 2 Y, 3 Z)
inline V3 MirrorVector(V3 v, int axis)
{
    if (axis == 1) { v.X = -v.X; }
    else if (axis == 2) { v.Y = -v.Y; }
    else if (axis == 3) { v.Z = -v.Z; }
    return v;
}
inline Q4 MirrorQuat(Q4 q, int axis)
{
    if (axis == 1) { q.Y = -q.Y; q.Z = -q.Z; }
    else if (axis == 2) { q.X = -q.X; q.Z = -q.Z; }
    else if (axis == 3) { q.X = -q.X; q.Y = -q.Y; }
    return q;
}
// FQuat::Rotator (pitch, yaw, roll in degrees), UE 4.26's
inline void QuatToRotator(Q4 q, float& pitch, float& yaw, float& roll)
{
    const float singularity = q.Z * q.X - q.W * q.Y;
    const float yawY = 2.0f * (q.W * q.Z + q.X * q.Y);
    const float yawX = 1.0f - 2.0f * (q.Y * q.Y + q.Z * q.Z);
    constexpr float threshold = 0.4999995f;
    const float toDeg = 180.0f / Pi;
    const auto normalizeAxis = [](float angle) {
        angle = std::fmod(angle, 360.0f);
        if (angle < 0.0f) { angle += 360.0f; }
        if (angle > 180.0f) { angle -= 360.0f; }
        return angle;
    };
    if (singularity < -threshold)
    {
        pitch = -90.0f;
        yaw = std::atan2(yawY, yawX) * toDeg;
        roll = normalizeAxis(-yaw - (2.0f * std::atan2(q.X, q.W) * toDeg));
    }
    else if (singularity > threshold)
    {
        pitch = 90.0f;
        yaw = std::atan2(yawY, yawX) * toDeg;
        roll = normalizeAxis(yaw - (2.0f * std::atan2(q.X, q.W) * toDeg));
    }
    else
    {
        pitch = std::asin(2.0f * singularity) * toDeg;
        yaw = std::atan2(yawY, yawX) * toDeg;
        roll = std::atan2(-2.0f * (q.W * q.X + q.Y * q.Z), 1.0f - 2.0f * (q.X * q.X + q.Y * q.Y)) * toDeg;
    }
}

// (3.18.0) FRandomStream (UE 5's GetFraction: the numbers KawaiiPhysics' procedural wind sees there) and a node's own
// random numbers (FMath::FRand's uses: a force's random scale, the node wind's gust and noise).
struct RandomStream
{
    uint32_t Seed = 0;
    explicit RandomStream(uint32_t seed = 0) : Seed(seed) {}
    float Fraction()
    {
        Seed = Seed * 196314165u + 907633515u;
        const uint32_t bits = 0x3F800000u | (Seed >> 9);
        float result;
        std::memcpy(&result, &bits, sizeof(result));
        return result - 1.0f;
    }
    float Range(float lo, float hi) { return lo + (hi - lo) * Fraction(); }
};
// FMath::VRand on a stream
inline V3 RandomUnitVector(RandomStream& r)
{
    for (int tries = 0; tries < 64; ++tries)
    {
        const V3 v{r.Fraction() * 2.0f - 1.0f, r.Fraction() * 2.0f - 1.0f, r.Fraction() * 2.0f - 1.0f};
        const float l = SizeSq(v);
        if (l <= 1.0f && l >= KindaSmallNumber) { return v * (1.0f / std::sqrt(l)); }
    }
    return {0, 0, 1};
}
// FMath::VRandCone on a stream
inline V3 RandomCone(V3 dir, float halfAngleRad, RandomStream& r)
{
    if (!(halfAngleRad > 0.0f)) { return SafeNormal(dir); }
    const float u = r.Fraction(), v = r.Fraction();
    const float theta = 2.0f * Pi * u;
    float phi = Acos(2.0f * v - 1.0f);
    phi = std::fmod(phi, halfAngleRad);
    float pitch = 0.0f, yaw = 0.0f;
    DirectionRotator(dir, pitch, yaw);
    const float cp = std::cos(DegreesToRadians(pitch)), sp = std::sin(DegreesToRadians(pitch));
    const float cy = std::cos(DegreesToRadians(yaw)), sy = std::sin(DegreesToRadians(yaw));
    const V3 dirZ{cp * cy, cp * sy, sp};   // (its X axis: the variation is around it)
    const V3 dirY{-sy, cy, 0.0f};
    V3 result = RotateAngleAxis(dir, phi * 180.0f / Pi, dirY);
    result = RotateAngleAxis(result, theta * 180.0f / Pi, dirZ);
    return SafeNormal(result);
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
    std::vector<Q4> RefRotation;     // (3.18.0) each bone's reference-pose rotation in the component's space (the mirrored
                                     // shapes; none: from the first pose the node sees)

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

// ---- (3.18.0) what a node sees of the world (the game's: KawaiiRt; none in the End editor's preview but the wind) ----
// A collision shape in the world's space (the level's simple collision, the floor, another mesh's shared shapes): kind
// 0 sphere, 1 capsule, 2 tapered capsule, 3 box, 4 plane, 5 convex (planes in its own space: X Y Z the normal, W the
// distance; Bounds its box there).
struct WorldShape
{
    int Kind = 0;
    V3 Location;
    Q4 Rotation;
    float Radius = 0, Length = 0, Radius0 = 0, Radius1 = 0;
    V3 Extent;
    bool Inner = false;
    std::vector<std::array<float, 4>> Planes;
    V3 BoundsMin, BoundsMax;
};
// UE's FScene::GetWindParameters at a place
struct WindSample
{
    V3 Direction{1, 0, 0};
    float Speed = 0, MinGust = 0, MaxGust = 0;
};
// A procedural wind gust (FKawaiiProceduralWindActiveGust)
struct WindGust
{
    float StartTime = 0, Strength = 0, RiseTime = 0, DecayTime = 0, HoldTime = 0;
    bool Active = false, RealTime = false;
};
// A shared wind (the entry's "shared_winds": KawaiiPhysics' Shared Publisher), kept by the game for a character's meshes
struct SharedWindState
{
    SkelCompat::KawaiiExternalForce Params;
    float Time = 0, UnscaledTime = 0;
    WindGust Gust;
    bool Enabled = true;
};
struct Environment
{
    // the level's wind at a world place (false: no wind source)
    std::function<bool(V3 world, WindSample& out)> Wind;
    // the character's gravity (its movement component's GetGravityZ), for the Gravity force's use_character_gravity_scale
    bool HasGravityZ = false;
    float GravityZ = -980.0f;
    const std::vector<WorldShape>* LevelShapes = nullptr;   // "use_simple_world_collision" (world space)
    const std::vector<WorldShape>* Ground = nullptr;        // the floor box (its "simple_world_collision_ground_collision", "ground_collision")
    // the shared shapes of the character's other meshes for a group tag (null: none)
    std::function<const std::vector<WorldShape>*(const std::wstring& tag)> Shared;
    // a sphere sweep in the world (world collision): true and `hit` where the sphere stops
    std::function<bool(V3 start, V3 end, float radius, V3& hit)> Sweep;
    int* SweepBudget = nullptr;                             // sweeps left this frame (shared by the entry's nodes)
    std::function<SharedWindState*(const std::wstring& tag)> SharedWind;
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
        // (3.18.0) its own random numbers (its root bone's name the seed: the same in the game and the editor)
        uint32_t seed = 2166136261u;
        for (const wchar_t c : Cfg.RootBone) { seed = (seed ^ static_cast<uint32_t>(c)) * 16777619u; }
        Random.Seed = seed;
        MakeForces();
    }

    const KawaiiNode& Settings() const { return Cfg; }

    // ---- (3.18.0) from outside the node: the animation triggers, the game's shared winds ----
    // External forces added (KawaiiPhysics' AddExternalForce): `owner` names them (RemoveForces takes them off); a
    // one-shot force (a pulse's) runs one step, then goes.
    void AddForces(const std::vector<KawaiiExternalForce>& forces, uint64_t owner, bool oneShot)
    {
        for (const auto& f : forces)
        {
            if (Forces.size() >= 64) { break; }
            ForceRt rt;
            rt.F = f;
            rt.Owner = owner;
            rt.OneShot = oneShot;
            PrepareForce(rt);
            Forces.push_back(std::move(rt));
        }
    }
    void RemoveForces(uint64_t owner)
    {
        if (owner == 0) { return; }
        Forces.erase(std::remove_if(Forces.begin(), Forces.end(), [&](const ForceRt& f) { return f.Owner == owner && f.Lifetime < 0.0f; }), Forces.end());
    }
    // A gust (KawaiiPhysics' RequestTransientGust, every procedural wind inherited): a transient procedural wind for each
    // of the node's own (its filters, curve, time scale, space and direction; `world` its direction instead when not
    // zero), or one of its own when it has none. Its envelope: rise, hold, decay (s).
    void RequestGust(float strength, float rise, float hold, float decay, V3 world)
    {
        PendingGusts.push_back({strength, rise, hold, decay, world});
        if (PendingGusts.size() > 32) { PendingGusts.erase(PendingGusts.begin()); }
    }
    // Settings multipliers (KawaiiPhysics' physics settings multipliers): a timed one (rise, hold, decay; or held till
    // stopped), one driven from outside (its weight each evaluation, a lease of evaluations), and its stop (a blend out).
    void StartSettingsMultiplier(int64_t handle, const KawaiiSettingsScale& scale, float rise, float hold, float decay, bool infiniteHold)
    {
        MultiplierRequest r;
        r.Kind = 0;
        r.Handle = handle;
        r.Scale = scale;
        r.Rise = rise;
        r.Hold = hold;
        r.Decay = decay;
        r.Infinite = infiniteHold;
        PendingMultipliers.push_back(r);
    }
    void PushSettingsMultiplier(int64_t handle, const KawaiiSettingsScale& scale, float alpha, int leaseEvaluations = 4, float leaseBlendOut = 0.2f)
    {
        if (handle == 0) { return; }
        MultiplierRequest r;
        r.Kind = 1;
        r.Handle = handle;
        r.Scale = scale;
        r.Alpha = Clamp(alpha, 0.0f, 1.0f);
        r.Lease = std::max(0, leaseEvaluations);
        r.LeaseBlendOut = std::max(0.0f, leaseBlendOut);
        // (a push takes the place of a stop or a start of the handle still waiting)
        PendingMultipliers.erase(std::remove_if(PendingMultipliers.begin(), PendingMultipliers.end(), [&](const MultiplierRequest& o) { return o.Handle == handle && o.Kind != 1; }),
                                 PendingMultipliers.end());
        for (auto& o : PendingMultipliers)
        {
            if (o.Handle == handle && o.Kind == 1)
            {
                o = r;
                return;
            }
        }
        PendingMultipliers.push_back(r);
    }
    void StopSettingsMultiplier(int64_t handle, float blendOut)
    {
        if (handle == 0) { return; }
        MultiplierRequest r;
        r.Kind = 2;
        r.Handle = handle;
        r.Decay = blendOut;
        PendingMultipliers.push_back(r);
    }
    bool HasSettingsMultipliers() const { return !Multipliers.empty() || !PendingMultipliers.empty(); }
    // The node's blend (set_alpha triggers): over its "alpha", or back to it.
    void SetAlphaOverride(bool on, float alpha)
    {
        AlphaOverridden = on;
        AlphaOverride = Clamp(alpha, 0.0f, 1.0f);
    }
    float CurrentAlpha() const { return AlphaOverridden ? AlphaOverride : Cfg.Alpha; }
    // A wind preset on its procedural winds (ApplyProceduralWindPreset), its own and the added ones.
    void ApplyWindPreset(const SkelCompat::KawaiiWindPreset& preset)
    {
        for (auto& f : Forces)
        {
            if (f.F.IsWind() && f.Lifetime < 0.0f) { SkelCompat::Detail::ApplyKawaiiWindPreset(preset, f.F); }
        }
    }
    // (shared collision) Its shapes (its own, its sets', the mirrored and the physics asset's) in the world's space as of
    // its last evaluation.
    void PublishShapes(std::vector<WorldShape>& out) const
    {
        if (!HaveSpaceCache) { return; }
        const float scale = UniformScale(ComponentToWorld);
        for (const auto& s : Shapes)
        {
            if (!s.Enable || s.Kind > 4) { continue; }
            WorldShape w;
            w.Kind = s.Kind;
            w.Location = ConvertLocationSpace(Cfg.SimulationSpace, KawaiiSpace::World, s.Location);
            w.Rotation = Normalized(ConvertRotationSpace(Cfg.SimulationSpace, KawaiiSpace::World, s.R));
            w.Radius = s.L.Radius * scale;
            w.Length = s.L.Length * scale;
            w.Radius0 = s.L.Radius0 * scale;
            w.Radius1 = s.L.Radius1 * scale;
            w.Extent = V3{s.L.Extent[0], s.L.Extent[1], s.L.Extent[2]} * scale;
            w.Inner = s.L.Inner;
            out.push_back(std::move(w));
        }
    }
    size_t ForceCount() const { return Forces.size(); }
    size_t ShapeCount() const { return Shapes.size(); }
    size_t OuterShapeCount() const { return OuterShapes.size(); }
    int SweepsLastFrame() const { return Sweeps; }

    // (the End editor's live edits) New settings that make the same chains (the caller checks that: the same bones, dummy
    // points, inserted points, space and bone constraints) take effect at the next evaluation without starting the
    // bones again: the physics values, curves, forces, limits and shapes are read from them from then on.
    void Retune(const KawaiiNode& settings)
    {
        Cfg = settings;
        InitPhysicsSettings = false;
        AnimPrepared = static_cast<size_t>(-1);   // (3.15.0) its key animation's tracks found again for the bones
        SyncPrepared = false;                     // (3.17.0) its sync bones' targets found again
        // (3.18.0) its own forces from the new settings (each keeping its clock when it is of the same type: a live edit
        // does not restart the wind), the added ones kept; its shapes made again (sets, mirror)
        std::vector<ForceRt> old;
        old.swap(Forces);
        MakeForces();
        size_t own = 0;
        for (auto& f : old)
        {
            if (f.Owner != 0 || f.Lifetime >= 0.0f)
            {
                Forces.push_back(std::move(f));
                continue;
            }
            if (own < Cfg.ExternalForces.size() && Forces[own].F.Type == f.F.Type)
            {
                Forces[own].Time = f.Time;
                Forces[own].WTime = f.WTime;
                Forces[own].WUnscaled = f.WUnscaled;
                Forces[own].Gust = f.Gust;
            }
            ++own;
        }
        Shapes.clear();
        ExtraLimits.clear();
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
                  const std::vector<uint8_t>* skip = nullptr, const Environment* env = nullptr)
    {
        Problem.clear();
        Skel = &skel;
        Pose = &pose;
        Skip = Cfg.SkipBonamikBones ? skip : nullptr;   // ("skip_bonamik_bones": false keeps them in its chains)
        ComponentToWorld = component;
        DeltaTime = delta;
        Env = env;
        WindNoiseFresh = false;
        Sweeps = 0;
        // (3.18.0) a blend of nothing: KawaiiPhysics' skeletal control does not run at all (FAnimWeight::IsRelevant)
        if (CurrentAlpha() < 0.00001f)
        {
            Problem = L"its alpha is 0";
            return false;
        }
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
        // (3.18.0) the settings multipliers of this frame first (KawaiiPhysics' ConsumeAndAdvancePhysicsSettingsMultipliers),
        // then the physics settings (every frame while one is on, and once after)
        const bool multiplied = ConsumeAndAdvanceSettingsMultipliers(delta);
        if (!InitPhysicsSettings || multiplied || MultipliedLastUpdate)
        {
            UpdatePhysicsSettingsOfModifyBones();
            InitPhysicsSettings = true;
            MultipliedLastUpdate = multiplied;
        }
        // (3.15.0) the node's own animation: its bones' pose turned by its waves and key animation, before the physics
        // pulls the bones toward it
        if (Cfg.Animated())
        {
            AnimTime += static_cast<double>(delta);
            AnimatePose(pose);
        }
        UpdateLimits();
        UpdateOuterShapes();   // (3.18.0) the ground, the level's shapes, the other meshes' shared shapes
        UpdateModifyBonesPoseTransform();
        // (3.17.0) the sync bones: the chains' pose follows their moves (KawaiiPhysics' ApplySyncBones)
        if (!SyncPrepared) { InitSyncBones(); }
        for (auto& bone : Bones) { bone.UnsyncedPoseLocation = bone.PoseLocation; }
        ApplySyncBones();
        UpdateSkelCompMove();
        ConsumeTransientForces(delta);   // (3.18.0) once an evaluation (not in the warm up's steps)
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
        // (3.18.0) a convex (kind 5, the level's): its planes in its own space (normal, distance), its box there
        std::vector<std::array<float, 4>> Planes;
        V3 BoundsMin, BoundsMax;
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
    std::vector<Shape> OuterShapes;   // (3.18.0) the ground's, the level's and the other meshes' shared, this frame
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

    // ---- (3.18.0) external forces (ExternalForces/KawaiiPhysicsExternalForce*.cpp) and the node's wind ----
    struct ForceRt
    {
        KawaiiExternalForce F;            // (its own copy: presets and the shared wind change it)
        uint64_t Owner = 0;               // 0: the node's own; else what added it
        bool OneShot = false;             // a pulse's: one step
        float Lifetime = -1.0f;           // >= 0: a transient force (a gust's), its time left (s)
        float RandomizedScale = 1.0f;
        V3 Force;                         // this frame's, in the simulation space (bone space: the bone's own)
        float Time = 0, PrevTime = 0;     // Basic, Curve
        std::vector<V3> WindDir;          // Wind: per bone (Bones' order), in the simulation space
        std::vector<float> WindSpeed;     //       (< 0: not on that bone)
        // Procedural Wind (FKawaiiProceduralWindRuntimeState)
        float WTime = 0, WUnscaled = 0;
        WindGust Gust;
        bool HasPendingGust = false;
        WindGust PendingGust;
        float PendingStop = -1.0f;
        float CachedSines = 0, CachedCycle = 1, CachedRandom = 0, CachedGust = 0;
        V3 CachedVector;
        bool PublisherDisabled = false;
        bool UsingShared = false;
        KawaiiExternalForce LocalBackup;  // its settings before a shared wind's were taken (put back when it goes)
    };
    struct GustRequest
    {
        float Strength = 0, Rise = 0, Hold = 0, Decay = 0;
        V3 Direction;
    };
    std::vector<ForceRt> Forces;
    std::vector<GustRequest> PendingGusts;
    std::vector<ForceRt> PendingTransient;
    RandomStream Random;
    const Environment* Env = nullptr;
    bool WindNoiseFresh = false;      // the node wind's gust and noise drawn this frame
    float WindGustFactor = 1.0f;
    Q4 WindNoise;
    int Sweeps = 0;                   // world collision sweeps of the last frame
    bool AlphaOverridden = false;
    float AlphaOverride = 1.0f;
    // (3.18.0) the shapes from outside the node (ground, level, shared), in the simulation space this frame
    std::vector<WorldShape> OuterWorld;
    // (3.18.0) the mirrored shapes made at the shapes' first update (KawaiiPhysics' ApplyMirrorLimits)
    std::vector<std::pair<int, SkelCompat::KawaiiLimit>> ExtraLimits;

    void MakeForces()
    {
        for (const auto& f : Cfg.ExternalForces)
        {
            ForceRt rt;
            rt.F = f;
            PrepareForce(rt);
            Forces.push_back(std::move(rt));
        }
    }
    static void PrepareForce(ForceRt& rt)
    {
        rt.LocalBackup = rt.F;
        rt.Gust = WindGust{};
    }

    static std::wstring_view NoName() { return {}; }
    std::wstring_view BoneName(const Bone& bone) const
    {
        return bone.MeshIndex >= 0 && static_cast<size_t>(bone.MeshIndex) < Skel->Names.size() ? std::wstring_view(Skel->Names[static_cast<size_t>(bone.MeshIndex)]) : NoName();
    }
    // FKawaiiPhysics_ExternalForce::CanApply: the bone in its apply filter (when it has one), not in its ignore filter
    bool CanApply(const KawaiiExternalForce& f, const Bone& bone) const
    {
        const std::wstring_view name = BoneName(bone);
        const auto listed = [&](const std::vector<std::wstring>& list) {
            return !name.empty() && std::any_of(list.begin(), list.end(), [&](const std::wstring& n) { return SkelCompat::NameEquals(n, name); });
        };
        if (!f.ApplyBoneFilter.empty() && !listed(f.ApplyBoneFilter)) { return false; }
        if (!f.IgnoreBoneFilter.empty() && listed(f.IgnoreBoneFilter)) { return false; }
        return true;
    }
    static float ForceRate(const KawaiiExternalForce& f, const Bone& bone) { return f.ForceRateByBoneLengthRate.Empty() ? 1.0f : f.ForceRateByBoneLengthRate.Eval(bone.LengthRateFromRoot); }
    // ConvertExternalForceToSimulationSpace: world and component forces into the simulation space, bone space as it is
    V3 ForceToSim(const KawaiiExternalForce& f, V3 v) const
    {
        if (f.Space == KawaiiForceSpace::Bone) { return v; }
        return ConvertVectorSpace(f.Space == KawaiiForceSpace::World ? KawaiiSpace::World : KawaiiSpace::Component, Cfg.SimulationSpace, v);
    }
    // ResolveExternalForceBoneTransform: the bone's (a dummy: its real parent's) pose in the simulation space
    Xf ForceBoneTransform(const Bone& bone) const
    {
        const Bone* b = &bone;
        if (bone.Dummy)
        {
            if (bone.InterBoneRealParent >= 0 && static_cast<size_t>(bone.InterBoneRealParent) < Bones.size()) { b = &Bones[static_cast<size_t>(bone.InterBoneRealParent)]; }
            else if (bone.Parent >= 0) { b = &Bones[static_cast<size_t>(bone.Parent)]; }
        }
        return b->MeshIndex >= 0 ? BoneInSimSpace(b->MeshIndex) : Xf{};
    }

    // ---- Procedural Wind (KawaiiPhysicsExternalForce_ProceduralWind.cpp) ----
    static float EvaluateGust(const WindGust& g, float time)
    {
        if (!g.Active) { return 0.0f; }
        const float elapsed = time - g.StartTime;
        if (elapsed < 0.0f) { return 0.0f; }
        const float rise = std::max(g.RiseTime, 0.0f), hold = std::max(g.HoldTime, 0.0f), decay = std::max(g.DecayTime, 0.0f);
        if (rise > KindaSmallNumber && elapsed < rise) { return g.Strength * (elapsed / rise); }
        if (elapsed < rise + hold) { return g.Strength; }
        if (decay <= KindaSmallNumber) { return 0.0f; }
        const float into = elapsed - rise - hold;
        return into < decay ? g.Strength * (1.0f - into / decay) : 0.0f;
    }

  public:
    static uint32_t StableHash(int32_t seed, int32_t grid, int32_t channel)
    {
        uint32_t h = 0x811C9DC5u;
        h ^= static_cast<uint32_t>(seed);
        h *= 0x01000193u;
        h ^= static_cast<uint32_t>(grid);
        h *= 0x01000193u;
        h ^= static_cast<uint32_t>(channel);
        h *= 0x01000193u;
        h ^= h >> 16;
        h *= 0x7FEB352Du;
        h ^= h >> 15;
        h *= 0x846CA68Bu;
        h ^= h >> 16;
        return h;
    }
    static float SampleNoiseAt(int32_t grid, int32_t seed, int32_t channel)
    {
        RandomStream r(StableHash(seed, grid, channel));
        return r.Range(-1.0f, 1.0f);
    }
    static float SampleSmoothNoise(float u, int32_t seed, int32_t channel)
    {
        const float gridFloat = std::floor(u);
        const int32_t grid = static_cast<int32_t>(gridFloat);
        const float alpha = u - gridFloat;
        const float smooth = alpha * alpha * (3.0f - 2.0f * alpha);
        return Lerp(SampleNoiseAt(grid, seed, channel), SampleNoiseAt(grid + 1, seed, channel), smooth);
    }
    struct WindSampleParts
    {
        float Constant = 0, Sway = 0, Ripple = 0, Cycle = 1, Random = 0, Gust = 0, Total = 0;
    };
    // ComputeWindSample: the wind's parts at a time and a place along the chains
    static WindSampleParts ComputeWindSample(const KawaiiExternalForce& f, float time, float lengthRate, const WindGust& gust, float unscaled)
    {
        constexpr float twoPi = Pi * 2.0f;
        WindSampleParts s;
        s.Constant = f.ConstantForce;
        s.Sway = f.SwayForce * std::sin(twoPi * time / std::max(f.SwayPeriod, 0.01f) + DegreesToRadians(f.SwayPhaseOffset));
        s.Ripple = f.RippleForce * std::sin(twoPi * time / std::max(f.RipplePeriod, 0.01f) - DegreesToRadians(lengthRate * f.RippleTipPhaseDelay) +
                                            DegreesToRadians(f.RipplePhaseOffset));
        s.Cycle = Lerp(f.StrengthCycleRange[0], f.StrengthCycleRange[1],
                       0.5f * (1.0f + std::sin(twoPi * time / std::max(f.StrengthCyclePeriod, 0.01f) + DegreesToRadians(f.StrengthCyclePhaseOffset))));
        s.Random = f.RandomForce * SampleSmoothNoise(time / std::max(f.RandomForcePeriod, 0.01f), f.Seed, 0);
        s.Gust = EvaluateGust(gust, gust.RealTime ? unscaled : time);
        s.Total = (s.Constant + s.Sway + s.Ripple) * s.Cycle + s.Random + s.Gust;
        return s;
    }
    // ApplyConeNoiseToDirection
    static V3 ConeNoise(V3 direction, float nx, float ny, float halfAngleDeg)
    {
        const auto safeDir = [](V3 v) {
            const V3 n = SafeNormal(v);
            return NearlyZero(n) ? V3{1, 0, 0} : n;
        };
        const float halfAngle = DegreesToRadians(std::max(halfAngleDeg, 0.0f));
        if (halfAngle <= KindaSmallNumber) { return safeDir(direction); }
        float dx = nx, dy = ny;
        const float diskLength = std::sqrt(dx * dx + dy * dy);
        if (diskLength <= KindaSmallNumber) { return safeDir(direction); }
        if (diskLength > 1.0f)
        {
            dx /= diskLength;
            dy /= diskLength;
        }
        const V3 base = safeDir(direction);
        V3 axisX, axisY;
        FindBestAxisVectors(base, axisX, axisY);
        const V3 offset = SafeNormal(axisX * dx + axisY * dy);
        const float angle = halfAngle * std::min(diskLength, 1.0f);
        return SafeNormal(base * std::cos(angle) + offset * std::sin(angle));
    }

  private:
    // The 13 settings a shared wind gives its consumers (BuildSharedWindParams: all but the phase offsets, the time
    // scale and the switch)
    static void TakeSharedSettings(KawaiiExternalForce& to, const KawaiiExternalForce& from)
    {
        for (int k = 0; k < 3; ++k) { to.WindDirection[k] = from.WindDirection[k]; }
        to.ConstantForce = from.ConstantForce;
        to.SwayForce = from.SwayForce;
        to.SwayPeriod = from.SwayPeriod;
        to.RippleForce = from.RippleForce;
        to.RipplePeriod = from.RipplePeriod;
        to.RippleTipPhaseDelay = from.RippleTipPhaseDelay;
        to.StrengthCycleRange[0] = from.StrengthCycleRange[0];
        to.StrengthCycleRange[1] = from.StrengthCycleRange[1];
        to.StrengthCyclePeriod = from.StrengthCyclePeriod;
        to.RandomForce = from.RandomForce;
        to.RandomForcePeriod = from.RandomForcePeriod;
        to.WindDirectionNoiseAngle = from.WindDirectionNoiseAngle;
        to.WindDirectionNoisePeriod = from.WindDirectionNoisePeriod;
    }

    void PreApplyProceduralWind(ForceRt& rt, float dt)
    {
        KawaiiExternalForce& f = rt.F;
        // its requests: a gust (from the clock it names), a stop (a fade from now)
        const auto consume = [&]() {
            if (rt.HasPendingGust)
            {
                rt.Gust = rt.PendingGust;
                rt.Gust.StartTime = rt.PendingGust.RealTime ? rt.WUnscaled : rt.WTime;
                rt.Gust.Active = true;
                rt.HasPendingGust = false;
            }
            if (rt.PendingStop >= 0.0f)
            {
                if (rt.Gust.Active)
                {
                    if (rt.PendingStop <= KindaSmallNumber) { rt.Gust.Active = false; }
                    else
                    {
                        const float now = EvaluateGust(rt.Gust, rt.Gust.RealTime ? rt.WUnscaled : rt.WTime);
                        rt.Gust.RealTime = false;
                        rt.Gust.StartTime = rt.WTime;
                        rt.Gust.Strength = now;
                        rt.Gust.RiseTime = 0.0f;
                        rt.Gust.DecayTime = rt.PendingStop;
                        rt.Gust.HoldTime = 0.0f;
                        rt.Gust.Active = true;
                    }
                }
                rt.PendingStop = -1.0f;
            }
        };
        SharedWindState* shared = nullptr;
        if (f.WindSource != KawaiiWindSource::Local && Env && Env->SharedWind) { shared = Env->SharedWind(f.SharedWindTag); }
        if (shared)
        {
            // a shared wind: its 13 settings, its clock and gust (the node's own kept, put back when the shared wind goes);
            // a gust asked of this one goes to the shared wind (SendPendingGustRequestsToSharedEntry)
            if (!rt.UsingShared)
            {
                rt.LocalBackup = f;
                rt.UsingShared = true;
            }
            if (rt.HasPendingGust)
            {
                shared->Gust = rt.PendingGust;
                shared->Gust.StartTime = rt.PendingGust.RealTime ? shared->UnscaledTime : shared->Time;
                shared->Gust.Active = true;
                rt.HasPendingGust = false;
            }
            consume();
            TakeSharedSettings(f, shared->Params);
            rt.WTime = shared->Time;
            rt.WUnscaled = shared->UnscaledTime;
            rt.Gust = shared->Gust;
            rt.PublisherDisabled = !shared->Enabled;
        }
        else
        {
            if (rt.UsingShared)
            {
                TakeSharedSettings(f, rt.LocalBackup);
                rt.UsingShared = false;
            }
            consume();
            rt.PublisherDisabled = false;
            const float step = std::max(dt, 0.0f);
            rt.WTime += step * f.TimeScale;
            rt.WUnscaled += step;
        }
        const WindSampleParts s = rt.PublisherDisabled ? WindSampleParts{} : ComputeWindSample(f, rt.WTime, 0.0f, rt.Gust, rt.WUnscaled);
        rt.CachedSines = s.Constant + s.Sway;
        rt.CachedCycle = s.Cycle;
        rt.CachedRandom = s.Random;
        rt.CachedGust = s.Gust;
        if (rt.PublisherDisabled)
        {
            rt.CachedVector = {};
            return;
        }
        V3 direction = SafeNormal(V3{f.WindDirection[0], f.WindDirection[1], f.WindDirection[2]});
        if (NearlyZero(direction)) { direction = {1, 0, 0}; }
        if (f.WindDirectionNoiseAngle > 0.0f)
        {
            const float u = rt.WTime / std::max(f.WindDirectionNoisePeriod, 0.01f);
            direction = ConeNoise(direction, SampleSmoothNoise(u, f.Seed, 1), SampleSmoothNoise(u, f.Seed, 2), f.WindDirectionNoiseAngle);
        }
        rt.CachedVector = ForceToSim(f, direction);
    }

    // PreApply of every force, once a frame (SimulateModifyBones): their force of this frame (and the Wind's per bone)
    void PreApplyForces()
    {
        const float dt = StepDt();   // (outside the steps: the frame's time, as KawaiiPhysics')
        for (auto& rt : Forces)
        {
            KawaiiExternalForce& f = rt.F;
            rt.RandomizedScale = f.IsWind() ? 1.0f : Random.Range(f.RandomForceScaleRange[0], f.RandomForceScaleRange[1]);
            switch (f.Type)
            {
            case KawaiiForceType::Basic:
            {
                rt.PrevTime = rt.Time;
                rt.Time += dt;
                V3 force{};
                if (f.Interval > 0.0f)
                {
                    if (rt.Time > f.Interval)
                    {
                        force = V3{f.ForceDir[0], f.ForceDir[1], f.ForceDir[2]} * rt.RandomizedScale;
                        rt.Time = std::fmod(rt.Time, f.Interval);
                    }
                }
                else { force = V3{f.ForceDir[0], f.ForceDir[1], f.ForceDir[2]} * rt.RandomizedScale; }
                rt.Force = ForceToSim(f, force);
                break;
            }
            case KawaiiForceType::Gravity:
            {
                V3 force = f.UseOverrideGravityDirection ? SafeNormal(V3{f.OverrideGravityDirection[0], f.OverrideGravityDirection[1], f.OverrideGravityDirection[2]})
                                                         : V3{0, 0, -1};
                // (the character's gravity scale: KawaiiPhysics multiplies by the movement's signed GravityZ, which turns a
                // normal world's pull up; here its size)
                if (f.UseCharacterGravityScale && Env && Env->HasGravityZ) { force *= std::fabs(Env->GravityZ); }
                force *= rt.RandomizedScale;
                rt.Force = ConvertVectorSpace(KawaiiSpace::World, Cfg.SimulationSpace, force);
                break;
            }
            case KawaiiForceType::Curve:
            {
                rt.PrevTime = rt.Time;
                const float maxTime = f.ForceCurve.LastTime();
                const auto wrap = [&]() {
                    if (maxTime > 0.0f && rt.Time > maxTime) { rt.Time = std::fmod(rt.Time, maxTime); }
                };
                const auto value = [&](float t) {
                    const auto v = f.ForceCurve.Eval(t);
                    return V3{v[0], v[1], v[2]};
                };
                V3 force{};
                if (f.CurveEvaluateType == KawaiiCurveEvaluate::Single)
                {
                    rt.Time += dt * f.TimeScale;
                    wrap();
                    force = value(rt.Time) * rt.RandomizedScale;
                }
                else
                {
                    const int steps = std::max(f.SubstepCount, 1);
                    const float sub = dt * f.TimeScale / static_cast<float>(steps);
                    V3 acc{};
                    if (f.CurveEvaluateType == KawaiiCurveEvaluate::Max) { acc = {-3.402823466e+38f, -3.402823466e+38f, -3.402823466e+38f}; }
                    if (f.CurveEvaluateType == KawaiiCurveEvaluate::Min) { acc = {3.402823466e+38f, 3.402823466e+38f, 3.402823466e+38f}; }
                    for (int i = 0; i < steps; ++i)
                    {
                        rt.Time += sub;
                        wrap();
                        const V3 v = value(rt.Time);
                        if (f.CurveEvaluateType == KawaiiCurveEvaluate::Average) { acc += v; }
                        else if (f.CurveEvaluateType == KawaiiCurveEvaluate::Max) { acc = {std::max(acc.X, v.X), std::max(acc.Y, v.Y), std::max(acc.Z, v.Z)}; }
                        else { acc = {std::min(acc.X, v.X), std::min(acc.Y, v.Y), std::min(acc.Z, v.Z)}; }
                    }
                    if (f.CurveEvaluateType == KawaiiCurveEvaluate::Average) { acc = acc / static_cast<float>(steps); }
                    force = acc * rt.RandomizedScale;
                }
                rt.Force = ForceToSim(f, force);
                break;
            }
            case KawaiiForceType::Wind:
            {
                // the level's wind at each bone's pose, once a frame (its direction's noise drawn here too)
                rt.WindDir.assign(Bones.size(), V3{});
                rt.WindSpeed.assign(Bones.size(), -1.0f);
                if (!Env || !Env->Wind) { break; }
                for (size_t i = 0; i < Bones.size(); ++i)
                {
                    if (!CanApply(f, Bones[i])) { continue; }
                    WindSample w;
                    if (!Env->Wind(ConvertLocationSpace(Cfg.SimulationSpace, KawaiiSpace::World, Bones[i].PoseLocation), w)) { w = WindSample{}; }
                    const V3 dir = ConvertVectorSpace(KawaiiSpace::World, Cfg.SimulationSpace, w.Direction);
                    rt.WindDir[i] = f.WindDirectionNoiseAngle > 0.0f ? RandomCone(dir, DegreesToRadians(f.WindDirectionNoiseAngle), Random) : dir;
                    rt.WindSpeed[i] = w.Speed;
                }
                break;
            }
            case KawaiiForceType::ProceduralWind: PreApplyProceduralWind(rt, dt); break;
            }
        }
    }

    // ApplyToVelocity (Gravity), a bone a step
    void ApplyForcesToVelocity(const Bone& bone, V3& velocity) const
    {
        for (const auto& rt : Forces)
        {
            if (!rt.F.Enabled || rt.F.Type != KawaiiForceType::Gravity || !CanApply(rt.F, bone)) { continue; }
            velocity += rt.Force * ForceRate(rt.F, bone) * StepDt();
        }
    }

    // Apply (Basic, Curve, Wind, Procedural Wind), a bone a step: on its place
    void ApplyForces(Bone& bone, size_t index) const
    {
        const float dt = StepDt();
        for (const auto& rt : Forces)
        {
            const KawaiiExternalForce& f = rt.F;
            if (!f.Enabled) { continue; }
            switch (f.Type)
            {
            case KawaiiForceType::Basic:
            case KawaiiForceType::Curve:
            {
                if (!CanApply(f, bone)) { break; }
                const float rate = ForceRate(f, bone);
                const V3 force = f.Space == KawaiiForceSpace::Bone ? TransformVector(ForceBoneTransform(bone), rt.Force) : rt.Force;
                bone.Location += force * rate * dt;
                break;
            }
            case KawaiiForceType::Wind:
            {
                if (index >= rt.WindSpeed.size()) { break; }
                const float speed = rt.WindSpeed[index];
                if (speed <= KindaSmallNumber) { break; }
                bone.Location += rt.WindDir[index] * speed * ForceRate(f, bone) * rt.RandomizedScale * dt;
                break;
            }
            case KawaiiForceType::ProceduralWind:
            {
                if (!CanApply(f, bone) || rt.PublisherDisabled) { break; }
                constexpr float twoPi = Pi * 2.0f;
                const float ripple = f.RippleForce * std::sin(twoPi * rt.WTime / std::max(f.RipplePeriod, 0.01f) - DegreesToRadians(bone.LengthRateFromRoot * f.RippleTipPhaseDelay) +
                                                              DegreesToRadians(f.RipplePhaseOffset));
                const float total = (rt.CachedSines + ripple) * rt.CachedCycle + rt.CachedRandom + rt.CachedGust;
                const float rate = ForceRate(f, bone);
                const V3 vector = f.Space == KawaiiForceSpace::Bone ? TransformVector(ForceBoneTransform(bone), rt.CachedVector) : rt.CachedVector;
                bone.Location += vector * total * rate * dt;
                break;
            }
            case KawaiiForceType::Gravity: break;
            }
        }
    }

    // PostApply after each step: the one-shot forces go
    void PostApplyForces()
    {
        Forces.erase(std::remove_if(Forces.begin(), Forces.end(), [](const ForceRt& f) { return f.OneShot; }), Forces.end());
    }

    // ConsumeAndRemoveExpiredTransientExternalForces: the transient forces' time, the gusts asked for since
    void ConsumeTransientForces(float frameDelta)
    {
        for (auto& f : Forces)
        {
            if (f.Lifetime >= 0.0f) { f.Lifetime = std::max(0.0f, f.Lifetime - frameDelta); }   // (a transient one ends at 0)
        }
        Forces.erase(std::remove_if(Forces.begin(), Forces.end(), [](const ForceRt& f) { return f.Lifetime == 0.0f; }), Forces.end());
        if (PendingGusts.empty()) { return; }
        std::vector<GustRequest> gusts;
        gusts.swap(PendingGusts);
        for (const auto& g : gusts)
        {
            std::vector<const ForceRt*> sources;
            for (const auto& f : Forces)
            {
                if (f.F.IsWind() && f.Lifetime < 0.0f && f.Owner == 0) { sources.push_back(&f); }
            }
            const auto build = [&](const ForceRt* source) {
                ForceRt rt;
                KawaiiExternalForce& w = rt.F;
                w = KawaiiExternalForce{};
                w.Type = KawaiiForceType::ProceduralWind;
                if (source)
                {
                    w.ApplyBoneFilter = source->F.ApplyBoneFilter;
                    w.IgnoreBoneFilter = source->F.IgnoreBoneFilter;
                    w.ForceRateByBoneLengthRate = source->F.ForceRateByBoneLengthRate;
                    w.RandomForceScaleRange[0] = source->F.RandomForceScaleRange[0];
                    w.RandomForceScaleRange[1] = source->F.RandomForceScaleRange[1];
                    w.TimeScale = source->F.TimeScale;
                }
                if (!NearlyZero(g.Direction))
                {
                    w.Space = KawaiiForceSpace::World;
                    w.WindDirection[0] = g.Direction.X;
                    w.WindDirection[1] = g.Direction.Y;
                    w.WindDirection[2] = g.Direction.Z;
                }
                else if (source)
                {
                    w.Space = source->F.Space;
                    for (int k = 0; k < 3; ++k) { w.WindDirection[k] = source->F.WindDirection[k]; }
                    w.WindDirectionNoiseAngle = source->F.WindDirectionNoiseAngle;
                    w.WindDirectionNoisePeriod = source->F.WindDirectionNoisePeriod;
                    w.Seed = source->F.Seed;
                }
                rt.Lifetime = (g.Rise + g.Hold + g.Decay) / std::max(w.TimeScale, KindaSmallNumber) + 0.2f;
                rt.HasPendingGust = true;
                rt.PendingGust = WindGust{0.0f, g.Strength, g.Rise, g.Decay, g.Hold, true, false};
                if (Forces.size() < 64) { Forces.push_back(std::move(rt)); }
            };
            if (sources.empty()) { build(nullptr); }
            else
            {
                for (const ForceRt* s : sources) { build(s); }
            }
        }
    }

    // GetWindVelocity: the level's wind at the bone's pose (its gust and noise drawn once a frame)
    V3 NodeWindVelocity(const Bone& bone)
    {
        if (Cfg.WindScale == 0.0f || !Env || !Env->Wind) { return {}; }
        WindSample w;
        if (!Env->Wind(ConvertLocationSpace(Cfg.SimulationSpace, KawaiiSpace::World, bone.PoseLocation), w)) { return {}; }
        V3 direction = ConvertVectorSpace(KawaiiSpace::World, Cfg.SimulationSpace, w.Direction);
        if (!WindNoiseFresh)
        {
            WindNoiseFresh = true;
            WindGustFactor = Random.Range(0.0f, 2.0f);
            WindNoise = Cfg.WindDirectionNoiseAngle > 0.0f ? FromAxisAngle(RandomUnitVector(Random), Random.Range(0.0f, DegreesToRadians(Cfg.WindDirectionNoiseAngle))) : Q4{};
        }
        if (Cfg.WindDirectionNoiseAngle > 0.0f) { direction = Rotate(WindNoise, direction); }
        return direction * w.Speed * Cfg.WindScale * WindGustFactor;
    }

    static float UniformScale(const Xf& x)
    {
        const float s = (std::fabs(x.S.X) + std::fabs(x.S.Y) + std::fabs(x.S.Z)) / 3.0f;
        return s > KindaSmallNumber ? s : 1.0f;
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
        const KawaiiSettingsScale m = EffectiveSettingsScale();   // (3.18.0)
        for (auto& bone : Bones)
        {
            const float rate = bone.LengthRateFromRoot;
            bone.Damping = Clamp(Cfg.Damping * Cfg.DampingCurve.Eval(rate) * m.Damping, 0.0f, 1.0f);
            bone.WorldDampingLocation = Clamp(Cfg.WorldDampingLocation * Cfg.WorldDampingLocationCurve.Eval(rate) * m.WorldDampingLocation, 0.0f, 1.0f);
            bone.WorldDampingRotation = Clamp(Cfg.WorldDampingRotation * Cfg.WorldDampingRotationCurve.Eval(rate) * m.WorldDampingRotation, 0.0f, 1.0f);
            bone.Stiffness = Clamp(Cfg.Stiffness * Cfg.StiffnessCurve.Eval(rate) * m.Stiffness, 0.0f, 1.0f);
            bone.Radius = std::max(Cfg.Radius * Cfg.RadiusCurve.Eval(rate) * m.Radius, 0.0f);
            const float baseLimit = std::max(Cfg.LimitAngle * Cfg.LimitAngleCurve.Eval(rate), 0.0f);
            // (a limited bone stays limited, however small its multiplier: 0 is "no limit")
            bone.LimitAngle = baseLimit > 0.0f ? std::max(baseLimit * m.LimitAngle, KindaSmallNumber) : 0.0f;
        }
    }

    // ---- (3.18.0) settings multipliers (AnimNode_KawaiiPhysicsSimulation.cpp's) ----
    struct Multiplier
    {
        int64_t Handle = 0;
        KawaiiSettingsScale Scale;
        float Rise = 0, Hold = 0, Decay = 0, Elapsed = 0, PeakAlpha = 1.0f, DrivenAlpha = 0;
        bool Infinite = false, Driven = false;
        int LeaseEvaluations = 0, LeaseRemaining = 0;
        float LeaseBlendOut = 0.2f;
    };
    struct MultiplierRequest
    {
        int Kind = 0;   // 0 start, 1 push, 2 stop
        int64_t Handle = 0;
        KawaiiSettingsScale Scale;
        float Rise = 0, Hold = 0, Decay = 0, Alpha = 0, LeaseBlendOut = 0.2f;
        int Lease = 0;
        bool Infinite = false;
    };
    std::vector<Multiplier> Multipliers;
    std::vector<MultiplierRequest> PendingMultipliers;
    bool MultipliedLastUpdate = false;

  public:
    // KawaiiPhysics::EvaluateEnvelopeAlpha01: 0 -> 1 over rise, 1 for hold, 1 -> 0 over decay, 0 after
    static float EnvelopeAlpha(float rise, float hold, float decay, float elapsed)
    {
        if (elapsed < 0.0f) { return 0.0f; }
        rise = std::max(rise, 0.0f);
        hold = std::max(hold, 0.0f);
        decay = std::max(decay, 0.0f);
        if (rise > KindaSmallNumber && elapsed < rise) { return elapsed / rise; }
        if (elapsed < rise + hold) { return 1.0f; }
        if (decay <= KindaSmallNumber) { return 0.0f; }
        const float into = elapsed - rise - hold;
        return into < decay ? 1.0f - into / decay : 0.0f;
    }
    // KawaiiPhysics::ResolveWindGustEnvelope: a total time cut into rise, hold, decay
    static void ResolveEnvelope(float duration, float rise, float decay, float& outRise, float& outHold, float& outDecay)
    {
        outRise = outHold = outDecay = 0.0f;
        if (duration <= 0.0f) { return; }
        outRise = std::max(0.0f, rise);
        outDecay = std::max(0.0f, decay);
        const float edges = outRise + outDecay;
        if (edges > duration && edges > 0.0f)
        {
            const float scale = duration / edges;
            outRise *= scale;
            outDecay *= scale;
            return;
        }
        outHold = std::max(0.0f, duration - edges);
    }
    KawaiiSettingsScale EffectiveSettingsScale() const
    {
        KawaiiSettingsScale e;
        for (const auto& m : Multipliers)
        {
            float alpha = 0.0f;
            if (m.Driven) { alpha = m.DrivenAlpha; }
            else if (m.Infinite) { alpha = m.PeakAlpha * (m.Rise > 0.0f ? Clamp(m.Elapsed / m.Rise, 0.0f, 1.0f) : 1.0f); }
            else { alpha = m.PeakAlpha * EnvelopeAlpha(m.Rise, m.Hold, m.Decay, m.Elapsed); }
            e.Damping *= Lerp(1.0f, m.Scale.Damping, alpha);
            e.Stiffness *= Lerp(1.0f, m.Scale.Stiffness, alpha);
            e.WorldDampingLocation *= Lerp(1.0f, m.Scale.WorldDampingLocation, alpha);
            e.WorldDampingRotation *= Lerp(1.0f, m.Scale.WorldDampingRotation, alpha);
            e.Radius *= Lerp(1.0f, m.Scale.Radius, alpha);
            e.LimitAngle *= Lerp(1.0f, m.Scale.LimitAngle, alpha);
        }
        return e;
    }

  private:
    void StopMultiplierAt(size_t i, float blendOut)
    {
        if (i >= Multipliers.size()) { return; }
        Multiplier& m = Multipliers[i];
        if (blendOut <= KindaSmallNumber)
        {
            Multipliers.erase(Multipliers.begin() + static_cast<std::ptrdiff_t>(i));
            return;
        }
        if (m.Driven) { m.PeakAlpha = m.DrivenAlpha; }
        else
        {
            const float current = m.Infinite ? (m.Rise > 0.0f ? Clamp(m.Elapsed / m.Rise, 0.0f, 1.0f) : 1.0f) : EnvelopeAlpha(m.Rise, m.Hold, m.Decay, m.Elapsed);
            m.PeakAlpha *= current;
        }
        m.Infinite = m.Driven = false;
        m.DrivenAlpha = 0.0f;
        m.LeaseEvaluations = m.LeaseRemaining = 0;
        m.LeaseBlendOut = 0.2f;
        m.Rise = m.Hold = 0.0f;
        m.Decay = blendOut;
        m.Elapsed = 0.0f;
    }

    // The multipliers this evaluation: the ones on advanced first (one added now starts at its rise's start), then the
    // requests, the leases that ran out stopped, the finished ones gone. True while one is on.
    bool ConsumeAndAdvanceSettingsMultipliers(float frameDelta)
    {
        if (Multipliers.empty() && PendingMultipliers.empty()) { return false; }
        for (auto& m : Multipliers)
        {
            m.Elapsed += frameDelta;
            if (m.Driven && m.LeaseEvaluations > 0) { --m.LeaseRemaining; }
        }
        const auto find = [&](int64_t handle) -> Multiplier* {
            for (auto& m : Multipliers)
            {
                if (m.Handle == handle) { return &m; }
            }
            return nullptr;
        };
        std::vector<MultiplierRequest> requests;
        requests.swap(PendingMultipliers);
        // (KawaiiPhysics takes the pushes, then the starts, then the stops)
        for (int kind : {1, 0, 2})
        {
            for (const auto& r : requests)
            {
                if (r.Kind != kind) { continue; }
                if (kind == 1)
                {
                    Multiplier* m = find(r.Handle);
                    if (!m)
                    {
                        Multipliers.emplace_back();
                        m = &Multipliers.back();
                        m->Handle = r.Handle;
                    }
                    m->Scale = r.Scale;
                    m->DrivenAlpha = r.Alpha;
                    m->LeaseEvaluations = m->LeaseRemaining = r.Lease;
                    m->LeaseBlendOut = r.LeaseBlendOut;
                    m->Infinite = false;
                    m->Driven = true;
                    m->PeakAlpha = 1.0f;
                    m->Rise = m->Hold = m->Decay = m->Elapsed = 0.0f;
                }
                else if (kind == 0)
                {
                    Multiplier* m = r.Handle != 0 ? find(r.Handle) : nullptr;
                    if (!m)
                    {
                        Multipliers.emplace_back();
                        m = &Multipliers.back();
                    }
                    m->Scale = r.Scale;
                    m->Rise = r.Rise;
                    m->Hold = r.Hold;
                    m->Decay = r.Decay;
                    m->Elapsed = 0.0f;
                    m->PeakAlpha = 1.0f;
                    m->Handle = r.Handle;
                    m->Infinite = r.Infinite;
                    m->Driven = false;
                    m->DrivenAlpha = 0.0f;
                    m->LeaseEvaluations = m->LeaseRemaining = 0;
                    m->LeaseBlendOut = 0.2f;
                }
                else
                {
                    for (size_t i = Multipliers.size(); i-- > 0;)
                    {
                        if (Multipliers[i].Handle == r.Handle) { StopMultiplierAt(i, r.Decay); }
                    }
                }
            }
        }
        for (size_t i = Multipliers.size(); i-- > 0;)
        {
            const Multiplier& m = Multipliers[i];
            if (m.Driven && m.LeaseEvaluations > 0 && m.LeaseRemaining <= 0) { StopMultiplierAt(i, m.LeaseBlendOut); }
        }
        for (size_t i = Multipliers.size(); i-- > 0;)
        {
            const Multiplier& m = Multipliers[i];
            if (!m.Driven && !m.Infinite && m.Elapsed >= m.Rise + m.Hold + m.Decay) { Multipliers.erase(Multipliers.begin() + static_cast<std::ptrdiff_t>(i)); }
        }
        while (Multipliers.size() > 32) { Multipliers.erase(Multipliers.begin()); }
        return !Multipliers.empty();
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
            // its own shapes, then its sets' and physics asset's (KawaiiPhysics' *LimitsData), then the mirrored ones
            const std::pair<const std::vector<KawaiiLimit>*, int> lists[] = {{&Cfg.Spheres, 0},      {&Cfg.Capsules, 1},      {&Cfg.TaperedCapsules, 2},
                                                                             {&Cfg.Boxes, 3},        {&Cfg.Planes, 4},        {&Cfg.DataSpheres, 0},
                                                                             {&Cfg.DataCapsules, 1}, {&Cfg.DataTaperedCapsules, 2}, {&Cfg.DataBoxes, 3},
                                                                             {&Cfg.DataPlanes, 4}};
            const auto add = [&](const KawaiiLimit& limit, int kind) {
                Shape s;
                s.L = limit;
                s.Kind = kind;
                s.DrivingBone = limit.Bone.empty() ? -1 : Skel->Find(limit.Bone);
                Shapes.push_back(s);
            };
            for (const auto& [list, kind] : lists)
            {
                for (const auto& limit : *list) { add(limit, kind); }
            }
            if (Cfg.MirrorLimits.Active())
            {
                MakeMirroredLimits();
                for (const auto& [kind, limit] : ExtraLimits) { add(limit, kind); }
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
            if (!Shapes[k].Enable) { continue; }
            CollideWith(bone, Shapes[k], boneIndex * Shapes.size() + k);
        }
    }

    // (3.18.0) the shapes from outside the node (no side kept for them)
    void AdjustByOuterShapes(Bone& bone)
    {
        for (const auto& s : OuterShapes)
        {
            if (s.Enable) { CollideWith(bone, s, static_cast<size_t>(-1)); }
        }
    }

    // One shape against one bone (`memory`: its kept side's place; -1: none)
    void CollideWith(Bone& bone, const Shape& s, size_t memory)
    {
        {
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
            case 5:
            {
                // (3.18.0) AdjustByConvexCollision: out along the plane the bone is farthest past (an intended
                // approximation near edges and corners, as KawaiiPhysics')
                if (s.Planes.empty()) { break; }
                const float radius = bone.Radius;
                const Xf frame{s.R, s.Location, {1, 1, 1}};
                const V3 local = InverseTransformPosition(frame, bone.Location);
                float distSq = 0.0f;
                for (int a = 0; a < 3; ++a)
                {
                    if (local[a] < s.BoundsMin[a]) { distSq += (local[a] - s.BoundsMin[a]) * (local[a] - s.BoundsMin[a]); }
                    else if (local[a] > s.BoundsMax[a]) { distSq += (local[a] - s.BoundsMax[a]) * (local[a] - s.BoundsMax[a]); }
                }
                if (distSq > radius * radius) { break; }
                float maxDist = -3.402823466e+38f;
                V3 best;
                for (const auto& p : s.Planes)
                {
                    const float d = p[0] * local.X + p[1] * local.Y + p[2] * local.Z - p[3];
                    if (d > maxDist)
                    {
                        maxDist = d;
                        best = {p[0], p[1], p[2]};
                    }
                }
                if (maxDist < radius) { bone.Location = TransformPosition(frame, local + best * (radius - maxDist)); }
                break;
            }
            default: break;
            }
        }
    }

    // (3.18.0) AdjustByWorldCollision: a sphere sweep from the bone's last place to its new one through the level (the
    // game's, a budget of sweeps a frame); it stops where the sweep hits
    void AdjustByWorldCollision(Bone& bone)
    {
        if (!Env || !Env->Sweep || (bone.Parent < 0 && !bone.BridgeDummy) || bone.Radius <= KindaSmallNumber) { return; }
        if (Env->SweepBudget)
        {
            if (*Env->SweepBudget <= 0) { return; }
            --*Env->SweepBudget;
        }
        ++Sweeps;
        const V3 start = ConvertLocationSpace(Cfg.SimulationSpace, KawaiiSpace::World, bone.PrevLocation);
        const V3 end = ConvertLocationSpace(Cfg.SimulationSpace, KawaiiSpace::World, bone.Location);
        V3 hit;
        if (Env->Sweep(start, end, bone.Radius * UniformScale(ComponentToWorld), hit)) { bone.Location = ConvertLocationSpace(KawaiiSpace::World, Cfg.SimulationSpace, hit); }
    }

    // (3.18.0) The outside shapes of this frame in the simulation space: the floor and the level's (its world collision's
    // settings), the shared shapes of the character's other meshes (its use_shared_collision; a source does not take
    // them).
    void UpdateOuterShapes()
    {
        OuterShapes.clear();
        if (!Env) { return; }
        const float inverseScale = 1.0f / UniformScale(ComponentToWorld);
        const auto add = [&](const std::vector<WorldShape>* list) {
            if (!list) { return; }
            for (const auto& w : *list)
            {
                if (OuterShapes.size() >= 512) { return; }
                Shape s;
                s.Kind = w.Kind;
                s.Location = ConvertLocationSpace(KawaiiSpace::World, Cfg.SimulationSpace, w.Location);
                s.R = Normalized(ConvertRotationSpace(KawaiiSpace::World, Cfg.SimulationSpace, w.Rotation));
                s.L.Radius = w.Radius * inverseScale;
                s.L.Length = w.Length * inverseScale;
                s.L.Radius0 = w.Radius0 * inverseScale;
                s.L.Radius1 = w.Radius1 * inverseScale;
                s.L.Extent[0] = w.Extent.X * inverseScale;
                s.L.Extent[1] = w.Extent.Y * inverseScale;
                s.L.Extent[2] = w.Extent.Z * inverseScale;
                s.L.Inner = w.Inner;
                if (w.Kind == 5)
                {
                    s.Planes = w.Planes;
                    for (auto& p : s.Planes) { p[3] *= inverseScale; }
                    s.BoundsMin = w.BoundsMin * inverseScale;
                    s.BoundsMax = w.BoundsMax * inverseScale;
                }
                if (w.Kind == 4) { s.P = Plane::Through(s.Location, AxisZ(s.R)); }
                s.Enable = true;
                OuterShapes.push_back(std::move(s));
            }
        };
        const auto& world = Cfg.World;
        if ((world.UseSimpleWorldCollision && world.GroundCollision) || world.GroundOnly) { add(Env->Ground); }
        if (world.UseSimpleWorldCollision) { add(Env->LevelShapes); }
        if (Cfg.UseSharedCollision && !Cfg.SharedCollisionSource && Env->Shared) { add(Env->Shared(Cfg.SharedCollisionGroupTag)); }
        // (their caches: as the node's own shapes')
        for (auto& s : OuterShapes)
        {
            const KawaiiLimit& l = s.L;
            switch (s.Kind)
            {
            case 1:
                s.Start = s.Location + AxisZ(s.R) * (l.Length * 0.5f);
                s.End = s.Location + AxisZ(s.R) * (l.Length * -0.5f);
                s.FallbackPushDir = AxisX(s.R);
                break;
            case 2:
                s.Start = s.Location + AxisZ(s.R) * (l.Length * 0.5f);
                s.End = s.Location - AxisZ(s.R) * (l.Length * 0.5f);
                s.Segment = s.End - s.Start;
                s.SegmentSizeSq = SizeSq(s.Segment);
                s.FallbackPushDir = AxisX(s.R);
                break;
            case 3: s.Box = Xf{s.R, s.Location, {1, 1, 1}}; break;
            case 4: s.Normal = AxisZ(s.R); break;
            default: break;
            }
        }
    }

    // (3.18.0) KawaiiPhysics' ApplyMirrorLimits: the node's shapes (own, then its sets') on a bone with a mirror bone,
    // copied onto it mirrored across the axis (AppendMirroredLimits); a bone that has a shape of its own already is
    // left (skip_mirrored_bone_with_existing_collision).
    void MakeMirroredLimits()
    {
        ExtraLimits.clear();
        const SkelCompat::KawaiiMirror& m = Cfg.MirrorLimits;
        const int axis = static_cast<int>(m.Axis);
        const auto mirrorName = [&](const std::wstring& name) -> int {
            const int self = Skel->Find(name);
            if (self < 0) { return -1; }
            // (not "check": UE's macro of that name, in the End editor's build)
            const auto otherBone = [&](const std::wstring& other) {
                const int b = Skel->Find(other);
                return b >= 0 && b != self ? b : -1;
            };
            for (const auto& [a, b] : m.Pairs)
            {
                if (SkelCompat::NameEquals(a, name)) { return otherBone(b); }
                if (SkelCompat::NameEquals(b, name)) { return otherBone(a); }
            }
            const auto starts = [](const std::wstring& text, const std::wstring& part) {
                return text.size() > part.size() && SkelCompat::NameEquals(std::wstring_view(text).substr(0, part.size()), part);
            };
            const auto ends = [](const std::wstring& text, const std::wstring& part) {
                return text.size() > part.size() && SkelCompat::NameEquals(std::wstring_view(text).substr(text.size() - part.size()), part);
            };
            for (const auto& [a, b] : m.Prefixes)
            {
                if (starts(name, a)) { return otherBone(b + name.substr(a.size())); }
                if (starts(name, b)) { return otherBone(a + name.substr(b.size())); }
            }
            for (const auto& [a, b] : m.Suffixes)
            {
                if (ends(name, a)) { return otherBone(name.substr(0, name.size() - a.size()) + b); }
                if (ends(name, b)) { return otherBone(name.substr(0, name.size() - b.size()) + a); }
            }
            return -1;
        };
        const auto refRotation = [&](int b) {
            return static_cast<size_t>(b) < Skel->RefRotation.size() ? Skel->RefRotation[static_cast<size_t>(b)] : BoneCS(b).R;
        };
        const std::pair<const std::vector<KawaiiLimit>*, const std::vector<KawaiiLimit>*> kinds[] = {
            {&Cfg.Spheres, &Cfg.DataSpheres}, {&Cfg.Capsules, &Cfg.DataCapsules}, {&Cfg.TaperedCapsules, &Cfg.DataTaperedCapsules}, {&Cfg.Boxes, &Cfg.DataBoxes}, {&Cfg.Planes, &Cfg.DataPlanes}};
        for (int kind = 0; kind < 5; ++kind)
        {
            const auto& own = *kinds[kind].first;
            const auto& data = *kinds[kind].second;
            const auto hasShape = [&](const std::wstring& bone) {
                const auto on = [&](const KawaiiLimit& l) { return SkelCompat::NameEquals(l.Bone, bone); };
                return std::any_of(own.begin(), own.end(), on) || std::any_of(data.begin(), data.end(), on);
            };
            for (const auto* list : {&own, &data})
            {
                for (const KawaiiLimit& source : *list)
                {
                    if (source.Bone.empty()) { continue; }
                    const int target = mirrorName(source.Bone);
                    if (target < 0) { continue; }
                    const std::wstring& targetName = Skel->Names[static_cast<size_t>(target)];
                    if (m.SkipExisting && hasShape(targetName)) { continue; }
                    const int sourceBone = Skel->Find(source.Bone);
                    const Q4 sourceRef = refRotation(sourceBone), targetRef = refRotation(target);
                    KawaiiLimit made = source;
                    made.Bone = targetName;
                    const V3 offset{source.Offset[0], source.Offset[1], source.Offset[2]};
                    const V3 moved = Unrotate(targetRef, MirrorVector(Rotate(sourceRef, offset), axis));   // MirrorOffsetLocation
                    made.Offset[0] = moved.X;
                    made.Offset[1] = moved.Y;
                    made.Offset[2] = moved.Z;
                    const Q4 offsetRotation = FromRotator(source.Rotation[0], source.Rotation[1], source.Rotation[2]);
                    const Q4 turned = Normalized(Inverse(targetRef) * MirrorQuat(sourceRef * offsetRotation, axis) * Inverse(MirrorQuat(sourceRef, axis)) * targetRef);
                    QuatToRotator(turned, made.Rotation[0], made.Rotation[1], made.Rotation[2]);
                    if (kind == 2)
                    {
                        // PreserveMirroredEndpointMeaning: its +Z end stays the mirror of the source's
                        const V3 expected = SafeNormal(MirrorVector(AxisZ(sourceRef * offsetRotation), axis));
                        const V3 made_ = SafeNormal(AxisZ(targetRef * FromRotator(made.Rotation[0], made.Rotation[1], made.Rotation[2])));
                        if (Dot(expected, made_) < 0.0f) { std::swap(made.Radius0, made.Radius1); }
                    }
                    ExtraLimits.emplace_back(kind, made);
                }
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
        // its own and its sets' (KawaiiPhysics' MergedBoneConstraints: BoneConstraints + BoneConstraintsData)
        for (const auto* list : {&Cfg.BoneConstraints, &Cfg.DataBoneConstraints})
        {
            for (const auto& c : *list)
            {
                Constraint one;
                one.Name1 = c.Bone1;
                one.Name2 = c.Bone2;
                one.OverrideCompliance = c.OverrideCompliance;
                one.Compliance = c.Compliance;
                one.ExcludeFromSubdivision = c.ExcludeFromSubdivision;
                Constraints.push_back(one);
            }
        }
        // (3.18.0) its sets' regex patterns (UKawaiiPhysicsBoneConstraintsDataAsset::ApplyRegex, run here on the model's
        // bones: the list "Bone1, Bone2, ..." searched with both patterns, the n-th match of the first paired with the
        // n-th of the second)
        if (!Cfg.ConstraintPatterns.empty() && Skel)
        {
            std::wstring list;
            for (const auto& name : Skel->Names) { list += name + L", "; }
            for (const auto& [first, second] : Cfg.ConstraintPatterns)
            {
                try
                {
                    const std::wregex p1(first), p2(second);
                    auto m1 = std::wsregex_iterator(list.begin(), list.end(), p1);
                    auto m2 = std::wsregex_iterator(list.begin(), list.end(), p2);
                    const std::wsregex_iterator end;
                    for (; m1 != end && m2 != end && Constraints.size() < SkelCompat::MaxKawaiiBoneConstraints; ++m1, ++m2)
                    {
                        Constraint one;
                        one.Name1 = m1->str(0);
                        one.Name2 = m2->str(0);
                        if (one.Name1.empty() || one.Name2.empty() || SkelCompat::NameEquals(one.Name1, one.Name2)) { continue; }
                        Constraints.push_back(one);
                    }
                }
                catch (...)
                {
                    // (a pattern the regex engine does not take: none from it)
                }
            }
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
        // (3.18.0) the external forces' PreApply, once a frame
        if (!Forces.empty()) { PreApplyForces(); }
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
        for (size_t i = 0; i < Bones.size(); ++i)
        {
            Bone& bone = Bones[i];
            if (bone.SkipSimulate || (bone.InterBoneDummy && Cfg.BoneSubdivisionCollisionOnly) || bone.BridgeDummy) { continue; }
            Simulate(bone, exponent, i);
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
        // (3.18.0) the external forces' PostApply (the one-shot ones go after their step)
        if (!Forces.empty()) { PostApplyForces(); }
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
            if (!OuterShapes.empty()) { AdjustByOuterShapes(Bones[i]); }   // (3.18.0) ground, level, shared
            if (Cfg.World.AllowWorldCollision) { AdjustByWorldCollision(Bones[i]); }
        }
        ApplyBridgeDummyCollisionFeedback();
        if (Cfg.BoneConstraintIterationsAfterCollision > 0)
        {
            for (auto& c : Constraints) { c.Lambda = 0.0f; }
            for (int i = 0; i < Cfg.BoneConstraintIterationsAfterCollision; ++i) { AdjustByBoneConstraints(); }
        }
        RestoreBoneLengthsAndLimits();
    }

    void Simulate(Bone& bone, float exponent, size_t index)
    {
        const Bone& parent = Bones[static_cast<size_t>(bone.Parent)];
        // (3.18.0) the level's wind (the node's enable_wind), added to the speed after its damping
        const V3 wind = Cfg.EnableWind ? NodeWindVelocity(bone) * static_cast<float>(Framerate()) : V3{};
        // ComputeVerletStepVelocity
        V3 velocity = (bone.Location - bone.PrevLocation) / std::max(DeltaTimeOld, KindaSmallNumber);
        bone.PrevLocation = bone.Location;
        velocity *= (1.0f - bone.Damping);
        velocity += wind;
        const float dt = StepDt();
        if (!Cfg.UseLegacyGravity) { velocity += GravityInSimSpace * dt; }
        else { bone.Location += GravityInSimSpace * (0.5f * dt * dt); }
        if (!Forces.empty()) { ApplyForcesToVelocity(bone, velocity); }   // (3.18.0) Gravity forces
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
        // (3.18.0) the external forces on its place
        if (!Forces.empty()) { ApplyForces(bone, index); }
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
        // (3.18.0) the node's alpha: its result blended with the pose it read (FCSPose::LocalBlendCSBoneTransforms,
        // FTransform::Blend: places and scales straight, rotations by FQuat::FastLerp)
        const float alpha = CurrentAlpha();
        const bool blend = alpha < 1.0f - 0.00001f;
        for (size_t i = 0; i < Bones.size(); ++i)
        {
            const int mesh = Bones[i].MeshIndex;
            if (mesh < 0 || Bones[i].Dummy || static_cast<size_t>(mesh) >= Pose->size()) { continue; }
            Xf& target = (*Pose)[static_cast<size_t>(mesh)];
            if (blend)
            {
                const Xf& a = target;
                const Xf& b = out[i];
                const float bias = (a.R.X * b.R.X + a.R.Y * b.R.Y + a.R.Z * b.R.Z + a.R.W * b.R.W) >= 0.0f ? 1.0f : -1.0f;
                const float k = bias * (1.0f - alpha);
                const Q4 r = Normalized({b.R.X * alpha + a.R.X * k, b.R.Y * alpha + a.R.Y * k, b.R.Z * alpha + a.R.Z * k, b.R.W * alpha + a.R.W * k});
                target = Xf{r, Lerp(a.T, b.T, alpha), Lerp(a.S, b.S, alpha)};
            }
            else { target = out[i]; }
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
    // (3.18.0) the nodes a trigger's filter tags pick (KawaiiPhysics' CollectKawaiiPhysicsNodes: none, every node)
    template <class F>
    void ForTagged(const std::vector<std::wstring>& tags, bool exact, F&& f)
    {
        for (auto& n : Nodes)
        {
            if (SkelCompat::Detail::KawaiiTagFilterPasses(n.Settings().Tag, tags, exact)) { f(n); }
        }
    }

    // `changed` (out): the bones whose transforms the nodes changed (theirs and the bones below them). Returns how many
    // nodes ran.
    int Evaluate(const Skeleton& skel, std::vector<Xf>& pose, std::vector<uint8_t>& changed, const Xf& component, float delta, const std::vector<uint8_t>* skip,
                 const Environment* env = nullptr)
    {
        int ran = 0;
        changed.assign(pose.size(), 0);
        for (auto& node : Nodes)
        {
            Before = pose;
            Set.assign(pose.size(), 0);
            if (!node.Evaluate(skel, pose, Set, component, delta, skip, env)) { continue; }
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
