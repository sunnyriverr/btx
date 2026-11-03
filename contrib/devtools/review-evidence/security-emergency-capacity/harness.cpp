// Copyright (c) 2026 The BTX developers. MIT license.
// All identities, credentials and model tensors below are synthetic fixtures.
// Two signer identities on this test host do NOT qualify two physical hosts.
#include <modelnet/security_v2/lifecycle.h>
#include <modelnet/security_v2/broker.h>
#include <modelnet/security_v2/mesh.h>
#include <modelnet/security_v2/work.h>
#include <tuple>
#include <thread>
#include <atomic>
#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <memory>
#ifndef _WIN32
#include <sys/stat.h>
#include <unistd.h>
#endif
using namespace modelnet::security;
namespace {
struct Harness {
    size_t passed{0},failed{0};Json results=Array();
    template<class F> void Test(const std::string& name,F f) {
        Json row=Object();row.pushKV("name",name);
        try{f();++passed;row.pushKV("status","PASS");std::cout<<"PASS "<<name<<'\n';}
        catch(const std::exception& e){++failed;row.pushKV("status","FAIL");row.pushKV("error",e.what());std::cerr<<"FAIL "<<name<<": "<<e.what()<<'\n';}
        results.push_back(row);
    }
};
void Check(bool value,const char* text){if(!value)throw std::runtime_error(text);}
template<class F> void Reject(F f,std::string_view expected={}) {
    try{f();}catch(const Error& e){if(!expected.empty()&&e.code!=expected)throw std::runtime_error("expected "+std::string(expected)+", received "+e.code);return;}
    throw std::runtime_error("expected refusal");
}
struct Temp {
    fs::path root;
    Temp(){root=fs::canonical(fs::temp_directory_path())/("btx-security-test-"+Hex(RandomBytes(12)));EnsurePrivateDirectory(root);}
    ~Temp(){std::error_code ec;fs::remove_all(root,ec);}
};
const std::vector<std::string> GATES{"external-controls","outcome","revocation","rollback","privacy","adversarial"};
Json Signed(const std::string& kind,const Json& body,const KeyPair& a,const KeyPair* b=nullptr) {
    auto e=Envelope(kind,body);AddSignature(e,a);if(b)AddSignature(e,*b);return e;
}
Json Common(const std::string& realm,uint64_t epoch,int64_t now,uint64_t ttl=60000) {
    auto b=Object();b.pushKV("realm",realm);b.pushKV("policy_epoch",epoch);b.pushKV("issued_ms",now);b.pushKV("expires_ms",static_cast<uint64_t>(now)+ttl);return b;
}
Json signed_records=Array();
struct Fixture {
    Temp temp;fs::path root;std::unique_ptr<Database> connection;Database& db;
    KeyPair owner=GenerateKey(),publisher=GenerateKey(),second=GenerateKey(),alice=GenerateKey(),bob=GenerateKey();
    std::string realm=Hash("test realm"),session=Hex(RandomBytes(32)),runtime=Hash("test runtime"),schema=Hash("tool schema");
    int64_t now=NowMs()-5000;Json policy_record,local;
    Policy policy;
    fs::path probe;
    std::string capsule,composition;std::vector<std::string> evaluations;
    explicit Fixture(fs::path executable={},bool common_domain=false,int64_t offset=5000):root(temp.root/"security"),connection(std::make_unique<Database>(root)),db(*connection),probe(std::move(executable)) {
        now=NowMs()-offset;
        if(!probe.empty())runtime=Hash(ReadFile(probe,128*1024*1024));
        auto pins=Object();pins.pushKV("schema","BTX/SecurityRootPins/v1");pins.pushKV("keys",Strings({KeyId(owner.public_key)}));pins.pushKV("threshold",1);WritePrivate(root/"root-pins.json",Canonical(pins));
        Json b=Object();b.pushKV("realm",realm);b.pushKV("epoch",1);b.pushKV("issued_ms",now);b.pushKV("expires_ms",now+3600000);
        b.pushKV("release_threshold",2);b.pushKV("evaluator_domains",2);b.pushKV("physical_hosts",2);b.pushKV("evidence_ttl_ms",60000);
        b.pushKV("canary_ms",1000);b.pushKV("trial_limit",8);b.pushKV("gates",Strings(GATES));Json principals=Array();
        auto principal=[&](const KeyPair& key,std::vector<std::string> roles,std::string domain,std::string host,std::string pin="") {
            Json p=Object();p.pushKV("public_key",Hex(key.public_key));p.pushKV("roles",Strings(roles));p.pushKV("domain",domain);p.pushKV("host",host);p.pushKV("transport_pin",pin);principals.push_back(p);
        };
        principal(owner,{"owner","release","revoker","coordinator","witness","peer"},"owner","owner-host",Hash("pin-owner"));
        principal(publisher,{"publisher"},"author","publisher-host");principal(second,{"release","revoker"},"release","release-host");
        principal(alice,{"evaluator","worker","peer"},"eval-a","host-a",Hash("pin-a"));
        principal(bob,{"evaluator","worker","peer"},common_domain?"eval-a":"eval-b","host-b",Hash("pin-b"));
        b.pushKV("principals",principals);policy_record=Signed("policy",b,owner);InstallPolicy(db,policy_record,now);signed_records.push_back(policy_record);policy=Policy::Load(db,now);
        EnsurePrivateDirectory(temp.root/"workspace");WritePrivate(temp.root/"workspace"/"source.txt","hello safe workspace\n");
        WritePrivate(temp.root/"workspace"/".env","SYNTHETIC_DECOY=not-a-real-secret\n");
        local=Object();local.pushKV("schema","BTX/SecurityLocal/v1");local.pushKV("host","host-a");auto work=Object();work.pushKV("code",(temp.root/"workspace").string());local.pushKV("workspaces",work);
        local.pushKV("packages",Object());local.pushKV("evaluation_plans",Object());local.pushKV("runtimes",Object());
        auto identity=Object();identity.pushKV("public_key",Hex(alice.public_key));identity.pushKV("secret_file",(root/"worker.key").string());local.pushKV("identity",identity);WritePrivate(root/"worker.key",Hex(alice.secret_key));
        auto compute=Object();compute.pushKV("allow_evaluation",true);compute.pushKV("max_memory_bytes",512*1024*1024);compute.pushKV("max_wall_ms",5000);compute.pushKV("max_cpu_ms",4000);local.pushKV("execution_policy",compute);SaveLocal();
        composition=MakeComposition("base");capsule=MakeEvidence(composition);
    }
    void SaveLocal(){WritePrivate(root/"local.json",Canonical(local),true);}
    std::string Import(const Json& e){ImportRecord(db,policy,e,now);signed_records.push_back(e);return RecordId(e);}
    Json Context(const std::string& c={}) {auto x=Object();x.pushKV("realm",realm);x.pushKV("composition",c.empty()?composition:c);x.pushKV("runtime",runtime);x.pushKV("tool_schema",schema);x.pushKV("session",session);return x;}
    std::string MakeComposition(const std::string& version,const std::vector<std::string>& parents={}) {
        auto b=Object();b.pushKV("realm",realm);b.pushKV("policy_epoch",1);b.pushKV("runtime",runtime);b.pushKV("sandbox",StaticSandboxDigest());b.pushKV("tool_schema",schema);b.pushKV("system_prompt",Hash("fixed system prompt"));b.pushKV("parents",Strings(parents));b.pushKV("contributors",Strings({KeyId(publisher.public_key)}));b.pushKV("license","MIT-test-fixture");b.pushKV("architecture","synthetic-fixture-not-an-LLM");b.pushKV("visibility","public");
        auto files=Array();const auto source=temp.root/("source-"+version);EnsurePrivateDirectory(source);
        const std::vector<std::pair<std::string,std::string>> components{{"weights.safetensors","weights"},{"tokenizer.json","tokenizer"},{"config.json","config"},{"chat.txt","chat_template"}};
        for(const auto& [path,role]:components) {
            std::string bytes=role=="weights"?std::string("synthetic tensors ")+version:std::string("{} ")+version;
            WritePrivate(source/path,bytes);auto f=Object();f.pushKV("path",path);f.pushKV("role",role);f.pushKV("sha384",Hash(bytes));f.pushKV("bytes",static_cast<uint64_t>(bytes.size()));files.push_back(f);
        }
        b.pushKV("files",files);auto e=Signed("composition",b,publisher);auto id=Import(e);ImportResident(db,policy,id,source,1024*1024,now);return id;
    }
    Json Challenge(const std::string& c,const std::string& gate,std::string package={}) {
        auto b=Common(realm,1,now);b.pushKV("composition",c);b.pushKV("campaign",Hash("campaign "+gate));b.pushKV("suite",Hash("suite "+gate));b.pushKV("sample_commitment",Hash("samples "+gate));b.pushKV("package",package.empty()?Hash("test package "+gate):package);b.pushKV("gate",gate);b.pushKV("trial_limit",8);return Signed("challenge",b,owner);
    }
    Json Receipt(const std::string& c,const std::string& request,const std::string& package,
                 const KeyPair& key,const std::string& host,int64_t timestamp,std::string output=Hash("output")) {
        auto b=Common(realm,1,timestamp);b.pushKV("job",Hash(Hex(RandomBytes(16))));b.pushKV("request",request);b.pushKV("package",package);b.pushKV("composition",c);b.pushKV("runtime",runtime);b.pushKV("sandbox",StaticSandboxDigest());b.pushKV("outcome","PASS");b.pushKV("output_digest",output);b.pushKV("output_bytes",100);b.pushKV("host",host);b.pushKV("limits",Object());b.pushKV("dispatched",true);return Signed("receipt",b,key);
    }
    Json Evaluation(const Json& challenge,const KeyPair& key,const std::string& host,std::string outcome="PASS") {
        const auto& ch=challenge["body"];const auto challenge_id=RecordId(challenge);
        const auto receipt=Receipt(Text(ch,"composition"),challenge_id,Text(ch,"package"),key,host,now);
        auto receipt_id=Import(receipt);auto b=Common(realm,1,now);
        for(auto field:{"composition","campaign","suite","sample_commitment","gate"})b.pushKV(field,ch[field]);
        b.pushKV("challenge",challenge_id);b.pushKV("runtime",runtime);b.pushKV("sandbox",StaticSandboxDigest());b.pushKV("outcome",outcome);b.pushKV("cases",50);b.pushKV("execution_receipt",receipt_id);b.pushKV("output_digest",receipt["body"]["output_digest"]);b.pushKV("host",host);b.pushKV("physical_host_evidence",host);b.pushKV("limitations",Strings({"SYNTHETIC_ATTESTATION_FIXTURE_ONE_PHYSICAL_TEST_HOST"}));return Signed("evaluation",b,key);
    }
    std::string Capsule(const std::string& c,const std::vector<std::string>& reports,uint64_t ttl=60000) {
        auto b=Common(realm,1,now,ttl);b.pushKV("composition",c);b.pushKV("evaluations",Strings(reports));b.pushKV("profile","restricted-tools");return Import(Signed("capsule",b,owner,&second));
    }
    std::string MakeEvidence(const std::string& c) {
        std::vector<std::string> reports;
        for(const auto& gate:GATES){auto ch=Challenge(c,gate);Import(ch);reports.push_back(Import(Evaluation(ch,alice,"host-a")));reports.push_back(Import(Evaluation(ch,bob,"host-b")));}
        evaluations=reports;return Capsule(c,reports);
    }
    std::string Grant(unsigned calls=4) {
        auto b=Common(realm,1,now);b.pushKV("composition",composition);b.pushKV("channel","");b.pushKV("capsule",capsule);b.pushKV("runtime",runtime);b.pushKV("tool_schema",schema);b.pushKV("session",session);b.pushKV("workspace","code");b.pushKV("tools",Strings({"read","hash","write-new","run-static"}));b.pushKV("read_paths",Strings({"source.txt","link.txt"}));b.pushKV("write_paths",Strings({"new.txt"}));std::vector<std::string> packages;for(const auto& x:local["packages"].getKeys())packages.push_back(x);b.pushKV("packages",Strings(packages));b.pushKV("max_calls",calls);b.pushKV("max_bytes",262144);b.pushKV("per_action_bytes",65536);return Import(Signed("grant",b,owner));
    }
    Json Revocation(const std::string& id){auto b=Common(realm,1,now);b.pushKV("subject",id);b.pushKV("sequence",1);b.pushKV("reason","test incident");return Signed("revocation",b,owner,&second);}
    Json ReadRequest(){auto r=Object();r.pushKV("tool","read");r.pushKV("path","source.txt");return r;}
    std::string InstallProbePackage(){auto p=Object();p.pushKV("executable",probe.string());p.pushKV("sha384",Hash(ReadFile(probe,128*1024*1024)));p.pushKV("sandbox",StaticSandboxDigest());p.pushKV("wall_ms",1000);p.pushKV("cpu_ms",1000);p.pushKV("memory_bytes",256*1024*1024);const auto id=DomainHash("BTX/LocalStaticPackage/v1",Canonical(p));auto packages=local["packages"];packages.pushKV(id,p);local.pushKV("packages",packages);SaveLocal();return id;}
    Json FollowMandate(std::string runtime_id={}){auto b=Common(realm,1,now);b.pushKV("channel","coding/stable");b.pushKV("profile","restricted-tools");b.pushKV("runtimes",Strings({runtime_id.empty()?runtime:runtime_id}));b.pushKV("tool_schemas",Strings({schema}));b.pushKV("automatic_follow",true);return Signed("mandate",b,owner);}
    Json Channel(unsigned seq,const std::string& cap,std::string previous=""){auto b=Common(realm,1,now);b.pushKV("name","coding/stable");b.pushKV("sequence",seq);b.pushKV("capsule",cap);b.pushKV("previous",previous);return Signed("channel",b,owner,&second);}
};
uint64_t Count(Database& db){return ParseUInt(db.Query("SELECT count(*) FROM objects")[0][0]);}
std::string Phase(Database& db,const Json& permit){return db.Query("SELECT phase FROM permits WHERE id=?",{Text(permit,"permit")})[0][0];}
Json Control(Fixture& f){auto b=Common(f.realm,1,f.now);b.pushKV("operation","resume");b.pushKV("nonce",Hex(RandomBytes(32)));return Signed("control",b,f.owner);}
Json NextPolicy(Fixture& f){auto b=f.policy_record["body"];b.pushKV("epoch",2);return Signed("policy",b,f.owner);}
Json observations=Object();
void Observe(const char* name,const Json& value){observations.pushKV(name,value);}
Json Snapshot(Database& db){
 auto out=Object();
 for(const auto& t:db.Query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")){
  auto name=t[0]; std::string order;
  for(const auto& c:db.Query("PRAGMA table_info(\""+name+"\")")){if(!order.empty())order+=",";order+="\""+c[1]+"\"";}
  std::string bytes;uint64_t count=0;
  while(true){auto rows=db.Query("SELECT * FROM \""+name+"\" ORDER BY "+order+" LIMIT 256 OFFSET ?",{std::to_string(count)});if(rows.empty())break;
   for(const auto& row:rows)for(const auto& col:row)bytes+=std::to_string(col.size())+":"+col;count+=rows.size();}
  auto state=Object();state.pushKV("rows",count);state.pushKV("sha384",Hash(bytes));out.pushKV(name,state);
 }return out;
}
Json Read(Broker& broker,Fixture& f,const std::string& grant){
    auto p=broker.Prepare(grant,f.Context(),f.ReadRequest(),f.now);
    auto r=broker.Execute(Text(p,"secret"),f.Context(),f.ReadRequest(),f.now);
    Check(Boolean(r,"ok")&&Boolean(r,"dispatched"),"harmless broker read did not dispatch");
    Check(Text(r,"output_digest")==Hash("hello safe workspace\n"),"wrong harmless read digest");
    return r;
}

}

void Fill(Fixture& f){Database::Transaction tx(f.db);for(uint64_t i=Count(f.db);i<16384;++i){auto b=Object();b.pushKV("fixture_only_unsigned_count",i);f.db.Put(Envelope("control",b));}tx.Commit();Check(Count(f.db)==16384,"exact baseline cap not constructed");}
Json Rev(Fixture& f,const std::string& subject,uint64_t n=1,uint64_t epoch=1){auto b=Common(f.realm,epoch,f.now);b.pushKV("subject",subject);b.pushKV("sequence",n);b.pushKV("reason","synthetic emergency test");return Signed("revocation",b,f.owner,&f.second);}
void StableReject(Database& db,const std::function<void()>& fn,std::string_view code){auto before=Canonical(Snapshot(db));Reject(fn,code);Check(Canonical(Snapshot(db))==before,"rejected transaction changed persistent state");}

int main(int argc,char** argv){Harness h;
    h.Test("below-cap-legitimate-authority-and-read-controls",[]{
        Fixture f;Broker b(f.db,std::string(64,'a'));auto grant=f.Grant(20);
        auto out=Object();out.pushKV("initial_objects",Count(f.db));out.pushKV("read",Read(b,f,grant));
        auto p=b.Prepare(grant,f.Context(),f.ReadRequest(),f.now);b.Pause(f.now);
        Check(f.db.Meta("paused")=="1"&&Phase(f.db,p)=="revoked","below-cap pause failed");
        auto resume=Control(f);signed_records.push_back(resume);b.Resume(resume,f.now);
        Check(f.db.Meta("paused")=="0"&&b.CanRelease(grant,f.Context(),f.ReadRequest(),f.now),"below-cap resume did not restore current authority");
        auto revocation=f.Revocation(grant);f.Import(revocation);
        Check(f.db.Has(RecordId(revocation))&&f.db.Revoked(grant,f.now),"valid below-cap revocation not authoritative");
        Check(!b.CanRelease(grant,f.Context(),f.ReadRequest(),f.now),"revoked grant still usable");
        auto next=NextPolicy(f);signed_records.push_back(next);InstallPolicy(f.db,next,f.now);
        Check(f.db.Meta("active_policy")==RecordId(next)&&f.db.Meta("policy_epoch")=="2","valid epoch2 policy not installed below cap");
        Check(f.db.VerifyJournal(),"below-cap journal invalid");out.pushKV("revocation_id",RecordId(revocation));out.pushKV("epoch2_id",RecordId(next));out.pushKV("final_objects",Count(f.db));Observe("below_cap",out);
    });

 h.Test("full-cap-policy-progress",[]{Fixture f;Fill(f);auto next=NextPolicy(f);InstallPolicy(f.db,next,f.now);Check(Count(f.db)==16385&&f.db.Meta("policy_epoch")=="2"&&f.db.Meta("active_policy")==RecordId(next),"policy not durably installed");Check(f.db.VerifyJournal(),"policy journal invalid");f.connection.reset();Database reopened(f.root);Check(Policy::Load(reopened,f.now).epoch==2&&Count(reopened)==16385&&reopened.VerifyJournal(),"policy not retained across reopen");});
 h.Test("full-cap-revocation-negative-evidence-tail-reopen",[]{
  Fixture f;auto failed=f.db.Get(f.evaluations[0])["body"];failed.pushKV("outcome","FAIL");f.Import(Signed("evaluation",failed,f.alice));
  f.now+=60001;const auto denied=f.MakeEvidence(f.composition);Reject([&]{AdmitCapsule(f.db,f.policy,denied,f.now);},"SEC_NEGATIVE_EVIDENCE");
  f.composition=f.MakeComposition("unaffected");f.capsule=f.MakeEvidence(f.composition);Broker broker(f.db,std::string(64,'e'));auto grant=f.Grant(20);auto permit=broker.Prepare(grant,f.Context(),f.ReadRequest(),f.now);Fill(f);
  auto rev=Rev(f,grant);ImportRecord(f.db,f.policy,rev,f.now);Check(f.db.Revoked(grant,f.now)&&f.db.Has(RecordId(rev))&&Count(f.db)==16385,"revocation did not commit");Check(Phase(f.db,permit)=="revoked"&&!broker.CanRelease(grant,f.Context(),f.ReadRequest(),f.now),"revocation ineffective");
  Reject([&]{AdmitCapsule(f.db,f.policy,denied,f.now);},"SEC_NEGATIVE_EVIDENCE");
  auto ob=f.Challenge(f.composition,"outcome")["body"];ob.pushKV("suite",Hash("new ordinary suite"));auto ordinary=Signed("challenge",ob,f.owner);Check(!f.db.Has(RecordId(ordinary)),"ordinary refusal probe is a duplicate");StableReject(f.db,[&]{ImportRecord(f.db,f.policy,ordinary,f.now);},"SEC_OBJECT_QUOTA");
  for(uint64_t i=1;i<128;++i){auto r=Rev(f,Hash("subject"+std::to_string(i)));ImportRecord(f.db,f.policy,r,f.now,true);}
  Check(Count(f.db)==16512,"tail count before reopen wrong");Check(f.db.VerifyJournal(),"journal before reopen invalid");
  f.connection.reset();Database reopened(f.root);auto policy=Policy::Load(reopened,f.now);Check(Count(reopened)==16512&&reopened.Revoked(grant,f.now),"reopen lost tail or revocation");
  Database a(f.root),b(f.root);auto r1=Rev(f,Hash("race one")),r2=Rev(f,Hash("race two"));std::atomic<bool> go{false};std::atomic<int> success{0},refused{0};std::string errors[2];
  auto attempt=[&](Database& db,const Json& r,int index){while(!go.load())std::this_thread::yield();try{ImportRecord(db,policy,r,f.now);++success;}catch(const Error& e){if(e.code=="SEC_CONTROL_QUOTA")++refused;else errors[index]=e.code;}};
  std::thread t1(attempt,std::ref(a),std::cref(r1),0),t2(attempt,std::ref(b),std::cref(r2),1);go=true;t1.join();t2.join();Check(errors[0].empty()&&errors[1].empty()&&success==1&&refused==1&&Count(reopened)==16513,"last-slot race violated fixed bound");
  auto over=Rev(f,Hash("overflow subject"));StableReject(reopened,[&]{ImportRecord(reopened,policy,over,f.now);},"SEC_CONTROL_QUOTA");
  auto next=NextPolicy(f);StableReject(reopened,[&]{InstallPolicy(reopened,next,f.now);},"SEC_CONTROL_QUOTA");
  auto merged=rev;for(int i=0;i<14;++i){auto key=GenerateKey();AddSignature(merged,key);}ImportRecord(reopened,policy,merged,f.now);Check(reopened.Get(RecordId(rev))["signatures"].size()==16,"duplicate signature union lost");
  auto extra=rev;auto extra_key=GenerateKey();AddSignature(extra,extra_key);StableReject(reopened,[&]{ImportRecord(reopened,policy,extra,f.now);},"SEC_SIGNATURE_LIMIT");
  {Database::Transaction tx(reopened);reopened.Put(rev,"public");tx.Commit();}Check(reopened.Query("SELECT visibility FROM objects WHERE id=?",{RecordId(rev)})[0][0]=="private","public duplicate exposed private record");
  Check(Count(reopened)==16513,"duplicate consumed reserve");Check(reopened.VerifyJournal(),"journal after duplicate invalid");
  Reject([&]{AdmitCapsule(reopened,policy,denied,f.now);},"SEC_NEGATIVE_EVIDENCE");
  Broker re(reopened,std::string(64,'f'));Check(!re.CanRelease(grant,f.Context(),f.ReadRequest(),f.now),"reopen revived revoked grant");re.Pause(f.now);Check(reopened.Meta("paused")=="1","pause failed at exhausted tail");
  auto proof=Object();proof.pushKV("total",Count(reopened));proof.pushKV("journal_valid",reopened.VerifyJournal());proof.pushKV("tail_slots",129);Observe("tail_proof",proof);
 });
 h.Test("full-cap-invalid-authority-and-late-write-rollback",[]{
  Fixture f;Fill(f);auto valid=Rev(f,Hash("reject subject"));
  auto bad=Envelope("revocation",valid["body"]);AddSignature(bad,f.publisher);StableReject(f.db,[&]{ImportRecord(f.db,f.policy,bad,f.now);},"SEC_SIGNATURE_THRESHOLD");
  auto stale=Rev(f,Hash("stale"),1,2);StableReject(f.db,[&]{ImportRecord(f.db,f.policy,stale,f.now);},"SEC_POLICY_BINDING");
  auto expired=valid["body"];expired.pushKV("issued_ms",f.now-70000);expired.pushKV("expires_ms",f.now-1);auto e=Signed("revocation",expired,f.owner,&f.second);StableReject(f.db,[&]{ImportRecord(f.db,f.policy,e,f.now);},"SEC_EXPIRED_OR_FUTURE");
  auto next=NextPolicy(f);auto wrong=Signed("policy",next["body"],f.publisher);StableReject(f.db,[&]{InstallPolicy(f.db,wrong,f.now);},"SEC_ROOT_SIGNATURES");
  f.db.Exec("CREATE TEMP TRIGGER reject_emergency_event BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT,'test-only late-write failure'); END");auto before=Canonical(Snapshot(f.db));
  // Baseline fails at object quota; candidate reaches the injected journal failure.
  try{ImportRecord(f.db,f.policy,valid,f.now);throw std::runtime_error("late failure did not fire");}catch(const Error& err){Check(err.code=="SEC_OBJECT_QUOTA"||err.code=="SEC_DATABASE_WRITE","unexpected injected failure");auto observation=Object();observation.pushKV("error",err.code);Observe("late_write",observation);}
  Check(Canonical(Snapshot(f.db))==before&&!f.db.Revoked(Hash("reject subject"),f.now)&&!f.db.Has(RecordId(valid)),"late failure partially committed");
  auto prior=Canonical(Snapshot(f.db));try{InstallPolicy(f.db,next,f.now);throw std::runtime_error("late policy failure did not fire");}catch(const Error& err){Check(err.code=="SEC_OBJECT_QUOTA"||err.code=="SEC_DATABASE_WRITE","unexpected late policy failure");auto o=Object();o.pushKV("error",err.code);Observe("late_policy_write",o);}Check(Canonical(Snapshot(f.db))==prior,"late policy failure partially committed");
  f.db.Exec("DROP TRIGGER reject_emergency_event");
 });
 auto result=Object();result.pushKV("passed",static_cast<uint64_t>(h.passed));result.pushKV("failed",static_cast<uint64_t>(h.failed));result.pushKV("tests",h.results);result.pushKV("observations",observations);
 if(argc>1){EnsurePrivateDirectory(fs::path(argv[1]).parent_path());WritePrivate(argv[1],Canonical(result),true);}
 std::cout<<Canonical(result)<<'\n';return h.failed?1:0;
}
