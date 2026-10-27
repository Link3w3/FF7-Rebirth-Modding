// cacs_soundbank <spec.txt> <out dir>: Create a Character System's sound bank maker on the command line.
//   container <name>            the mod (<name>.utoc/.ucas/.pak)
//   bank <name> [id]            the bank (id 0 or none: from its name)
//   folder <path>               /Game/Sound/Voice/{language}/Character/Player, or any /Game/ folder
//   alias <asset path>          its alias setting (optional)
//   attenuation <asset path>    (default /Game/Sound/Config/Attenuation/player; "none": none)
//   kbps <n>  rate <hz>  channels <n>
//   line <cue> [volume=v] [category=n] [bus=n] [id=n] [length=s] <LANG>=<wav> ... (or just <wav>)
//   wavs <dir>                  every .wav in it, its file name the cue
#include "../core/SoundBankCore.hpp"
#include <cstdio>
#include <dirent.h>
#include <fstream>
#include <iterator>
#include <sstream>
static CacsSound::Bytes ReadAll(const std::string& p)
{
    std::ifstream f(p, std::ios::binary);
    return CacsSound::Bytes((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
}
static bool Load(const std::string& path, CacsSound::Pcm& pcm)
{
    const CacsSound::Bytes b = ReadAll(path);
    std::string error;
    if (!CacsSound::ReadWav(b.data(), b.size(), pcm, error)) { std::fprintf(stderr, "%s: %s\n", path.c_str(), error.c_str()); return false; }
    return true;
}
static void Save(const std::string& path, const CacsSound::Bytes& b)
{
    std::ofstream(path, std::ios::binary).write(reinterpret_cast<const char*>(b.data()), static_cast<std::streamsize>(b.size()));
}
int main(int argc, char** argv)
{
    if (argc < 3) { std::fprintf(stderr, "usage: cacs_soundbank spec.txt outdir\n"); return 2; }
    CacsSound::Build::Request req;
    std::ifstream in(argv[1]);
    std::string line;
    while (std::getline(in, line))
    {
        std::istringstream ss(line);
        std::string kind;
        if (!(ss >> kind) || kind[0] == '#') { continue; }
        if (kind == "container") { ss >> req.Container; }
        else if (kind == "bank") { unsigned id = 0; ss >> req.Bank >> id; req.BankId = static_cast<uint16_t>(id); }
        else if (kind == "folder") { ss >> req.Folder; }
        else if (kind == "alias") { ss >> req.AliasSetting; }
        else if (kind == "attenuation") { ss >> req.Attenuation; if (req.Attenuation == "none") { req.Attenuation.clear(); } }
        else if (kind == "kbps") { ss >> req.Kbps; }
        else if (kind == "rate") { ss >> req.Rate; }
        else if (kind == "channels") { ss >> req.Channels; }
        else if (kind == "line")
        {
            CacsSound::Build::Line l;
            ss >> l.Cue;
            std::string tok;
            while (ss >> tok)
            {
                const size_t eq = tok.find('=');
                const std::string key = eq == std::string::npos ? std::string() : tok.substr(0, eq), val = eq == std::string::npos ? tok : tok.substr(eq + 1);
                if (key == "volume") { l.Volume = std::stof(val); }
                else if (key == "category") { l.Category = static_cast<uint8_t>(std::stoi(val)); }
                else if (key == "bus") { l.Bus = static_cast<uint8_t>(std::stoi(val)); }
                else if (key == "id") { l.Id = std::stoi(val); }
                else if (key == "length") { l.Length = std::stof(val); }
                else
                {
                    CacsSound::Pcm pcm;
                    if (!Load(val, pcm)) { return 1; }
                    l.Audio.emplace_back(key, std::move(pcm));
                }
            }
            req.Lines.push_back(std::move(l));
        }
        else if (kind == "wavs")
        {
            std::string dir;
            ss >> dir;
            DIR* d = opendir(dir.c_str());
            if (!d) { std::fprintf(stderr, "no folder %s\n", dir.c_str()); return 1; }
            std::vector<std::string> names;
            while (dirent* e = readdir(d))
            {
                std::string n = e->d_name;
                if (n.size() > 4 && (n.substr(n.size() - 4) == ".wav" || n.substr(n.size() - 4) == ".WAV")) { names.push_back(n); }
            }
            closedir(d);
            std::sort(names.begin(), names.end());
            for (const std::string& n : names)
            {
                CacsSound::Build::Line l;
                l.Cue = n.substr(0, n.size() - 4);
                CacsSound::Pcm pcm;
                if (!Load(dir + "/" + n, pcm)) { return 1; }
                l.Audio.emplace_back("", std::move(pcm));
                req.Lines.push_back(std::move(l));
            }
        }
    }
    CacsSound::Build::Result r = CacsSound::Build::Make(req);
    if (!r.Ok) { std::fprintf(stderr, "error: %s\n", r.Error.c_str()); return 1; }
    const std::string base = std::string(argv[2]) + "/" + req.Container;
    Save(base + ".utoc", r.Utoc);
    Save(base + ".ucas", r.Ucas);
    Save(base + ".pak", r.Pak);
    for (const std::string& s : r.Report) { std::printf("%s\n", s.c_str()); }
    std::printf("%s: %zu packages, utoc %zu, ucas %zu bytes\n", req.Container.c_str(), r.Packages.size(), r.Utoc.size(), r.Ucas.size());
    return 0;
}
