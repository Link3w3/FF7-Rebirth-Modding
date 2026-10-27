// RM_Surface rebuilt: the dither noise. The game reads its spatiotemporal blue noise (128 x 128 x 64; the engine's copy
// is a 128 x 8192 image, the 64 slices stacked) at (pixel x & 127, pixel y & 127, (frame & 7) + the primitive's context).
// Hair is done the HairDitherFix 2.0 way: every one of the 64 slices (the game takes 8) and the noise anchored to the
// texture coordinates (hashed alpha: one noise cell about one pixel along each UV axis), so the strands keep the game's
// cut-offs without crawling grain. Inputs: STBN (the noise image), UV (the coverage's UV0), Hair (the Hair switch, 1/0).
#if PIXELSHADER
uint Frame = View.FrameNumber;
uint2 p = uint2(Parameters.SvPosition.xy) & 127u;
uint z = Frame & 7u;
if (Hair > 0.5)
{
	float2 Footprint = max(max(abs(ddx_coarse(UV)), abs(ddy_coarse(UV))), 9.99999997e-07);
	float2 Cell = floor(UV * exp2(-round(log2(Footprint))));
	p = uint2(int2(Cell)) & 127u;
	z = Frame & 63u;
}
return STBN.Load(int3(p.x, p.y + z * 128u, 0));
#else
return float4(0.5, 0.5, 0.5, 0.5);
#endif
