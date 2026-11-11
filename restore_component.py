#!/usr/bin/env python3
"""Hosted-only small consumer of extracted RestoreWallet; not wallet integration.

No extraction edits are made. Context/database/load/translation providers are
minimal stubs; filesystem/stdio and the extracted fsbridge functions are real.
Linker fopen/fclose wrappers provide marked collision/close-result fault seams.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
def extract(text, signature):
    start = text.index(signature)
    end = text.index("\n}\n", start) + 3
    return text[start:end]
PREFIX = r'''
#include <algorithm>
#include <array>
#include <cassert>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <sys/resource.h>
#include <csignal>
#include <vector>
namespace fs { using namespace std::filesystem; std::string PathToString(const path& p) { return p.string(); } }
using bilingual_str = std::string;
std::string Untranslated(const std::string& s) { return s; }
const char* arg(const std::string& s) { return s.c_str(); }
const char* arg(const char* s) { return s; }
template<class... A> std::string strprintf(const char* f, const A&... a) {
    int n = std::snprintf(nullptr, 0, f, arg(a)...);
    if (n < 0) throw std::runtime_error("format failure");
    std::vector<char> b(n + 1); std::snprintf(b.data(), b.size(), f, arg(a)...); return b.data();
}
void Assume(bool b) { if (!b) throw std::runtime_error("Assume failed"); }
enum class DatabaseStatus { SUCCESS, FAILED_LOAD, FAILED_INVALID_BACKUP_FILE, FAILED_ALREADY_EXISTS };
struct DatabaseOptions { bool require_existing{false}; };
struct Args {};
struct WalletContext { Args* args; };
struct CWallet {};
void ReadDatabaseArgs(const Args&, DatabaseOptions&) {}
fs::path root;
fs::path GetWalletDir() { return root; }
bool TryCreateDirectories(const fs::path& p) { return fs::create_directories(p); }
int load_calls{0};
std::shared_ptr<CWallet> LoadWallet(WalletContext&, const std::string&, std::optional<bool>,
    const DatabaseOptions&, DatabaseStatus&, bilingual_str&, std::vector<bilingual_str>&) {
    ++load_calls; throw std::runtime_error("Unexpected LoadWallet call in no-load component control");
}
namespace fsbridge {
'''
SUFFIX = r'''
extern "C" FILE* __real_fopen(const char*, const char*);
extern "C" int __real_fclose(FILE*);
std::string seam_path;
bool close_armed{false}, collision_armed{false}, close_hit{false}, collision_hit{false};
FILE* close_stream{nullptr};
extern "C" FILE* __wrap_fopen(const char* path, const char* mode) {
    if (seam_path == path && std::strcmp(mode, "wbx") == 0 && collision_armed) {
        collision_armed = false;
        FILE* rival = __real_fopen(path, "wb");
        if (!rival) throw std::runtime_error("collision seam create failed");
        if (std::fwrite("rival-file", 1, 10, rival) != 10 || __real_fclose(rival) != 0)
            throw std::runtime_error("collision seam write failed");
        collision_hit = true;
    }
    FILE* file = __real_fopen(path, mode);
    if (file && seam_path == path && std::strcmp(mode, "wbx") == 0 && close_armed) {
        close_stream = file; close_armed = false;
    }
    return file;
}
extern "C" int __wrap_fclose(FILE* file) {
    const bool inject = file == close_stream;
    if (inject) close_stream = nullptr;
    int result = __real_fclose(file);
    if (inject && result == 0) { close_hit = true; errno = EIO; return EOF; }
    return result;
}
std::string read(const fs::path& p) { std::ifstream f(p, std::ios::binary); return {std::istreambuf_iterator<char>(f), {}}; }
void write(const fs::path& p, const std::string& s) {
    std::ofstream f(p, std::ios::binary); f << s; f.close(); if (!f) throw std::runtime_error("fixture write failed");
}
std::string quote(const std::string& s) {
    std::string out="\""; for (unsigned char c : s) {
        if (c=='\\' || c=='"') { out+='\\'; out+=c; }
        else if (c=='\n') out+="\\n"; else if (c=='\r') out+="\\r"; else if (c=='\t') out+="\\t";
        else if (c < 32) out+='?'; else out+=c;
    } return out+'"';
}
int failures{0};
void record(const std::string& name, bool good, const std::string& error, bool seam=false) {
    failures += !good;
    std::cout << "{\"case\":" << quote(name) << ",\"pass\":" << (good?"true":"false")
              << ",\"error\":" << quote(error) << ",\"seam_reached\":" << (seam?"true":"false") << "}\n";
}
int main(int argc, char** argv) {
    if (argc != 2) return 90;
    root=fs::path(argv[1]); fs::create_directories(root);
    Args args; WalletContext context{&args}; std::vector<bilingual_str> warnings;
    const std::string data(20480, 'Q'); const auto backup=root/"source.backup"; write(backup, data);
    auto call = [&](const std::string& name, const fs::path& source) {
        DatabaseStatus status=DatabaseStatus::SUCCESS; bilingual_str error;
        const auto wallet=RestoreWallet(context, source, name, std::nullopt, status, error, warnings, false);
        if (wallet) throw std::runtime_error("No-load returned a wallet"); return error;
    };
    auto error=call("success", backup);
    record("no_load_success_keeps_complete_file", error.empty() && read(root/"success/wallet.dat")==data && load_calls==0, error);
    fs::create_directory(root/"capped"); write(root/"capped/sentinel", "keep");
    struct rlimit before{}, during{};
    if (getrlimit(RLIMIT_FSIZE, &before) != 0) return 91;
    during=before; during.rlim_cur=1024; std::signal(SIGXFSZ, SIG_IGN);
    if (setrlimit(RLIMIT_FSIZE, &during) != 0) return 92;
    try { error=call("capped", backup); }
    catch (...) { setrlimit(RLIMIT_FSIZE, &before); throw; }
    if (setrlimit(RLIMIT_FSIZE, &before) != 0) return 93;
    struct rlimit restored{}; if (getrlimit(RLIMIT_FSIZE, &restored) != 0) return 94;
    record("no_load_capped_copy_cleans_owned_partial", !error.empty() && !fs::exists(root/"capped/wallet.dat")
        && read(root/"capped/sentinel")=="keep" && restored.rlim_cur==before.rlim_cur && restored.rlim_max==before.rlim_max, error);
    error=call("capped", backup);
    record("no_load_same_name_retry", error.empty() && read(root/"capped/wallet.dat")==data && read(root/"capped/sentinel")=="keep", error);
    fs::create_directory(root/"close"); write(root/"close/sentinel", "keep");
    seam_path=(root/"close/wallet.dat").string(); close_armed=true; error=call("close", backup);
    record("no_load_close_result_failure_cleans_owned_file", close_hit && !error.empty() && !fs::exists(root/"close/wallet.dat")
        && read(root/"close/sentinel")=="keep", error, close_hit);
    seam_path.clear(); error=call("close", backup);
    record("no_load_retry_after_close_result_failure", error.empty() && read(root/"close/wallet.dat")==data, error);
    error=call("success", backup);
    record("existing_complete_file_preserved", !error.empty() && read(root/"success/wallet.dat")==data, error);
    fs::create_directory(root/"collision"); seam_path=(root/"collision/wallet.dat").string(); collision_armed=true;
    error=call("collision", backup);
    record("racing_exclusive_creation_preserves_other_file", collision_hit && !error.empty() && read(root/"collision/wallet.dat")=="rival-file", error, collision_hit);
    seam_path.clear(); error=call("missing", root/"no-source");
    record("missing_source_creates_nothing", !error.empty() && !fs::exists(root/"missing"), error);
    record("source_unchanged_and_load_never_called", read(backup)==data && load_calls==0, "");
    return failures ? 1 : 0;
}
'''
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="Exact candidate wallet.cpp")
    parser.add_argument("--fs-source", required=True, type=Path, help="Pinned util/fs.cpp")
    parser.add_argument("--output", required=True, type=Path, help="New isolated output directory")
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    wallet = extract(args.source.read_text(), "std::shared_ptr<CWallet> RestoreWallet(")
    bridge_text = args.fs_source.read_text()
    fopen = extract(bridge_text, "FILE *fopen(")
    join = extract(bridge_text, "fs::path AbsPathJoin(")
    digest = lambda value: hashlib.sha256(value).hexdigest()
    receipt = {"wallet_source_sha256": digest(args.source.read_bytes()),
               "fs_source_sha256": digest(args.fs_source.read_bytes()),
               "extracted_restore_sha256": digest(wallet.encode()),
               "extracted_fopen_sha256": digest(fopen.encode()),
               "extracted_join_sha256": digest(join.encode()), "source_text_replacements": [],
               "providers": ["WalletContext/Args/DatabaseOptions/DatabaseStatus", "CWallet/LoadWallet stub (must remain uncalled)",
                             "ReadDatabaseArgs/GetWalletDir/TryCreateDirectories", "bilingual_str/Untranslated/strprintf", "fs path aliases/PathToString", "Assume"],
               "fault_seams": ["linker --wrap=fopen: creates rival before real exclusive open",
                               "linker --wrap=fclose: real close then one injected EIO return"],
               "scope": "Extracted Linux component, no SQLite/full wallet/Windows integration"}
    cpp = args.output / "consumer.cpp"
    cpp.write_text(PREFIX + fopen + join + "\n} // namespace fsbridge\n" + wallet + SUFFIX)
    (args.output / "source-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    command = ["g++", "-std=c++20", "-O0", "-Wall", "-Wextra", str(cpp),
               "-Wl,--wrap=fopen", "-Wl,--wrap=fclose", "-o", str(args.output / "consumer")]
    result = {"status": "preparing", "compile_command": command, "receipt": receipt}
    try:
        compiled = subprocess.run(command, capture_output=True, text=True, timeout=90)
        (args.output / "compile.stdout").write_text(compiled.stdout)
        (args.output / "compile.stderr").write_text(compiled.stderr)
        result["compile_exit"] = compiled.returncode
        if compiled.returncode:
            result["status"] = "component_compile_failure"
            return 1
        ran = subprocess.run([str(args.output / "consumer"), str(args.output / "runtime")],
                             capture_output=True, text=True, timeout=30)
        (args.output / "run.stdout").write_text(ran.stdout)
        (args.output / "run.stderr").write_text(ran.stderr)
        rows = [json.loads(line) for line in ran.stdout.splitlines() if line.strip()]
        result.update(run_exit=ran.returncode, controls=rows,
                      status="component_controls_pass" if ran.returncode == 0 and len(rows) == 9 and all(x["pass"] for x in rows)
                      else "component_control_failure")
        return 0 if result["status"] == "component_controls_pass" else 1
    except Exception as error:
        result.update(status="component_setup_failure", error=repr(error))
        return 1
    finally:
        (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
if __name__ == "__main__":
    raise SystemExit(main())
