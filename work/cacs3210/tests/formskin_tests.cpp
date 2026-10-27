// (3.19.0) skins per form: the row's FormSkinOf / VoiceOf
#include "../src/SkelCompatCore.hpp"
#include <cstdio>
#include <cstdlib>
using namespace SkelCompat;
static int fails = 0;
#define CHECK(c) do { if (!(c)) { std::printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); ++fails; } } while (0)
int main()
{
    AnimSetRow row;
    Form normal; normal.Name = L"NORMAL";
    Form older; older.Name = L"OLDER SEPHIROTH"; older.Model = L"/Game/X/Older.Older";
    Form winged; winged.Name = L"WINGED";
    Form bizarro; bizarro.Name = L"BIZARRO"; bizarro.AnimClass = L"/Game/X/ABP.ABP_C";
    row.Forms.List = {normal, older, winged, bizarro};
    row.Speaks.Set = true; row.Speaks.Bank = L"row";
    row.Skin = 2; row.SkinSpeaks.Set = true; row.SkinSpeaks.Bank = L"rowskin";
    CHECK(row.FormSkinOf(L"WINGED") == nullptr);
    CHECK(row.VoiceOf(2).Bank == L"rowskin");          // no choice: the row's skin's voice
    FormSkinChoice a; a.Form = L"WINGED"; a.Skin = 5; a.Speaks.Set = true; a.Speaks.Bank = L"formskin";
    FormSkinChoice b; b.Form = L"older sephiroth"; b.Skin = -1;
    FormSkinChoice c; c.Form = L"NORMAL"; c.Skin = 7;   // a skin with no voice of its own
    row.FormSkins = {a, b, c};
    CHECK(row.FormSkinOf(L"OLDER SEPHIROTH") != nullptr && row.FormSkinOf(L"OLDER SEPHIROTH")->Skin == -1);   // names fold case
    CHECK(row.VoiceOf(2).Bank == L"formskin");         // the form's skin's voice
    CHECK(row.VoiceOf(1).Bank == L"row");              // its own model: the row's voice, not the row skin's
    CHECK(row.VoiceOf(0).Bank == L"row");              // another skin with no voice: the row's
    CHECK(row.VoiceOf(3).Bank == L"rowskin");          // no choice
    CHECK(row.VoiceOf(-1).Bank == L"rowskin");         // outside battle
    FormSkinChoice d; d.Form = L"BIZARRO"; d.Skin = 2;  // the row's own skin chosen: its voice
    row.FormSkins.push_back(d);
    CHECK(row.VoiceOf(3).Bank == L"rowskin");
    const auto targets = row.VoiceTargets();
    CHECK(std::find(targets.begin(), targets.end(), std::wstring(L"formskin")) != targets.end());
    CHECK(row.HasVoices());
    if (fails) { std::printf("%d failed\n", fails); return 1; }
    std::printf("all form skin tests passed\n");
    return 0;
}
