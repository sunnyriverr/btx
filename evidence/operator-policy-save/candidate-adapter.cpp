#include <modelnet/helper.h>
#include <modelnet/auto_storage.h>
#include <modelnet/catalog.h>
#include <modelnet/policy.h>
#include <univalue.h>
#include <util/fs.h>
#include <fstream>
#include <mutex>
namespace modelnet {
static std::mutex g_helper_store_mu;
struct HelperRuntimeInfo {
    StorageMode storage_mode{StorageMode::AUTO};
    uint64_t target_bytes{0};
    uint64_t effective_quota{0};
    uint64_t fs_capacity{0};
    uint64_t fs_available{0};
    uint64_t reserve_bytes{0};
    bool demand_seed{true};
    bool preserve_rare{false};
    bool follow_peers{true};
    bool public_host_reachable{false};
    bool advertised_host{false};
    uint64_t upload_bps{0};
    int active_transfers{0};
    std::string watch_dir;
    int64_t last_watch_scan_ms{0};
    int last_watch_imported{0};
    int last_watch_skipped{0};
};
static HelperRuntimeInfo g_runtime;
fs::path HelperDir(ModelCatalog& cat) { return cat.Store().Root().parent_path(); }
bool WriteJsonFile(const fs::path& path, const UniValue& obj, std::string& err)
{
    // Write a temp file, check it after close and rename it over path. Writing
    // path in place left a cut-short file when a full disk failed the write
    // (often only the flush at close), and the caller was told it was saved.
    // The next read of that file starts from an empty store.
    fs::create_directories(path.parent_path());
    std::error_code ec;
    const fs::path tmp = fs::PathFromString(fs::PathToString(path) + ".tmp");
    {
        std::ofstream out(tmp, std::ios::trunc);
        if (!out) {
            err = "write " + fs::PathToString(path);
            return false;
        }
        out << obj.write() << "\n";
        out.close();
        if (!out) {
            fs::remove(tmp, ec);
            err = "write " + fs::PathToString(path);
            return false;
        }
    }
    fs::rename(tmp, path, ec);
    if (ec) {
        fs::remove(tmp, ec);
        err = "write " + fs::PathToString(path);
        return false;
    }
    return true;
}
bool QualificationDispatch(ModelCatalog& cat, const UniValue& req, UniValue& result, std::string& err_code, std::string& err, std::atomic<bool>* stop) {
const std::string method=req["method"].get_str(); const UniValue params=req["params"]; auto Arg=[&](size_t i)->const UniValue& { return params[i]; };
    if (method == "getmodelpolicy" || method == "setmodelpolicy") {
        std::lock_guard<std::mutex> store_lock(g_helper_store_mu);
        PreservationPolicy live = cat.Policy();
        if (method == "setmodelpolicy") {
            UniValue patch = Arg(0);
            if (!patch.isObject()) {
                err_code = "INVALID_PARAMETER";
                err = "policy object required";
                return false;
            }
            if (patch.exists("automatic_spend_atoms") && patch["automatic_spend_atoms"].getInt<int64_t>() != 0) {
                err_code = "INVALID_PARAMETER";
                err = "automatic spend remains 0; use EXPLICIT_PAID getmodel for a quote";
                return false;
            }
            if (patch.exists("auto_pay") && patch["auto_pay"].get_bool()) {
                err_code = "INVALID_PARAMETER";
                err = "auto_pay is refused; automatic spend is 0";
                return false;
            }
            if (!PolicyFromJson(patch, live, err)) {
                err_code = "INVALID_PARAMETER";
                return false;
            }
            const uint64_t hard = cat.QuotaBytes();
            if (live.storage_quota_bytes == 0 || live.storage_quota_bytes > hard) {
                live.storage_quota_bytes = hard;
            }
            const UniValue dumped = PolicyToJson(live);
            if (!WriteJsonFile(HelperDir(cat) / "policy.json", dumped, err)) {
                err_code = "IO";
                return false;
            }
            cat.SetPolicy(live);
            g_runtime.follow_peers = live.follow_configured_peers;
            g_runtime.preserve_rare = live.preserve_rare;
        }
        result = PolicyToJson(cat.Policy());
        result.pushKV("auto_pay", false);
        return true;
    }

return false;
}
}
