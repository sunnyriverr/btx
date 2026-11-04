// Positive, in-memory interoperability controls for the actual production V2Transport.
// No sockets, injected handshake material, packet mutations, or substitute crypto.
// Build against this task's production source and configured native build headers.

#include <cstdint>

#include <chainparams.h>
#include <common/args.h>
#include <common/settings.h>
#include <key.h>
#include <net.h>
#include <random.h>
#include <span.h>
#include <univalue.h>
#include <util/chaintype.h>
#include <util/translation.h>

#include <algorithm>
#include <array>
#include <cstdlib>
#include <deque>
#include <exception>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

// Production args.cpp supplies gArgs. Standalone executables supply this normal
// application translation callback, as src/test/util/setup_common.cpp does.
const TranslateFn G_TRANSLATION_FUN{nullptr};

// Component fixture: only the network magic consumed by transport is supplied.
// No chain selection, genesis construction or node/chainstate is exercised.
class TransportFixtureParams final : public CChainParams
{
public:
    TransportFixtureParams()
    {
        pchMessageStart = {0xfa, 0xbf, 0xb5, 0xda};
        m_chain_type = ChainType::REGTEST;
    }
};
const CChainParams& Params()
{
    static const TransportFixtureParams params;
    return params;
}

namespace {

void Require(bool condition, const std::string& message)
{
    if (!condition) throw std::runtime_error(message);
}

// Exact restoration includes absence and all settings sources, not just each
// option's effective Boolean. This standalone program has no concurrent readers
// of gArgs. The constructor settings are restored before pumping either peer;
// V2Transport snapshots its two PQ policy flags during construction.
class ScopedArgsSettings final
{
    common::Settings m_saved;

public:
    ScopedArgsSettings()
    {
        gArgs.LockSettings([&](common::Settings& settings) {
            std::swap(settings, m_saved);
        });
    }

    ~ScopedArgsSettings()
    {
        gArgs.LockSettings([&](common::Settings& settings) {
            std::swap(settings, m_saved);
        });
    }

    ScopedArgsSettings(const ScopedArgsSettings&) = delete;
    ScopedArgsSettings& operator=(const ScopedArgsSettings&) = delete;
};

enum class Policy { DEFAULT_PQ, PQ_ONLY, DISABLED_PQ };

std::unique_ptr<V2Transport> MakeTransport(NodeId nodeid, bool initiating, Policy policy)
{
    ScopedArgsSettings restore;
    switch (policy) {
    case Policy::DEFAULT_PQ:
        // No overrides: exercise the production defaults.
        break;
    case Policy::PQ_ONLY:
        gArgs.ForceSetArg("-v2pqonly", "1");
        break;
    case Policy::DISABLED_PQ:
        gArgs.ForceSetArg("-v2pqhybrid", "0");
        break;
    }
    // Actual production constructor generates fresh X25519 material and, when
    // applicable, a responder ML-KEM key pair using production randomness.
    return std::make_unique<V2Transport>(nodeid, initiating);
}

struct ExpectedMessage {
    std::string type;
    std::vector<uint8_t> payload;
};

CSerializedNetMsg Serialize(const ExpectedMessage& expected)
{
    CSerializedNetMsg message;
    message.m_type = expected.type;
    message.data = expected.payload;
    return message;
}

void Drain(V2Transport& transport, std::vector<CNetMessage>& received)
{
    while (transport.ReceivedMessageComplete()) {
        bool reject{false};
        auto message = transport.GetReceivedMessage({}, reject);
        Require(!reject, "legitimate application message was rejected");
        received.push_back(std::move(message));
    }
}

bool Pump(V2Transport& source, std::deque<CSerializedNetMsg>& queued,
          V2Transport& destination, std::vector<CNetMessage>& received)
{
    bool progress{false};
    if (!queued.empty() && source.SetMessageToSend(queued.front())) {
        queued.pop_front();
        progress = true;
    }
    const auto& [data, more, message_type] = source.GetBytesToSend(!queued.empty());
    (void)more;
    (void)message_type;
    if (data.empty()) return progress;

    // Preserve production bytes exactly. MarkBytesSent may release their source
    // buffer, so first copy to the in-memory connection's owned byte vector.
    std::vector<uint8_t> bytes(UCharCast(data.data()), UCharCast(data.data()) + data.size());
    source.MarkBytesSent(bytes.size());
    Span<const uint8_t> remaining{bytes};
    while (!remaining.empty()) {
        const auto old_size = remaining.size();
        Require(destination.ReceivedBytes(remaining), "legitimate transport bytes were rejected");
        const auto old_count = received.size();
        Drain(destination, received);
        Require(remaining.size() < old_size || received.size() > old_count,
                "receive path made no progress");
    }
    return true;
}

void CheckMessage(const CNetMessage& actual, const ExpectedMessage& expected)
{
    Require(actual.m_type == expected.type, "application message type changed");
    Require(actual.m_message_size == expected.payload.size(), "application message size changed");
    Require(std::ranges::equal(actual.m_recv, MakeByteSpan(expected.payload)),
            "application payload changed");
}

void CheckNegotiation(V2Transport& initiator, V2Transport& responder, bool expect_hybrid)
{
    Require(initiator.IsHybridActiveForTest() == expect_hybrid,
            "initiator hybrid state differs from negotiated policy");
    Require(responder.IsHybridActiveForTest() == expect_hybrid,
            "responder hybrid state differs from negotiated policy");
    const auto init_info = initiator.GetInfo();
    const auto resp_info = responder.GetInfo();
    Require(init_info.transport_type == TransportProtocolType::V2 &&
                resp_info.transport_type == TransportProtocolType::V2,
            "legitimate pair did not negotiate V2");
    Require(init_info.session_id.has_value() && init_info.session_id == resp_info.session_id,
            "legitimate pair did not agree on its session id");
}

void RunFreshConnection(const std::string& name, Policy initiator_policy,
                        Policy responder_policy, bool expect_hybrid, uint8_t fresh_index)
{
    // Reuse logical NodeIds across independently constructed connections; no
    // transport object, key pair, cipher, queue, or receive buffer is reused.
    auto initiator = MakeTransport(NodeId{0}, true, initiator_policy);
    auto responder = MakeTransport(NodeId{1}, false, responder_policy);
    std::deque<CSerializedNetMsg> init_queue, resp_queue;
    std::vector<CNetMessage> init_received, resp_received;

    // Round 0 queues ordinary 8-byte ping/pong nonces before handshake completion.
    // Round 1 proves the same connection remains usable after negotiation.
    for (uint8_t round = 0; round < 2; ++round) {
        const ExpectedMessage from_init{
            "ping", {0x11, 0x22, 0x33, 0x44, fresh_index, round, 0x00, 0x81}};
        const ExpectedMessage from_resp{
            "pong", {0x55, 0x66, 0x77, 0x88, fresh_index, round, 0x00, 0x42}};
        init_queue.push_back(Serialize(from_init));
        resp_queue.push_back(Serialize(from_resp));

        bool quiescent{false};
        for (int step = 0; step < 512; ++step) {
            bool progress{false};
            progress |= Pump(*initiator, init_queue, *responder, resp_received);
            progress |= Pump(*responder, resp_queue, *initiator, init_received);
            if (!progress) {
                quiescent = true;
                break;
            }
        }
        Require(quiescent, "pair exceeded bounded in-memory pump steps");
        Require(init_queue.empty() && resp_queue.empty(), "application send queue did not drain");
        Require(init_received.size() == static_cast<size_t>(round + 1) &&
                    resp_received.size() == static_cast<size_t>(round + 1),
                "missing or unexpected application messages");
        CheckMessage(resp_received.back(), from_init);
        CheckMessage(init_received.back(), from_resp);
        CheckNegotiation(*initiator, *responder, expect_hybrid);
    }
    std::cout << "PASS " << name << " fresh=" << unsigned(fresh_index)
              << " hybrid=" << expect_hybrid << " exact_messages=4\n";
}

} // namespace

int main()
{
    try {
        // Minimal production setup, following the V2 transport fuzz initializer.
        // RandomInit is optional in production but explicit here. No node,
        // connection manager, chainstate, datadir, or socket is created.
        RandomInit();
        ECC_Context ecc_context;
        // Params() above is the explicit minimal component-fixture substitution.

        struct Scenario {
            const char* name;
            Policy initiator;
            Policy responder;
            bool hybrid;
        };
        constexpr std::array<Scenario, 7> scenarios{{
            {"default/default", Policy::DEFAULT_PQ, Policy::DEFAULT_PQ, true},
            {"pqonly/pqonly", Policy::PQ_ONLY, Policy::PQ_ONLY, true},
            {"default/pqonly", Policy::DEFAULT_PQ, Policy::PQ_ONLY, true},
            {"pqonly/default", Policy::PQ_ONLY, Policy::DEFAULT_PQ, true},
            {"disabled/disabled", Policy::DISABLED_PQ, Policy::DISABLED_PQ, false},
            {"default/disabled", Policy::DEFAULT_PQ, Policy::DISABLED_PQ, false},
            {"disabled/default", Policy::DISABLED_PQ, Policy::DEFAULT_PQ, false},
        }};
        for (const auto& scenario : scenarios) {
            for (uint8_t fresh_index = 0; fresh_index < 2; ++fresh_index) {
                RunFreshConnection(scenario.name, scenario.initiator, scenario.responder,
                                   scenario.hybrid, fresh_index);
            }
        }
        std::cout << "PASS total_connections=14 exact_messages=56\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "FAIL positive_transport: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
