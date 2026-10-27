// RM_Surface rebuilt: the dither noise. The game reads its spatiotemporal blue noise (128 x 128 x 64) at
// (pixel x & 127, pixel y & 127, (frame & 7) + the primitive's context); the engine's copy of that noise is stored as a
// 128 x 8192 image (the 64 slices stacked).
#if PIXELSHADER
uint2 p = uint2(Parameters.SvPosition.xy) & 127u;
uint z = (View.FrameNumber & 7u) & 63u;
return STBN.Load(int3(p.x, p.y + z * 128u, 0));
#else
return float4(0.5, 0.5, 0.5, 0.5);
#endif
