#include "harness.hpp"
#include "s3520.cpp"
#include <random>
using namespace cpuglsl;
int main()
{
    std::mt19937 rng(1);
    std::uniform_real_distribution<double> u(0, 1);
    for (auto n : {"View", "Primitive"}) for (int i = 0; i < 1024; ++i) ubo(n)._m0[i] = vec4(D(u(rng)), D(u(rng)), D(u(rng)), D(u(rng)));
    Inputs in;
    auto rv = [&](double s) { return vec4(D(u(rng) * 2 - 1, s * (u(rng) - .5), s * (u(rng) - .5)), D(u(rng) * 2 - 1, s * (u(rng) - .5), s * (u(rng) - .5)),
                                           D(u(rng) * 2 - 1, s * (u(rng) - .5), s * (u(rng) - .5)), D(u(rng) * 2 - 1, s * (u(rng) - .5), s * (u(rng) - .5))); };
    in.v["TEXCOORD_10"] = rv(0.01); in.v["TEXCOORD_11"] = rv(0.01); in.v["TEXCOORD"] = rv(0.002);
    in.v["CONSTANT_CONTEXT"] = vec4(D(3.0)); in.v["CURRENT_CLIP_SPACE_POSITION"] = rv(0.001); in.v["PREVIOUS_CLIP_SPACE_POSITION"] = rv(0.001);
    gl_FragCoord = vec4(D(100.5, 1, 0), D(200.5, 0, 1), D(0.3), D(1.0));
    S3520::set_inputs(in);
    S3520::run();
    Outputs o; S3520::get_outputs(o);
    for (auto& [k, v] : o.v) printf("%s = %.6f %.6f %.6f %.6f\n", k.c_str(), v.x.v, v.y.v, v.z.v, v.w.v);
}
