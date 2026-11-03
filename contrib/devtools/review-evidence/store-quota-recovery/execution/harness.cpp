// Copyright (c) 2026 The BTX developers. MIT license.
// All identities, credentials and model tensors below are synthetic fixtures.
// Two signer identities on this test host do NOT qualify two physical hosts.
#include <modelnet/security_v2/lifecycle.h>
#include <modelnet/security_v2/broker.h>
#include <modelnet/security_v2/mesh.h>
#include <modelnet/security_v2/work.h>
#include <tuple>
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
    for(const auto& table:db.Query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")){
        const auto& name=table[0];std::string order;
        for(const auto& col:db.Query("PRAGMA table_info(\""+name+"\")")){if(!order.empty())order+=",";order+="\""+col[1]+"\"";}
        auto rows=db.Query("SELECT * FROM \""+name+"\" ORDER BY "+order);std::string bytes;
        for(const auto& row:rows)for(const auto& col:row)bytes+=std::to_string(col.size())+":"+col;
        auto state=Object();state.pushKV("rows",static_cast<uint64_t>(rows.size()));state.pushKV("sha384",Hash(bytes));out.pushKV(name,state);
    }
    return out;
}
Json Read(Broker& broker,Fixture& f,const std::string& grant){
    auto p=broker.Prepare(grant,f.Context(),f.ReadRequest(),f.now);
    auto r=broker.Execute(Text(p,"secret"),f.Context(),f.ReadRequest(),f.now);
    Check(Boolean(r,"ok")&&Boolean(r,"dispatched"),"harmless broker read did not dispatch");
    Check(Text(r,"output_digest")==Hash("hello safe workspace\n"),"wrong harmless read digest");
    return r;
}
Json Refuse(const char* name,const std::function<void()>& operation,std::string_view expected){
    try{operation();}catch(const Error& e){
        Check(e.code==expected,"unexpected refusal code");auto row=Object();row.pushKV("error",e.code);Observe(name,row);return row;
    }
    throw std::runtime_error("expected refusal");
}
}
int main(int argc,char** argv){
    Harness h;
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
    h.Test("default-16384-object-cap-pause-reopen-direct-resume",[]{
        Fixture f;const std::string boot(64,'b');Broker b(f.db,boot);auto grant=f.Grant(20);
        Observe("cap_fixture_below_cap_read",Read(b,f,grant));
        auto prepared=b.Prepare(grant,f.Context(),f.ReadRequest(),f.now);
        auto executing=b.Prepare(grant,f.Context(),f.ReadRequest(),f.now);
        // Fixture-only durable executing row. No worker is launched or cancelled.
        f.db.Exec("UPDATE permits SET phase='executing' WHERE id=?",{Text(executing,"permit")});
        Check(Phase(f.db,prepared)=="prepared"&&Phase(f.db,executing)=="executing","permit phase setup failed");
        const auto initial=Count(f.db);
        std::string first_filler,last_filler;
        {
            Database::Transaction tx(f.db);
            // Inert unsigned fixtures enter only via Database::Put, never ImportRecord.
            // They are not authority/evidence, never dereferenced by the signed controls.
            for(uint64_t i=initial;i<16384;++i){auto body=Object();body.pushKV("fixture_only_unsigned_count",i);auto id=f.db.Put(Envelope("control",body));if(first_filler.empty())first_filler=id;last_filler=id;}
            tx.Commit();
        }
        Check(Count(f.db)==16384,"actual default object cap not reached");
        auto fill=Object();fill.pushKV("initial_objects",initial);fill.pushKV("filler_objects",16384-initial);fill.pushKV("actual_objects",Count(f.db));fill.pushKV("first_filler",first_filler);fill.pushKV("last_filler",last_filler);Observe("count_construction",fill);
        Check(b.CanRelease(grant,f.Context(),f.ReadRequest(),f.now),"valid current authority broken before cap controls");
        auto revocation=f.Revocation(grant),next=NextPolicy(f);signed_records.push_back(revocation);signed_records.push_back(next);
        auto before=Snapshot(f.db);Observe("before_quota_failures",before);
        Refuse("at_cap_revocation",[&]{ImportRecord(f.db,Policy::Load(f.db,f.now),revocation,f.now);},"SEC_OBJECT_QUOTA");
        Check(Canonical(Snapshot(f.db))==Canonical(before),"failed revocation changed persistent state");
        Refuse("at_cap_epoch2",[&]{InstallPolicy(f.db,next,f.now);},"SEC_OBJECT_QUOTA");
        auto after=Snapshot(f.db);Observe("after_quota_failures",after);
        Check(Canonical(after)==Canonical(before),"failed policy changed persistent state");
        Check(!f.db.Has(RecordId(revocation))&&!f.db.Revoked(grant,f.now)&&!f.db.Has(RecordId(next)),"failed authority partly installed");
        b.Pause(f.now);
        Check(f.db.Meta("paused")=="1"&&Count(f.db)==16384,"pause failed at exact cap");
        Check(Phase(f.db,prepared)=="revoked"&&Phase(f.db,executing)=="revoked","pause failed to revoke both durable phases");
        Check(!b.CanRelease(grant,f.Context(),f.ReadRequest(),f.now),"paused grant can release");
        Refuse("paused_prepare",[&]{b.Prepare(grant,f.Context(),f.ReadRequest(),f.now);},"SEC_GRANT_REVOKED_OR_PAUSED");
        Check(f.db.VerifyJournal(),"paused journal invalid");Observe("paused_state",Snapshot(f.db));
        // Close the original Database connection, then open the same persisted store.
        // Broker b is never used again; this is not Service/guard restart.
        f.connection.reset();
        {Database reopened(f.root);Broker re(reopened,boot);
            Check(reopened.Meta("paused")=="1"&&Count(reopened)==16384,"reopen lost full-store pause");
            Check(Phase(reopened,prepared)=="revoked"&&Phase(reopened,executing)=="revoked","reopen lost permit invalidation");
            Check(!re.CanRelease(grant,f.Context(),f.ReadRequest(),f.now),"reopened pause ineffective");
            auto resume=Control(f);signed_records.push_back(resume);const auto resume_id=RecordId(resume);
            Check(!reopened.Has(resume_id),"resume was imported before direct call");re.Resume(resume,f.now);
            Check(reopened.Meta("paused")=="0"&&Count(reopened)==16384&&!reopened.Has(resume_id),"direct resume inserted an object or did not commit");
            Check(reopened.Query("SELECT id FROM consumed_controls WHERE id=?",{resume_id}).size()==1,"resume replay state not persisted");
            Check(re.CanRelease(grant,f.Context(),f.ReadRequest(),f.now),"valid current authority not restored after resume");
            Refuse("resume_replay",[&]{re.Resume(resume,f.now);},"SEC_RESUME_REPLAY");
            Refuse("old_prepared_secret",[&]{re.Execute(Text(prepared,"secret"),f.Context(),f.ReadRequest(),f.now);},"SEC_PERMIT_REPLAY");
            Refuse("old_executing_secret",[&]{re.Execute(Text(executing,"secret"),f.Context(),f.ReadRequest(),f.now);},"SEC_PERMIT_REPLAY");
            Observe("resumed_real_read",Read(re,f,grant));
            Refuse("capacity_still_full",[&]{InstallPolicy(reopened,next,f.now);},"SEC_OBJECT_QUOTA");
            Check(Count(reopened)==16384&&reopened.Meta("policy_epoch")=="1"&&reopened.VerifyJournal(),"final cap/state/journal changed");
            Observe("final_state",Snapshot(reopened));auto proof=Object();proof.pushKV("resume_id",resume_id);proof.pushKV("active_policy",reopened.Meta("active_policy"));proof.pushKV("revocation_id",RecordId(revocation));proof.pushKV("epoch2_id",RecordId(next));proof.pushKV("objects",Count(reopened));proof.pushKV("journal_valid",reopened.VerifyJournal());proof.pushKV("can_release_after_resume",re.CanRelease(grant,f.Context(),f.ReadRequest(),f.now));Observe("final_proof",proof);
        }
    });
    auto result=Object();result.pushKV("passed",static_cast<uint64_t>(h.passed));result.pushKV("failed",static_cast<uint64_t>(h.failed));result.pushKV("tests",h.results);result.pushKV("observations",observations);
    if(argc>1){EnsurePrivateDirectory(fs::path(argv[1]).parent_path());WritePrivate(argv[1],Canonical(result),true);std::string records;for(const auto& e:signed_records.getValues())records+=Canonical(e)+"\n";WritePrivate(std::string(argv[1])+".records.jsonl",records,true);}
    std::cout<<Canonical(result)<<'\n';return h.failed?1:0;
}
