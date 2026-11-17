// Test-only consumer; production S3PieceStore and persistence are unchanged.
#include <modelnet/s3_store.h>
#include <util/translation.h>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
const TranslateFn G_TRANSLATION_FUN{nullptr};
void need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
int main(int argc,char** argv){try{
 need(argc==2,"work directory required");fs::path root=fs::u8path(argv[1]);fs::create_directories(root);
 auto creds=root/"creds";{std::ofstream f(creds);f<<"aws_access_key_id=AKIATESTKEYNOTREAL00\naws_secret_access_key=not-real-clock-fixture-secret\n";}fs::permissions(creds,fs::perms::owner_read|fs::perms::owner_write);
 // 2026-03-01 01:00 UTC, then 2026-02-28 01:00 and 2026-04-01 01:00.
 constexpr int64_t D=1772326800,PREV=D-86400,NEXT_MONTH=1775005200;
 UniValue all(UniValue::VARR);
 for(int kind=0;kind<4;++kind){
  modelnet::CloudStoreConfig c;c.s3.endpoint="https://acct.r2.cloudflarestorage.com";c.s3.bucket="btx-models";c.s3.prefix="clock-"+std::to_string(kind);c.s3.region="auto";c.s3.use_fake=true;c.s3.creds.kind=modelnet::CredentialRefKind::PATH;c.s3.creds.value=fs::PathToString(creds);c.budget_state_path=root/fs::PathFromString("budget-"+std::to_string(kind)+".json");
  if(kind==0)c.budget_gets_per_day=1;if(kind==1)c.budget_bytes_per_day=6;if(kind==2)c.budget_gets_per_month=1;if(kind==3)c.budget_bytes_per_month=6;
  UniValue row(UniValue::VOBJ);row.pushKV("kind",kind);UniValue events(UniValue::VARR);
  auto read=[&](int64_t clock,const char* name,bool seed){modelnet::S3PieceStore store(c);store.SetClockForTests(clock);std::string err;need(store.Init(err),err.c_str());if(seed){std::istringstream in("daycap");need(store.PutObject("clock-object",in,6,err),err.c_str());}std::vector<unsigned char> out;bool ok=store.GetObject("clock-object",0,0,out,err);if(ok)need(std::string(out.begin(),out.end())=="daycap","payload mismatch");UniValue e(UniValue::VOBJ);e.pushKV("step",name);e.pushKV("clock",clock);e.pushKV("allowed",ok);e.pushKV("error",err);e.pushKV("health",store.HealthJson());events.push_back(e);return ok;};
  need(read(D,"initial",true),"initial control");need(!read(D,"same_day_reopen",false),"same-day cap not preserved");
  bool back=read(PREV,"backward_reopen",false);bool returned=read(D,"return_original_reopen",false);
  need(!read(D,"same_day_after_return",false),"same-day refusal after return");
  need(read(kind<2?D+86400:NEXT_MONTH,"forward_rollover",false),"forward rollover failed");
  row.pushKV("backward_allowed",back);row.pushKV("original_window_allowed_again",returned);row.pushKV("events",events);all.push_back(row);
 }
 std::cout<<all.write()<<"\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 2;}}
