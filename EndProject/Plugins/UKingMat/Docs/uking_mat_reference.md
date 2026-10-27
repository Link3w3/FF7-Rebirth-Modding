# uking_mat (Breath of the Wild, Wii U) — reverse-engineering reference

Everything below was recovered from `uking_mat.product.bfsha/.sbfsha` (NintendoWare FSHA 4.5.0.4) by
decompiling the Latte (R700) microcode of its programs and checking hypotheses numerically against
the decompiled shaders. Items marked *(inferred)* are not fully pinned down.

## Archive
- 1 shading model `uking_mat`; 407 static options, 4 dynamic (gsys_weight, gsys_assign_type,
  gsys_assign_variation, system_id); 13188 programs = 1099 option sets × 12.
- Assign types: visualize (debug), material (forward), zonly (depth/shadow), gbuffer (deferred).
  - gbuffer var0 = plain G-buffer; var1 = + gameplay effects (mimicry, chemical ice, mottled,
    special effect A/B/C, proc discard); var2 = + damage colour.
  - material var0 = forward lighting; var1 = cook/burn overlay; var2 = simple forward.
- Samplers: texture slots 0..5 = `_a0 _s0 _n0 _e0 _t0 _a1`; vertex texture `_v0`; arrays `array0/1`.
- Material block `gsys_material` (616 B). Defaults: const_color* = 1, const_value* = 1,
  const_vector* = 0, tex_srt = identity (tex_srt3 = ×100), indirect_scale = 1,
  wind intensity 0.1 / lie intensity 3 / lie height 0.5.

## Texture coordinates
- `uking_texcoordN_mapping`: 0..3 → `_u0.._u3`; 11 → world XZ; 20..25 → texcoord set N−20;
  100..115 → constant (source code); 10 unknown (1 option set).
- srt k (uniform `tex_srtk`, column-major 2×3): `u' = u*m0.x + v*m0.z + m1.x`,
  `v' = u*m0.y + v*m0.w + m1.y`. The engine builds it from the BFRES TexSrt with the
  NintendoWare Maya formula (identity → (1, −0, 0, 1 | 0, 0), matching the archive default).
- offset_srt k': matrices `srt_k + srt_k' * object_random` (object random = gsys_shape[3].y).
- Texture select (`uking_textureN_texcoord`): 0,1,2 → sets 0–2; 6,7,8 → sets 3–5; 3,4,5 → proctexcoord 0–2.
- Proctexcoord mapping: 0 = matcap `(N.x*0.5+0.5, −N.y*0.5+0.5)` (final normal, view space);
  3 = sphere map of `R = reflect(eye→surface, N_raw)`; 1 = screen uv (scene colour/depth); 2 = lumberjack.
- Toon-spec coordinate: `t = srt(mapping).x`; pattern uses `(t, 0.7 t)`.
- Bake uv: `_u1 * gsys_bake_stK.xy + gsys_bake_stK.zw`.

## Texture fetch / decode
- decode 0 raw; 1 signed all channels (`x*2.007874 − 1.007874` = 255/127, −128/127);
  2 normal map (signed xy, `z = sqrt(1 − sat(x²+y²))`, w raw).
- texture6/7 = re-fetch of slot `uking_textureN_texture` with their own texcoord.
- Texture arrays: `tex(arrayN, (u, v, round(texture_array_indexS)))`.
- Indirect K (`uking_enable_indirectK`): slot K sampled at its *undistorted* texcoord, decoded with
  its own decode; offset added to texcoord set `uking_indirectK_texcoord` (all slots using that set):
  - type 0: `indirect_scaleK.xy * v.xy`, v signed only if signed_fetch and decode = 0.
  - type 1 (parallax): `scale * h * (dot(T, e2s), dot(cross(N, T), e2s))`, h raw.
  - world_scaling: offset `/= (view_depth * gsys_context[17].y)`.

## Sources (SET0)
| code | value |
|---|---|
| 0..5 | texture slots; 6, 7 = texture6/7 |
| 8, 9 | scene colour 0/1 (screen-space colour buffer) |
| 100..103, 112, 113 | const_color0..5 |
| 104..111 | const_value0..7 (broadcast) |
| 114, 115 | const_vector0/1 |
| 200..213 | combiner outputs color0..13 |
| 300 | vertex colour `_c0` |
| 400..406 | 0, 0.5, 1, 2, 4, 0.25, 0.75 |
| 500 | scene linear depth − pixel depth |
| 502 | `sat(1 + dot(N_geo, normalize(Vpos)))` (rim, geometric normal) |
| 503 | `sat(1 + dot(N_raw, normalize(Vpos)))` (rim, normal-mapped) |
| 504 | view depth `−Vpos.z` |
| 507 | uking_dynamic_exposure |
| 508 | `1 / (depth * gsys_context[17].y)` |
| 509 | time (gsys_environment[41].x) |
| 510 | per-object random (gsys_shape[3].y) |
| 511 | inner light (see below) |
| 513 | N·L = `−dot(L, N_raw)` |
| 514 | N·H = `−dot(N_raw, normalize(normalize(Vpos) + L_raw)) * ratio` |
| 515 | `dot(normalize(Vpos), L)` |

- `N_raw` = `T*x + B*y + N*z` (unnormalized, B = cross(N, T)·tangent.w), or `normalize(N_geo)`
  without a normal map; normalized when normal modify is active.
- Combiners with `before_normal = 0` see 503/511/513/514 as 0.

## Channels (SET2)  `code = comp*10 + mod`
comp 0 rgba, 1..4 r/g/b/a broadcast; mod 0 x, 1 1−x, 2 −x, 3 x−1; 2000 = normal-map decode.
1000-series unused by BotW assets.

## Combiner calc types (SET1), then saturate if `clamp01`
| | | | |
|---|---|---|---|
| 0 A | 1 A+B | 2 A·B | 4 lerp(A,B,C) |
| 5 (A+B)·C | 6 A·B+C·D | 7 pow(A,B) | 8 A·B+C |
| 9 A·B·C | 10 A+B+C+D | 11 A·B·C·D | 12 lerp(A,B,C)·D |
| 13 A·0.498+0.502 (encode) | 14 A·2.0079−1.0079 (decode) | 15 lerp(A,B,C)+D | 16 (A+B)·C+D |
| 17 A+B+C | 18 (A+B)·C·D | 19 (A+B+C)·D | 21 (A·B+C)·D |
| 25 normalize(lerp(A,B,C)) | 26 normalize(A.xy + B.xy·C, A.z) *(C role inferred)* | 27 lerp(A·D,B,C) | 28 pow(A,B)·C+D |
| 29 sin(2π(A·B+C))·D | 30 cos(2π(A·B+C))·D | | |

Never used by BotW assets: 3, 20, 22, 23, 24, 31, 32. Only combiners 0..11 are ever enabled.
Evaluation: in index order; a combiner never references a later one.

## Normal
- `uking_enable_normalmap`: nm = src(normal_color) (+ decode if enable_decode_normalmap).
- normalmap2: r = srcch(blend_ratio, blend_channel).x; method 0 `normalize(lerp(n1, n2, r))`;
  method 1 `normalize(n1.xy + r·n2.xy, n1.z)` (n2 signed).
- Normal modify type 1 (foliage, only with a normal map): `N' = normalize(N + w·normalize(P − C))`,
  C/w from vtx_normal_modify_A (const_vector0), T' = cross(cross(N', T), N'), B' = cross(N', T)·w.
- calc_binormal_vertex uses a vertex binormal attribute.

## Outputs (G-buffer)
- RT0 = (material id, object attribute, view N.z or id, alpha); RT1 = albedo, behave data;
  RT2 = view normal·0.5+0.5 (length encodes AO: 0.75 + 0.25·AO), w = specmask 6 bits + 2 flag bits;
  RT3 = emission.
- albedo = src(albedo_color); × AO.x (× bake shadow `_t0` at bake uv when bake_shadow_type 0) only
  when the AO source is 300 (vertex colour).
- specmask = srcch(specmask_scaler, specular_channel).x; with a toon-spec srt:
  behave 0 `× p²`, behave 2/10 `× sat(p² + metal)`, `p = sat(1−(frac(t)−.5)²)·sat(1−(frac(.7t)−.5)²)`.
- behave: 0 generic, 1 toon chara, 2 metal (metal > 0.5 → shiny id, metal bits in RT1.w), 10, 100 hair
  (Kajiya-style highlight in RT1.w), 101–105 (105 foliage).
- Translucent G-buffer programs (renderstate 2) blend their values with the existing G-buffer.
- `gsys_force_zprepass` programs write alpha = 1 (alpha test happens in the pre-pass).

## Inner light (source 511)
Sphere (or capsule, `enable_inner_light_line`) light at const_vector (local), radius r(t), diffusivity k:
eye ray refracted with IOR 1.5 (`T = refract(e2s, N_raw, 1.5)`, 0 on total internal reflection);
`511 = (1/r_c²)·sat(r_c²/|L_c|²)·(k·sat(−N·L̂_c) + (1−k)·sat(T·P̂)^8)` where c is the closest point of the
segment to the surface and P the point of the light closest to the refracted ray.

## Vertex stage
- Position modify type 1: `P_local += n_local · calc(A..D)` (sources SET3: 0 = vertex texture `_v0`,
  100..115 constants, 300 vertex colour, 4xx); types 0/2 and shadow_only have no effect here.
- Wind (`uking_enable_wind_vtx_transform`), BotW world space, w = srcch(vc, wind channel):
  `amp = 20·(w·intensity + w'·flutter)`, flutter = `sat(s−0.5)·sin(7t)sin(5t)sin(3t)·0.05`,
  t = `(time + 0.5w)·100π`; gust g = jitter + LUT(gsys_user1) along the wind direction(s);
  `Δxz = amp·lerp(dir1·g1, dir2·g2, blend)`, `Δy = −max(0.16·(amp·g)³, 0)`.
  Variants: normal_lock (remove inward component), lie (grass lie-down map, w' = sat(w − lie_height)),
  height (w = max(local y, 0)), coreinfo (pivot from `_c1`), scale (× object Y scale).

## Forward lighting (material var0, generic)
`lit = albedo'·(ambient + toonStep·shadow·lerp(0.8·ambient, sun, shadow))`,
`toonStep = sat((sat(N·L) − 0.4)·75·…)`, `albedo' = sat(albedo·1.0732098 − 0.000528556)·0.9317843 + 0.0004925`.
Behave 1 toon glint: `H = normalize(−1.5 L.x, 0.6, 1)`, `p = pow(sat(N·H), e^(spec²+3))`,
`spec = sat(sat((p−.005)·100)·.2 + sat((p−.14)·70)·.3)·spec²·8`, added ×3·shadow·sat(N·L+0.9).
BotW's deferred lighting pass is not part of this archive.
