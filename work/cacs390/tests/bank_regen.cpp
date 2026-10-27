// bank_regen <spec.txt> <out.sab> <out.uasset>: rebuilds a bank from its sounds' HCA streams with SoundBankCore
// (spec: "bank <name> <id>", "package <path>", "source <path>", "alias <path>", "attenuation <path>",
//  "sound <name> <volume> <category> <bus> <hca file>").
#include "../core/SoundBankCore.hpp"
#include <cstdio>
#include <fstream>
#include <iterator>
#include <sstream>
static CacsSound::Bytes ReadAll(const std::string& p)
{
    std::ifstream f(p, std::ios::binary);
    return CacsSound::Bytes((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
}
int main(int argc, char** argv)
{
    if (argc < 4) { return 2; }
    std::ifstream in(argv[1]);
    std::string line;
    CacsSound::Sead::Bank bank;
    CacsSound::BankPackage::Spec spec;
    spec.Attenuation.clear();
    while (std::getline(in, line))
    {
        std::istringstream ss(line);
        std::string kind;
        ss >> kind;
        if (kind == "bank") { unsigned id; ss >> bank.Name >> id; bank.Id = static_cast<uint16_t>(id); }
        else if (kind == "package") { ss >> spec.Package; }
        else if (kind == "source") { ss >> spec.Source; }
        else if (kind == "alias") { ss >> spec.AliasSetting; }
        else if (kind == "attenuation") { ss >> spec.Attenuation; }
        else if (kind == "sound")
        {
            CacsSound::Sead::Sound s;
            unsigned cat, bus;
            std::string file;
            ss >> s.Name >> s.Volume >> cat >> bus >> file;
            s.Category = static_cast<uint8_t>(cat);
            s.Bus = static_cast<uint8_t>(bus);
            ss >> s.Id;
            if (!ss) { s.Id = -1; }
            float length = -1.0f;
            if (ss >> length) { s.Length = length; }
            s.Hca = ReadAll(file);
            if (!CacsSound::Hca::ParseHeader(s.Hca.data(), s.Hca.size(), s.Info)) { std::fprintf(stderr, "bad hca %s\n", file.c_str()); return 1; }
            bank.Sounds.push_back(std::move(s));
        }
    }
    std::string error;
    CacsSound::Bytes sab = CacsSound::Sead::Write(bank, &error);
    if (sab.empty()) { std::fprintf(stderr, "%s\n", error.c_str()); return 1; }
    std::ofstream(argv[2], std::ios::binary).write(reinterpret_cast<const char*>(sab.data()), static_cast<std::streamsize>(sab.size()));
    CacsSound::Bytes pkg = CacsSound::BankPackage::Write(spec, bank, sab, &error);
    if (pkg.empty()) { std::fprintf(stderr, "%s\n", error.c_str()); return 1; }
    std::ofstream(argv[3], std::ios::binary).write(reinterpret_cast<const char*>(pkg.data()), static_cast<std::streamsize>(pkg.size()));
    std::printf("sab %zu bytes, package %zu bytes\n", sab.size(), pkg.size());
    return 0;
}
