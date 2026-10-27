#include "../src/SkelCompatCore.hpp"
#include <cstdio>
using namespace SkelCompat::Shooter;
int main()
{
    int fails = 0;
    // DualSense USB: r[0]=1, LX r[1], LY r[2], RX r[3], RY r[4], L2 r[5], R2 r[6], b0 r[8]
    uint8_t in[64]{};
    in[0] = 0x01; in[1] = 0; in[2] = 255; in[3] = 128; in[4] = 128; in[8] = 0x08;   // left stick full left and down, hat neutral
    PadRead read;
    if (!ReadPadReport(in, sizeof(in), PadKind::DualSenseUsb, 0, read)) { ++fails; puts("read"); }
    if (!(read.LX < -0.99f && read.LY < -0.99f)) { ++fails; printf("LX %f LY %f\n", read.LX, read.LY); }
    if (in[1] != 0) { ++fails; puts("changed without centre"); }
    ReadPadReport(in, sizeof(in), PadKind::DualSenseUsb, 0, read, 1.0f, 0, true);
    if (in[1] != 128 || in[2] != 128 || in[3] != 128 || in[4] != 128) { ++fails; puts("not centred"); }
    if (!(read.LX < -0.99f)) { ++fails; puts("read after centre should be the controller's"); }
    // DualSense Bluetooth: r[0]=0x31, LX r[2], LY r[3], RX r[4], RY r[5]
    uint8_t bt[78]{};
    bt[0] = 0x31; bt[2] = 255; bt[3] = 0; bt[4] = 128; bt[5] = 128; bt[9] = 0x08;
    ReadPadReport(bt, sizeof(bt), PadKind::DualSenseBt, 0, read);
    if (!(read.LX > 0.99f && read.LY > 0.99f)) { ++fails; printf("BT LX %f LY %f\n", read.LX, read.LY); }
    // XInput: +4 LX, +6 LY
    uint8_t x[12]{};
    int16_t lx = -32767, ly = 32767;
    memcpy(x + 4, &lx, 2); memcpy(x + 6, &ly, 2);
    ReadXInputPad(x, 0, read);
    if (!(read.LX < -0.99f && read.LY > 0.99f)) { ++fails; printf("X LX %f LY %f\n", read.LX, read.LY); }
    ReadXInputPad(x, 0, read, 1.0f, 0, true);
    int16_t a, b; memcpy(&a, x + 4, 2); memcpy(&b, x + 6, 2);
    if (a != 0 || b != 0) { ++fails; puts("X not centred"); }
    printf("%d failure(s)\n", fails);
    return fails;
}
