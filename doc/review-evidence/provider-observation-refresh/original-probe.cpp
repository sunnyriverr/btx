#include <modelnet/catalog.h>
#include <modelnet/helper.h>
#include <modelnet/identity.h>
#include <modelnet/provider_route.h>
#include <util/fs.h>
#include <util/translation.h>
#include <univalue.h>
#include <chrono>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
const TranslateFn G_TRANSLATION_FUN{nullptr};
using namespace modelnet;
static void Require(bool v, const std::string& why) { if (!v) throw std::runtime_error(why); }
static UniValue Native(ModelCatalog& cat, const std::string& route, const UniValue& body, int expected_status=200) {
    NativeRequest req;
    req.method="POST";req.path="/btx-model/2/"+route;req.body=body.write();req.peer_addr="fixture-provider";
    NativeResponse resp;
    Require(HandleNativeRequest(cat,req,resp),"native route missing");
    Require(resp.status==expected_status,"native status "+std::to_string(resp.status)+": "+resp.body);
    UniValue value;Require(value.read(resp.body),"native reply JSON");return value;
}
static UniValue Rpc(ModelCatalog& cat,const std::string& method,const UniValue& params) {
    UniValue req(UniValue::VOBJ);req.pushKV("method",method);req.pushKV("params",params);
    UniValue out;std::string code,err;
    Require(DispatchHelperRpc(cat,req,out,code,err),method+": "+code+" "+err);return out;
}
int main(int argc,char** argv) {
    try {
        Require(argc==4,"root fixture initial-complete");
        fs::path root=fs::PathFromString(argv[1]);fs::create_directories(root);fs::current_path(root);
        ModelCatalog cat(root/"models",64*1024*1024);
        CatalogEntry entry;std::string err;
        Require(cat.ImportPath(argv[2],false,entry,err),"import: "+err);
        Require(cat.Seed(entry.model_id,false,err),"unseed fixture: "+err);
        UniValue query(UniValue::VOBJ);query.pushKV("scope","LOCAL");query.pushKV("text","");query.pushKV("limit",10);
        UniValue search_params(UniValue::VARR);search_params.push_back(query);
        UniValue id_params(UniValue::VARR);id_params.push_back(entry.model_id.Hex());
        Rpc(cat,"searchmodels",search_params);
        Require(Rpc(cat,"getmodelproviders",id_params)["providers"].size()==0,"fixture has unexpected provider");
        std::vector<unsigned char> pk,sk;Require(GenerateMlDsa44(pk,sk,err),"keygen: "+err);
        ProviderRecord rec;rec.resource=entry.model_id;rec.pubkey=pk;rec.seq=10;
        rec.complete=std::string(argv[3])=="1";rec.reachability_kind="direct";rec.endpoints={"192.0.2.10:29447"};
        rec.expiry_ms=std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch()).count()+300000;
        rec.ranges={{0,1}};
        auto sign=[&]{Require(SignProviderRecord(rec,Span<const unsigned char>{sk.data(),sk.size()},err),"sign: "+err);};
        sign();Native(cat,"ext/providers/put",ProviderRecordToJson(rec));
        Rpc(cat,"searchmodels",search_params);
        UniValue before=Rpc(cat,"getmodelproviders",id_params);
        Require(before["providers"].size()==1,"first provider missing");
        Require(before["providers"][0]["complete"].get_bool()==rec.complete,"initial completeness mismatch");
        const bool initial=rec.complete;
        rec.seq=11;rec.complete=!initial;rec.reachability_kind="relay";sign();
        const UniValue accepted=Native(cat,"ext/providers/put",ProviderRecordToJson(rec));
        Require(accepted["ok"].get_bool(),"new record not accepted");
        UniValue lookup(UniValue::VOBJ);lookup.pushKV("resource",entry.model_id.Hex());
        const UniValue cache=Native(cat,"ext/providers/get",lookup);
        Require(cache["records"].size()==1,"cache identity count changed");
        Require(cache["records"][0]["seq"].getInt<int>()==11,"new seq not retained");
        Require(cache["records"][0]["complete"].get_bool()==rec.complete,"cache not updated");
        Require(cache["records"][0]["reachability_kind"].get_str()=="relay","cache route not updated");
        const UniValue search=Rpc(cat,"searchmodels",search_params);
        const UniValue after=Rpc(cat,"getmodelproviders",id_params);
        Require(after["providers"].size()==1,"observation identity count changed");
        const UniValue availability=Rpc(cat,"getmodelavailability",id_params);
        const UniValue peers=Rpc(cat,"getmodelpeercount",id_params);
        const bool matches=after["providers"][0]["complete"].get_bool()==rec.complete && after["providers"][0]["relayed"].get_bool();
        // A previous, still-valid signed sequence must not displace seq11.
        rec.seq=9;sign();Native(cat,"ext/providers/put",ProviderRecordToJson(rec),403);
        const auto rollback=Native(cat,"ext/providers/get",lookup);
        Require(rollback["records"][0]["seq"].getInt<int>()==11,"rollback displaced new sequence");
        UniValue out(UniValue::VOBJ);out.pushKV("initial_complete",initial);out.pushKV("latest_complete",!initial);
        out.pushKV("accepted_new_record",true);out.pushKV("new_cache_record",cache["records"][0]);
        out.pushKV("before",before);out.pushKV("after",after);out.pushKV("availability",availability);out.pushKV("peercount",peers);out.pushKV("search",search);
        out.pushKV("rollback_refused",true);out.pushKV("display_matches_latest",matches);
        std::cout<<out.write()<<'\n';return matches?0:1;
    } catch(const std::exception& e) {std::cerr<<"SETUP_OR_CONTROL_FAILURE: "<<e.what()<<'\n';return 2;}
}
