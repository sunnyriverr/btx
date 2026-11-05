// Scoped component controls for the existing JIT-RUN CPU/refusal contract.
#include "runtime.cpp"
#include <random.h>
#include <iostream>

// Deterministic test lease IDs only. Production randomness is not under test.
void GetRandBytes(Span<unsigned char> bytes) noexcept
{
    static unsigned char n = 0;
    for (auto& b : bytes) b = ++n;
}

namespace {
int checks = 0, failures = 0;
void Check(bool ok, const char* label)
{
    ++checks;
    if (!ok) ++failures;
    std::cout << (ok ? "PASS " : "FAIL ") << label << '\n';
}
struct Env {
    std::string name, old;
    bool had;
    Env(const char* k, const char* value) : name(k), had(std::getenv(k) != nullptr)
    {
        if (had) old = std::getenv(k);
        Set(value);
    }
    void Set(const char* v) {
#ifdef _WIN32
        _putenv_s(name.c_str(), v ? v : "");
#else
        if (v) setenv(name.c_str(), v, 1); else unsetenv(name.c_str());
#endif
    }
    ~Env() { Set(had ? old.c_str() : nullptr); }
};
}

int main(int argc, char** argv)
{
    using namespace modelnet;
    if (argc != 2) return 2;
    const unsigned char payload[] = {'t','i','n','y','-','c','p','u','-','f','i','x','t','u','r','e'};
    Span<const unsigned char> bytes{payload, sizeof(payload)};
    UniValue params(UniValue::VOBJ);
    params.pushKV("backend", "CPU");
    params.pushKV("adapter_abi", RUNTIME_ADAPTER_ABI);
    ReadyReceipt loaded, remapped, rebuilt;
    std::string code, err;
    Digest48 expected;
    Check(CpuFixtureSmoke(bytes, expected, err), "real CPU smoke");
    Check(LoadTrustedRuntime("synthetic-cpu-fixture", bytes, params, loaded, code, err), "CPU load");
    Check(loaded.smoke_performed && loaded.smoke_passed && !loaded.lease_id.empty() &&
          loaded.achieved == ReadinessTarget::FIRST_USEFUL_RESULT, "CPU readiness and lease");
    Check(loaded.json["smoke_digest48"].get_str() == expected.Hex(), "CPU digest matches verified bytes");
    Check(loaded.json["stub"].isFalse() && loaded.json["remote_endpoint"].isFalse() &&
          loaded.json["funded_wallet"].isFalse() && loaded.json["automatic_spend_atoms"].getInt<int>() == 0,
          "local no-spend receipt");
    UniValue sleep;
    Check(SleepRuntimePreserveWeights(loaded.lease_id, sleep, code, err), "sleep succeeds");
    Check(sleep["weights_preserved"].isTrue() && sleep["kv_discarded"].isTrue() &&
          sleep["workspace_discarded"].isTrue() && sleep["ready"].isFalse(), "sleep preserves weights and clears readiness");
    Check(!WakeRuntimeRemapOnly(loaded.lease_id, remapped, code, err) && code == "PREMATURE_READY" &&
          !remapped.smoke_performed && !remapped.smoke_passed, "remap alone refuses readiness");
    Check(remapped.json["remap_only"].isTrue() && remapped.json["kv_rebuilt"].isFalse() &&
          remapped.json["ready"].isFalse(), "remap receipt retains unready state");
    Check(WakeRuntimeRebuildKv(loaded.lease_id, rebuilt, code, err), "wake rebuild succeeds");
    Check(rebuilt.smoke_performed && rebuilt.smoke_passed && rebuilt.lease_id == loaded.lease_id &&
          rebuilt.json["smoke_digest48"].get_str() == expected.Hex(), "wake re-smokes same retained bytes");
    Check(rebuilt.achieved == ReadinessTarget::FIRST_USEFUL_RESULT && rebuilt.json["kv_rebuilt"].isTrue() &&
          rebuilt.json["remap_only"].isFalse() && rebuilt.json["ready"].isTrue() &&
          rebuilt.json["weights_preserved"].isTrue(), "wake receipt restores readiness after rebuild");
    Check(!SleepRuntimePreserveWeights("not-a-lease", sleep, code, err) && code == "UNKNOWN_LEASE", "unknown sleep lease");
    Check(!WakeRuntimeRemapOnly("not-a-lease", remapped, code, err) && code == "UNKNOWN_LEASE", "unknown remap lease");
    Check(!WakeRuntimeRebuildKv("not-a-lease", rebuilt, code, err) && code == "UNKNOWN_LEASE", "unknown wake lease");
    ReadyReceipt rec;
    auto refused = [&](const char* runtime, Span<const unsigned char> data, const UniValue& p, const char* wanted) {
        bool ok = LoadTrustedRuntime(runtime, data, p, rec, code, err);
        return !ok && code == wanted && !rec.smoke_performed && !rec.smoke_passed && rec.lease_id.empty();
    };
    Check(refused("synthetic-cpu-fixture", {}, params, "UNVERIFIED_RANGE"), "empty verified payload refused");
    UniValue bad(UniValue::VOBJ); bad.pushKV("adapter_abi", "unsupported");
    Check(refused("synthetic-cpu-fixture", bytes, bad, "ADAPTER_ABI_MISMATCH"), "ABI mismatch refused");
    bad = UniValue(UniValue::VOBJ); bad.pushKV("backend", "unknown");
    Check(refused("synthetic-cpu-fixture", bytes, bad, "UNKNOWN_ADAPTER_PARAMETER"), "unknown backend refused");
    Check(refused("unknown-runtime", bytes, params, "UNSUPPORTED_RUNTIME_PROFILE"), "unknown runtime refused");
    bad = UniValue(UniValue::VOBJ); bad.pushKV("backend", "CUDA");
    Check(refused("synthetic-cpu-fixture", bytes, bad, "UNSUPPORTED_RUNTIME_PROFILE"), "CPU fixture cannot qualify CUDA");
    for (const char* key : {"executable_path", "command", "LD_PRELOAD", "unrecognized_flag"}) {
        bad = UniValue(UniValue::VOBJ); bad.pushKV(key, "unsupported");
        Check(refused("synthetic-cpu-fixture", bytes, bad, "UNKNOWN_ADAPTER_PARAMETER"), key);
    }
    bad = UniValue(UniValue::VOBJ); UniValue flags(UniValue::VOBJ); flags.pushKV("unrecognized_flag", 1); bad.pushKV("flags", flags);
    Check(refused("synthetic-cpu-fixture", bytes, bad, "UNKNOWN_ADAPTER_PARAMETER"), "unknown nested flag refused");
    Env llama("BTX_LLAMA_CLI", nullptr), vllm("BTX_VLLM", nullptr), mlx("BTX_MLX", nullptr), cuda("BTX_MODEL_CUDA_LOADER", nullptr);
    bad = UniValue(UniValue::VOBJ); bad.pushKV("backend", "CPU");
    Check(refused("llama.cpp", bytes, bad, "RUNTIME_NOT_INSTALLED"), "operator environment required");
    llama.Set(argv[1]);
    Check(refused("llama.cpp", bytes, bad, "LIVE_RUNTIME_NOT_RUN"), "existing operator path alone is not runtime success");
#ifdef _WIN32
    vllm.Set(argv[1]); mlx.Set(argv[1]); cuda.Set(argv[1]);
    const auto accelerated = ProbeAcceleratedAdapters();
    Check(accelerated.size() == 3, "three accelerated statuses");
    for (const auto& s : accelerated) {
        Check(!s.present && !s.stub && s.detail.find("NOT_RUN") != std::string::npos, s.backend.c_str());
    }
    for (const auto& pair : {std::pair{"llama.cpp", "CUDA"}, {"vLLM", "ROCM"}, {"MLX", "METAL"}, {"safetensors-cuda", "CUDA"}}) {
        bad = UniValue(UniValue::VOBJ); bad.pushKV("backend", pair.second);
        Check(refused(pair.first, bytes, bad, "HARDWARE_NOT_RUN"), pair.first);
    }
#endif
    // Internal missing-state controls exercise the guarded wake predicate.
    {
        std::lock_guard<std::mutex> lock(g_rt_mu);
        g_sessions[loaded.lease_id].weights_resident = false;
    }
    Check(!WakeRuntimeRebuildKv(loaded.lease_id, rec, code, err) && code == "UNVERIFIED_RANGE" && !rec.smoke_passed,
          "nonresident weights refuse wake");
    {
        std::lock_guard<std::mutex> lock(g_rt_mu);
        g_sessions[loaded.lease_id].weights_resident = true;
        g_sessions[loaded.lease_id].weights.clear();
    }
    Check(!WakeRuntimeRebuildKv(loaded.lease_id, rec, code, err) && code == "UNVERIFIED_RANGE" && !rec.smoke_passed,
          "empty weights refuse wake");
    std::cout << "checks=" << checks << " failures=" << failures << '\n';
    return failures ? 1 : 0;
}
