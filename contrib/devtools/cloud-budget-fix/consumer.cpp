// Local qualification consumer of the unmodified S3PieceStore/FakeS3 objects.
#include <modelnet/s3_store.h>
#include <univalue.h>
#include <util/fs.h>
#include <util/translation.h>
#include <csignal>
#include <exception>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <sys/resource.h>
#include <vector>
// Same executable-owned translation hook as src/modeld.cpp.
const TranslateFn G_TRANSLATION_FUN{nullptr};
using namespace modelnet;
constexpr int64_t DAY=86400LL*20000+3600;
void require(bool x,const std::string& why){if(!x)throw std::runtime_error(why);}
std::string bytes(const fs::path& p){std::ifstream f(p,std::ios::binary);require(bool(f),"read failed");return std::string(std::istreambuf_iterator<char>(f),{});}
UniValue file_json(const fs::path& p){UniValue v;require(v.read(bytes(p))&&v.isObject(),"budget parse failed");return v;}
UniValue counts(const UniValue& v){UniValue out(UniValue::VOBJ);for(const auto* k:{"day_gets","month_gets","used_gets","day_bytes","month_bytes","used_bytes"})out.pushKV(k,v[k].getInt<int64_t>());return out;}
class FileLimit {
 rlimit old{};using Handler=void(*)(int);Handler handler{SIG_ERR};
public:
 explicit FileLimit(rlim_t n){require(getrlimit(RLIMIT_FSIZE,&old)==0,"getrlimit");handler=std::signal(SIGXFSZ,SIG_IGN);require(handler!=SIG_ERR,"signal");auto now=old;now.rlim_cur=n;if(setrlimit(RLIMIT_FSIZE,&now)){std::signal(SIGXFSZ,handler);throw std::runtime_error("setrlimit");}}
 ~FileLimit(){if(setrlimit(RLIMIT_FSIZE,&old)||std::signal(SIGXFSZ,handler)==SIG_ERR)std::terminate();}
};
int main(int argc,char** argv){
 UniValue report(UniValue::VOBJ);fs::path output;
 try{
  require(argc==3,"usage: consumer workdir output");fs::path root=fs::u8path(argv[1]);output=fs::u8path(argv[2]);fs::create_directories(root);
  auto creds=root/"credentials";{std::ofstream f(creds);f<<"aws_access_key_id=AKIATESTKEYNOTREAL00\naws_secret_access_key=super-secret-cloud-value-xyz\n";require(bool(f),"credentials write");}
  fs::permissions(creds,fs::perms::owner_read|fs::perms::owner_write,fs::perm_options::replace);
  CloudStoreConfig cfg;cfg.s3.endpoint="https://acct.r2.cloudflarestorage.com";cfg.s3.bucket="btx-models";cfg.s3.prefix="v1";cfg.s3.region="auto";cfg.s3.use_fake=true;cfg.s3.creds.kind=CredentialRefKind::PATH;cfg.s3.creds.value=fs::PathToString(creds);cfg.budget_gets_per_day=1;cfg.budget_state_path=root/"budget.json";
  const auto source=root/"object.bin";{std::ofstream f(source,std::ios::binary);f<<"daycap";require(bool(f),"payload write");}
  Digest48 art{};art.data.fill(0x46);
  auto init=[&](S3PieceStore& s,int64_t day){s.SetClockForTests(day);std::string e;require(s.Init(e),"healthy Init: "+e);};
  auto put=[&](S3PieceStore& s){std::string e;require(s.PutSourceFile(art,0,source,6,1,e),"PUT: "+e);};
  auto get=[&](S3PieceStore& s){UniValue r(UniValue::VOBJ);std::string e;std::vector<unsigned char> b;bool ok=s.GetSourceFile(art,0,b,e);r.pushKV("get_ok",ok);r.pushKV("payload",std::string(b.begin(),b.end()));r.pushKV("error",e);return r;};
  auto valid=[&](const UniValue& g){require(g["get_ok"].get_bool()&&g["payload"].get_str()=="daycap","normal GET payload");};
  auto denied=[&](const UniValue& g){require(!g["get_ok"].get_bool()&&g["error"].get_str().find("budget")!=std::string::npos,"expected budget refusal");};
  // Independent clean sequence, not contaminated by the later failed rewrite.
  {auto clean=cfg;clean.budget_state_path=root/"clean-budget.json";
   {S3PieceStore s(clean);init(s,DAY);put(s);valid(get(s));denied(get(s));}
   {S3PieceStore s(clean);init(s,DAY);put(s);denied(get(s));s.SetClockForTests(DAY+86400);valid(get(s));denied(get(s));}
   auto v=file_json(clean.budget_state_path);require(v["month_gets"].getInt<int64_t>()==2&&v["used_bytes"].getInt<int64_t>()==12,"clean rollover counts");}
  report.pushKV("clean_rollover_control",true);
  {S3PieceStore s(cfg);init(s,DAY);put(s);valid(get(s));denied(get(s));}
  const auto committed=bytes(cfg.budget_state_path);auto seeded=file_json(cfg.budget_state_path);
  UniValue seed(UniValue::VOBJ);seed.pushKV("counters",counts(seeded));seed.pushKV("valid_json",true);seed.pushKV("payload","daycap");seed.pushKV("file_bytes",int64_t(committed.size()));report.pushKV("seed",seed);
  {S3PieceStore s(cfg);init(s,DAY);put(s);auto g=get(s);denied(g);g.pushKV("put_ok",true);report.pushKV("healthy_reopen",g);}
  UniValue fault(UniValue::VOBJ);bool ok,ready;std::string e;
  {FileLimit limited(committed.size()/2);S3PieceStore s(cfg);s.SetClockForTests(DAY);ok=s.Init(e);ready=s.IsReady();}
  fault.pushKV("init_ok",ok);fault.pushKV("ready",ready);fault.pushKV("error",e);fault.pushKV("no_origin_get",true);fault.pushKV("limit_bytes",int64_t(committed.size()/2));
  auto damaged=bytes(cfg.budget_state_path);UniValue parsed;fault.pushKV("invalid_json_after",!parsed.read(damaged));fault.pushKV("committed_bytes_preserved",damaged==committed);fault.pushKV("after_file_bytes",int64_t(damaged.size()));report.pushKV("fault",fault);
  {S3PieceStore s(cfg);init(s,DAY);put(s);auto recovered=file_json(cfg.budget_state_path);report.pushKV("day_after",recovered["day_utc"].getInt<int64_t>());report.pushKV("month_after",recovered["month_utc"].getInt<int64_t>());auto counter=counts(recovered);auto g=get(s);g.pushKV("counters_before_get",counter);g.pushKV("init_ok",true);g.pushKV("put_ok",true);report.pushKV("recovered",g);}
  {S3PieceStore s(cfg);init(s,DAY+86400);put(s);auto first=get(s),second=get(s);UniValue roll(UniValue::VOBJ);roll.pushKV("day",file_json(cfg.budget_state_path)["day_utc"].getInt<int64_t>());roll.pushKV("month",file_json(cfg.budget_state_path)["month_utc"].getInt<int64_t>());roll.pushKV("put_ok",true);roll.pushKV("first_get_ok",first["get_ok"].get_bool());roll.pushKV("payload",first["payload"].get_str());roll.pushKV("second_get_ok",second["get_ok"].get_bool());roll.pushKV("error",second["error"].get_str());roll.pushKV("counters",counts(file_json(cfg.budget_state_path)));report.pushKV("rollover",roll);}
  {cfg.budget_state_path.clear();S3PieceStore s(cfg);init(s,DAY);put(s);valid(get(s));denied(get(s));s.SetClockForTests(DAY+86400);valid(get(s));denied(get(s));}
  report.pushKV("in_memory_control",true);report.pushKV("fault_scope_restored",true);report.pushKV("day_before",int64_t(20000));report.pushKV("month_before",seeded["month_utc"].getInt<int64_t>());report.pushKV("budget_path",fs::PathToString(root/"budget.json"));report.pushKV("complete",true);report.pushKV("skipped",false);report.pushKV("schema",1);
  std::ofstream out(output);out<<report.write()<<"\n";require(bool(out),"report write");return 0;
 }catch(const std::exception& e){if(!output.empty()){report.pushKV("setup_error",e.what());report.pushKV("complete",false);std::ofstream out(output);out<<report.write()<<"\n";}return 2;}
}
