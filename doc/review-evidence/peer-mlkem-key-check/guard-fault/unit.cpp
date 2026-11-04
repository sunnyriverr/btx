// Unit-only failure injection. All handshake keys and bytes are genuinely valid.
#include <crypto/ml_kem.h>
namespace unit {
bool force_failure{false};
unsigned checks{0}, encapsulations{0}, invalid_generated_keys{0};
void Reset(bool fail) { force_failure = fail; checks = encapsulations = invalid_generated_keys = 0; }
}
namespace mlkem {
bool UnitRealKeyCheck(const PublicKey&) noexcept;
EncapsResult UnitRealEncaps(const PublicKey&);
bool IsValidEncapsulationKey(const PublicKey& key) noexcept
{
    ++unit::checks;
    const bool valid = UnitRealKeyCheck(key);
    if (!valid) ++unit::invalid_generated_keys;
    return valid && !unit::force_failure;
}
EncapsResult Encaps(const PublicKey& key)
{
    ++unit::encapsulations;
    if (!UnitRealKeyCheck(key)) ++unit::invalid_generated_keys;
    return UnitRealEncaps(key);
}
}
#define main UnusedPositiveControlsMain
#include "../runtime/positive_transport.cpp"
#undef main

namespace {
bool ForcedFailure(Policy policy)
{
    unit::Reset(true);
    auto init = MakeTransport(NodeId{0}, true, policy);
    auto resp = MakeTransport(NodeId{1}, false, policy);
    bool rejected{false};
    std::vector<CNetMessage> init_received, resp_received;
    auto transfer = [&](V2Transport& src, V2Transport& dst, std::vector<CNetMessage>& messages) {
        const auto& [data, more, type] = src.GetBytesToSend(false);
        (void)more; (void)type;
        if (data.empty()) return false;
        std::vector<uint8_t> bytes(UCharCast(data.data()), UCharCast(data.data()) + data.size());
        src.MarkBytesSent(bytes.size());
        Span<const uint8_t> remaining{bytes};
        while (!remaining.empty()) {
            const auto before = remaining.size();
            if (!dst.ReceivedBytes(remaining)) { rejected = true; return true; }
            Drain(dst, messages);
            Require(remaining.size() < before, "valid handshake made no receive progress");
        }
        return true;
    };
    for (int step = 0; step < 64 && !rejected; ++step) {
        bool progress = transfer(*init, *resp, resp_received);
        if (!rejected) progress |= transfer(*resp, *init, init_received);
        if (!progress) break;
    }
    // Discard only already-queued own output, without delivering it.
    // An empty buffer rules out handshake back-pressure as the refusal cause.
    size_t drained_handshake_bytes{0};
    for (int step = 0; step < 8; ++step) {
        const auto& [queued, more, type] = init->GetBytesToSend(false);
        (void)more; (void)type;
        if (queued.empty()) break;
        drained_handshake_bytes += queued.size();
        init->MarkBytesSent(queued.size());
    }
    Require(std::get<0>(init->GetBytesToSend(false)).empty(), "own send buffer did not drain");
    CSerializedNetMsg probe;
    probe.m_type = "ping";
    probe.data = {1, 2, 3, 4, 5, 6, 7, 8};
    const auto original_payload = probe.data;
    const bool still_gated = !init->SetMessageToSend(probe) && probe.data == original_payload;
    const bool not_application = init->GetInfo().transport_type == TransportProtocolType::DETECTING;
    const bool pass = rejected && unit::checks == 1 && unit::encapsulations == 0 &&
                      unit::invalid_generated_keys == 0 && !init->IsHybridActiveForTest() &&
                      !resp->IsHybridActiveForTest() && still_gated && not_application &&
                      init_received.empty() && resp_received.empty() && !init->ShouldReconnectV1();
    std::cout << "forced_validation_failure policy=" << (policy == Policy::PQ_ONLY ? "pqonly" : "default")
              << " rejected=" << rejected << " checks=" << unit::checks
              << " encapsulations=" << unit::encapsulations
              << " invalid_generated_keys=" << unit::invalid_generated_keys
              << " drained_handshake_bytes=" << drained_handshake_bytes
              << " send_gate_held_after_drain=" << still_gated << " pre_application=" << not_application
              << " hybrid=" << init->IsHybridActiveForTest() << " pass=" << pass << '\n';
    return pass;
}
}
int main()
{
    try {
        RandomInit();
        ECC_Context ecc;
        unsigned failures{0};
        for (const auto policy : {Policy::DEFAULT_PQ, Policy::PQ_ONLY}) {
            if (!ForcedFailure(policy)) ++failures;
            unit::Reset(false);
            RunFreshConnection("normal_after_unit_failure", policy, policy, true, 0);
            Require(unit::encapsulations == 1 && unit::invalid_generated_keys == 0,
                    "normal recovery did not use a valid generated key exactly once");
        }
        std::cout << "unit_guard_failures=" << failures << '\n';
        return failures ? EXIT_FAILURE : EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "fixture_error=" << error.what() << '\n';
        return 2;
    }
}
