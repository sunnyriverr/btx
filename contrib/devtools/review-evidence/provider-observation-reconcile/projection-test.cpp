#include <cassert>
#include <cstdint>
#include <map>
#include <string>
#include <utility>
#include <vector>
struct Digest48 { std::string value; std::string Hex() const { return value; } };
struct ProviderObservation { std::string provider_id, endpoint; bool complete=false,direct=true,relayed=false; int64_t last_seen_ms=0; std::vector<int> ranges; std::string netgroup; };
struct CatalogEntry { bool seeded=false,incomplete=false; };
struct ModelCatalog { bool exists=false; CatalogEntry entry; bool Find(const Digest48&,CatalogEntry& out) { out=entry;return exists; } };
static std::map<std::string,std::vector<ProviderObservation>> g_search_obs;
int64_t ConnNowMs() { return 100; }
std::vector<ProviderObservation> CurrentProviderObservations(ModelCatalog& cat, const Digest48& id)
{
    std::vector<ProviderObservation> observations;
    const auto it = g_search_obs.find(id.Hex());
    if (it != g_search_obs.end()) observations = it->second;
    CatalogEntry entry;
    if (cat.Find(id, entry) && entry.seeded) {
        ProviderObservation local;
        local.provider_id = "local";
        local.endpoint = "local";
        local.complete = !entry.incomplete;
        local.last_seen_ms = ConnNowMs();
        observations.push_back(std::move(local));
    }
    return observations;
}

int main() {
 ModelCatalog cat;Digest48 id{"test"};
 assert(CurrentProviderObservations(cat,id).empty());assert(g_search_obs.empty());
 ProviderObservation partial;partial.provider_id="remote-partial";partial.complete=false;
 partial.direct=false;partial.relayed=true;partial.last_seen_ms=42;partial.ranges={2,3};
 g_search_obs[id.Hex()]={partial};
 cat.exists=true;cat.entry.seeded=true;
 auto values=CurrentProviderObservations(cat,id);assert(values.size()==2);
 assert(values[0].provider_id=="remote-partial" && !values[0].complete && values[0].relayed);
 assert(values[0].ranges==partial.ranges && values[0].last_seen_ms==42);
 assert(values[1].provider_id=="local" && values[1].complete && values[1].direct);
 assert(g_search_obs.at(id.Hex()).size()==1); // synthesized local never cached
 cat.entry.seeded=false;values=CurrentProviderObservations(cat,id);
 assert(values.size()==1 && values[0].provider_id=="remote-partial");
 cat.entry.seeded=true;cat.entry.incomplete=true;values=CurrentProviderObservations(cat,id);
 assert(values.size()==2 && !values[1].complete); // represented partial remains partial
 cat.entry.seeded=false;values=CurrentProviderObservations(cat,id);assert(values.size()==1);
 cat.exists=false;assert(CurrentProviderObservations(cat,id).size()==1);
 assert(g_search_obs.at(id.Hex())[0].ranges==partial.ranges);
}
