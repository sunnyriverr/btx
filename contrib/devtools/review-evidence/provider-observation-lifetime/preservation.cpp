#include <algorithm>
#include <cassert>
#include <map>
#include <mutex>
#include <string>
#include <vector>
struct Digest48 { std::string value; std::string Hex() const { return value; } };
struct ProviderObservation { std::string provider_id; };
struct CatalogEntry { bool seeded=false; };
struct ModelCatalog { bool exists=false, seeded=false; bool Find(const Digest48&, CatalogEntry& e) { e.seeded=seeded;return exists; } };
static std::mutex g_search_mu;
static std::map<std::string,std::vector<ProviderObservation>> g_search_obs;
void ForgetLocalProviderObservation(ModelCatalog& cat, const Digest48& id)
{
    std::lock_guard<std::mutex> lock(g_search_mu);
    CatalogEntry entry;
    if (cat.Find(id, entry) && entry.seeded) return; // A concurrent reseed wins.
    auto it = g_search_obs.find(id.Hex());
    if (it == g_search_obs.end()) return;
    auto& obs = it->second;
    obs.erase(std::remove_if(obs.begin(), obs.end(),
                             [](const ProviderObservation& o) { return o.provider_id == "local"; }),
              obs.end());
    if (obs.empty()) g_search_obs.erase(it);
}

int main() {
 ModelCatalog cat; Digest48 id{"model"};
 g_search_obs[id.Hex()]={{"local"},{"peer-a"},{"peer-b"}};
 ForgetLocalProviderObservation(cat,id);
 assert(g_search_obs.at(id.Hex()).size()==2);
 assert(g_search_obs.at(id.Hex())[0].provider_id=="peer-a");
 assert(g_search_obs.at(id.Hex())[1].provider_id=="peer-b");
 g_search_obs[id.Hex()]={{"local"}};
 ForgetLocalProviderObservation(cat,id);assert(g_search_obs.empty());
 ForgetLocalProviderObservation(cat,id);assert(g_search_obs.empty());
 cat.exists=true;cat.seeded=true;g_search_obs[id.Hex()]={{"local"},{"peer-a"}};
 ForgetLocalProviderObservation(cat,id);assert(g_search_obs.at(id.Hex()).size()==2);
}
