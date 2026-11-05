#include <modelnet/search.h>
#include <iostream>
#include <stdexcept>
using namespace modelnet;
int main() {
    ProviderObservation fresh;
    fresh.provider_id = "remote-a";
    fresh.endpoint = "192.0.2.1:29447";
    fresh.complete = true;
    fresh.direct = true;
    fresh.last_seen_ms = 1800000000000LL;
    ProviderObservation old = fresh;
    old.last_seen_ms -= 30LL * 24 * 60 * 60 * 1000;
    auto view = [](const std::vector<ProviderObservation>& obs) {
        const auto h = ComputeSwarmHealth(0, 0, obs);
        UniValue r(UniValue::VOBJ);
        r.pushKV("availability", AvailabilityJson(h));
        r.pushKV("peercount", PeerCountJson(h));
        return r;
    };
    UniValue records(UniValue::VOBJ);
    const auto f = view({fresh});
    const auto o = view({old});
    const auto empty = view({});
    if (f.write() != o.write()) throw std::runtime_error("age changed current projection");
    if (o["peercount"]["complete"].getInt<int>() != 1 || o["peercount"]["reachable_direct"].getInt<int>() != 1) throw std::runtime_error("old observation not counted");
    if (o["availability"]["class"].get_str() != "UNKNOWN" || o["availability"]["reconstructable_known"].get_bool()) throw std::runtime_error("unknown piece count control");
    if (empty["peercount"]["total"].getInt<int>() != 0) throw std::runtime_error("empty control");
    ProviderObservation partial = fresh;
    partial.provider_id = "remote-b";
    partial.complete = false;
    partial.direct = false;
    partial.relayed = true;
    const auto mixed = view({old, partial});
    if (mixed["peercount"]["total"].getInt<int>() != 2 || mixed["peercount"]["complete"].getInt<int>() != 1 || mixed["peercount"]["partial"].getInt<int>() != 1 || mixed["peercount"]["reachable_direct"].getInt<int>() != 1 || mixed["peercount"]["reachable_relay"].getInt<int>() != 1) throw std::runtime_error("mixed control");
    if (view({fresh, fresh})["peercount"]["total"].getInt<int>() != 1) throw std::runtime_error("dedup control");
    records.pushKV("fresh", f);
    records.pushKV("thirty_day_old", o);
    records.pushKV("empty", empty);
    records.pushKV("mixed", mixed);
    records.pushKV("scope", "Exact health/JSON projection component only; synthetic observations, no remote peer/provider admission or withdrawal executed");
    std::cout << records.write() << '\n';
}
