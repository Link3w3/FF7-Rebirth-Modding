// The DLL's ability-row choice (RebirthSkelCompat.cpp: TakenPlayers .. AbilityRowFor, included as it is) on the merged
// compat set: which compat row's abilities play for a player row with each character in Cloud's place.
#include "SkelCompatCore.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <set>
#include <sstream>
using namespace std;
struct { SkelCompat::Config Config; } State;
#include "owners_body.inc"
static string readAll(const filesystem::path& p) { ifstream f(p, ios::binary); stringstream s; s << f.rdbuf(); return s.str(); }
static string n(const wstring& w) { string s; for (wchar_t c : w) s += c < 128 ? char(c) : '?'; return s; }
int main(int argc, char** argv)
{
    set<wstring> inst;
    { ifstream f(argv[3]); string line; while (getline(f, line)) if (!line.empty()) { wstring w(line.begin(), line.end()); for (auto& c : w) c = towlower(c); inst.insert(w); } }
    vector<filesystem::path> files;
    for (auto& e : filesystem::directory_iterator(argv[1])) if (e.path().extension() == ".json") files.push_back(e.path());
    sort(files.begin(), files.end());
    for (auto& p : files) SkelCompat::AppendConfig(readAll(p), p.filename().wstring(), State.Config);
    vector<filesystem::path> skins;
    for (auto& e : filesystem::directory_iterator(argv[2])) if (e.path().extension() == ".json") skins.push_back(e.path());
    sort(skins.begin(), skins.end());
    for (auto& p : skins) SkelCompat::AppendSkin(readAll(p), p.stem().wstring(), State.Config);
    SkelCompat::FinishConfig(State.Config, [&](const wstring& name) { wstring w = name; for (auto& c : w) c = towlower(c); return inst.count(w) > 0; });
    set<wstring> players;
    for (auto& r : State.Config.AnimSets) if (!r.Abilities.empty()) players.insert(r.Player);
    auto show = [&](const wchar_t* who) {
        cout << "== " << n(who) << "\n";
        for (auto& p : players)
        {
            const SkelCompat::AnimSetRow* row = AbilityRowFor(p);
            cout << "   " << n(p) << ": " << (row ? n(row->Origin) + " row " + n(row->Characters.front()) + " (owners: " + n(OwnersOfRow(*row)) + ")" : string("none (the row's own)")) << "\n";
        }
        for (auto& c : State.Config.Characters)
        {
            if (std::find(HoldingPlaces.begin(), HoldingPlaces.end(), &c) == HoldingPlaces.end()) continue;
            cout << "   players of " << n(c.Name) << ":";
            for (auto& p : PlayersOf(c)) cout << " " << n(p);
            cout << "\n";
        }
    };
    show(L"no character (every place its own)");
    for (auto& c : State.Config.Characters)
    {
        HoldingPlaces.assign(1, &c);
        show(c.Name.c_str());
    }
}
