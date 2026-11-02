// Investigation-only code. No clock, authorization or database mutation.
#include <modelnet/security_v2/diagnostic.h>
#include <modelnet/security_v2/evaluation.h>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdio>
#include <cstdlib>
#include <exception>
#include <functional>
#include <mutex>
#include <sstream>
#include <thread>
namespace modelnet::security::diagnostic {
namespace {
struct Context {std::string task,challenge,stage,failure_stage,failure_error;int64_t captured=0,supplied=0,failure_supplied=0;unsigned ordinal=0;};
thread_local Context context;
std::mutex output_mutex,gate_mutex;
std::condition_variable gate_condition;
std::atomic<unsigned> ordinal{0};
uint64_t sequence=0;
bool held=false,advanced=false,released=false,cancelled=false,timed_out=false;
std::string last_error;
std::string first,second;
int64_t held_time=0;
const std::string mode=[] {const char* p=std::getenv("BTX_DIAG_MODE");return std::string(p?p:"natural");}();
uint64_t Steady(){return std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
void Emit(Json row) noexcept {
    try {row.pushKV("mode",mode);row.pushKV("task",context.task);row.pushKV("challenge",context.challenge);
        row.pushKV("stage",context.stage);row.pushKV("perform_captured_ms",context.captured);
        row.pushKV("stage_supplied_ms",context.supplied);row.pushKV("wall_ms",NowMs());row.pushKV("steady_us",Steady());
        std::ostringstream thread;thread<<std::this_thread::get_id();row.pushKV("thread",thread.str());
        std::lock_guard lock(output_mutex);row.pushKV("sequence",++sequence);
        std::fprintf(stderr,"DIAG %s\n",Canonical(row).c_str());std::fflush(stderr);
    }catch(...){std::fprintf(stderr,"DIAG_TRACE_FAILURE\n");}
}
Json Event(const char* kind){auto x=Object();x.pushKV("event",kind);return x;}
bool Wait(std::unique_lock<std::mutex>& lock,const std::function<bool()>& ready){
    const bool ok=gate_condition.wait_for(lock,std::chrono::seconds(3),[&]{return cancelled||ready();});
    if(!ok){timed_out=true;cancelled=true;gate_condition.notify_all();}return ok&&!cancelled;
}
}
void Task(const std::string& id,const std::string& challenge){context={};context.task=id;context.challenge=challenge;context.ordinal=++ordinal;Emit(Event("task-selected"));}
void BeforePerform(){
    context.stage="before-perform-time";
    if(mode=="controlled"&&context.ordinal==2){
        int64_t after=0;{
            std::unique_lock lock(gate_mutex);second=context.challenge;
            if(Wait(lock,[]{return held;}))after=held_time;
        }
        if(after){const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(3);
            while(NowMs()<=after){
                {std::lock_guard lock(gate_mutex);if(cancelled)break;if(std::chrono::steady_clock::now()>=deadline){timed_out=true;cancelled=true;gate_condition.notify_all();break;}}
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
            }
        }
        Emit(Event("second-released-before-capture"));
    }
}
void Captured(int64_t now){context.captured=now;context.supplied=now;Emit(Event("perform-time-captured"));}
void Stage(Database& db,const std::string& stage,int64_t supplied,const std::string& error){
    context.stage=stage;context.supplied=supplied;auto x=Event("stage");x.pushKV("error",error);
    x.pushKV("persisted_clock",db.Meta("clock","0"));x.pushKV("runtime_available",db.Meta("runtime_available"));x.pushKV("paused",db.Meta("paused","0"));auto rows=Array();
    if(!context.challenge.empty())for(const auto& r:db.Query("SELECT evaluator,phase,report FROM evaluation_runs WHERE challenge=?",{context.challenge})){
        auto a=Object();a.pushKV("evaluator",r[0]);a.pushKV("phase",r[1]);a.pushKV("report",r[2]);rows.push_back(a);
    }
    x.pushKV("evaluation_rows",rows);x.pushKV("failure_stage",context.failure_stage);x.pushKV("failure_error",context.failure_error);x.pushKV("failure_supplied_ms",context.failure_supplied);Emit(x);
}
void Clock(int64_t supplied,uint64_t persisted,bool accepted){auto x=Event("clock-check");x.pushKV("supplied_ms",supplied);x.pushKV("persisted_before_ms",persisted);x.pushKV("accepted",accepted);x.pushKV("error",accepted?"":"SEC_CLOCK_ROLLBACK");Emit(x);}
void ImportBegin(Database& db,const std::string& kind,int64_t now){Stage(db,"import:"+kind,now);}
void ImportCommitted(Database& db,const std::string& kind,int64_t now){Stage(db,"import-committed:"+kind,now);}
void BeforeReport(Database& db,int64_t now){
    Stage(db,"evaluation-report-before-import",now);
    if(context.ordinal!=1||mode=="record-expiry"||
       (mode!="controlled"&&mode!="challenge-expiry"&&mode!="pause"&&mode!="revoke"&&mode!="local-deny"))return;
    {std::lock_guard lock(gate_mutex);first=context.challenge;held_time=now;held=true;gate_condition.notify_all();}
    Stage(db,"first-report-held-outside-transaction",now);
    {std::unique_lock lock(gate_mutex);(void)Wait(lock,[]{return advanced||released;});}
    Stage(db,"first-report-released",now);
}
void EvaluationCommitted(Database& db){
    Stage(db,"evaluation-row-committed");
    if(mode=="controlled"&&context.ordinal==2){std::lock_guard lock(gate_mutex);advanced=true;gate_condition.notify_all();}
}
void BeforePersist(Database& db,const Json& record,int64_t supplied){
    if(mode!="record-expiry"||Text(record,"kind")!="evaluation"||context.ordinal!=1)return;
    Stage(db,"record-expiry-held-after-validation",supplied);
    {std::lock_guard lock(gate_mutex);first=context.challenge;held_time=static_cast<int64_t>(UInt(record["body"],"expires_ms",INT64_MAX));held=true;gate_condition.notify_all();}
    {std::unique_lock lock(gate_mutex);(void)Wait(lock,[]{return released;});}
    Stage(db,"record-expiry-released-before-final-sample",supplied);
}
bool AwaitHeld(){std::unique_lock lock(gate_mutex);return Wait(lock,[]{return held;});}
void ReleaseHeld(){std::lock_guard lock(gate_mutex);released=true;gate_condition.notify_all();}
std::string LastError(){std::lock_guard lock(gate_mutex);return last_error;}
void Cancel(){std::lock_guard lock(gate_mutex);cancelled=true;gate_condition.notify_all();}
void Caught(Database& db){
    context.failure_stage=context.stage;context.failure_supplied=context.supplied;
    try {std::rethrow_exception(std::current_exception());}catch(const Error& e){context.failure_error=e.code;}catch(const std::exception& e){context.failure_error=e.what();}catch(...){context.failure_error="non-standard-exception";}
    Stage(db,"evaluation-catch-before-blocked-update",context.supplied,context.failure_error);
}
void WorkerError(const fs::path& root,const std::string& error){
    {std::lock_guard lock(gate_mutex);last_error=error;}
    const auto failed_stage=context.stage;try {Database db(root);Stage(db,"worker-error-after:"+failed_stage,context.supplied,error);}catch(...){auto x=Event("worker-error-snapshot-failed");x.pushKV("error",error);Emit(x);}Cancel();
}
Json Snapshot(Database& db){
    auto out=Object();out.pushKV("mode",mode);out.pushKV("wall_ms",NowMs());out.pushKV("steady_us",Steady());out.pushKV("clock",db.Meta("clock","0"));
    out.pushKV("paused",db.Meta("paused","0"));out.pushKV("active_policy",db.Meta("active_policy"));out.pushKV("runtime_available",db.Meta("runtime_available"));
    const auto local=ReadLocalConfig(db);out.pushKV("execution_policy",local["execution_policy"]);out.pushKV("mesh_configured",local["continuous_security"].isObject());out.pushKV("remote_work_configured",local["remote_work"].isObject());
    auto runs=Array();for(const auto& r:db.Query("SELECT challenge,evaluator,phase,report,lease_until FROM evaluation_runs ORDER BY challenge")){
        auto a=Object();a.pushKV("challenge",r[0]);a.pushKV("evaluator",r[1]);a.pushKV("phase",r[2]);a.pushKV("report",r[3]);a.pushKV("lease_until",r[4]);runs.push_back(a);
    }out.pushKV("evaluation_runs",runs);
    auto records=Array();for(const auto& r:db.Query("SELECT envelope FROM objects WHERE kind IN ('challenge','receipt','evaluation') ORDER BY kind,id"))records.push_back(Parse(r[0]));out.pushKV("records",records);
    auto events=Array();for(const auto& r:db.Query("SELECT seq,kind,subject FROM events ORDER BY seq")){auto a=Object();a.pushKV("seq",r[0]);a.pushKV("kind",r[1]);a.pushKV("subject",r[2]);events.push_back(a);}out.pushKV("events",events);
    {std::lock_guard lock(gate_mutex);out.pushKV("first_challenge",first);out.pushKV("second_challenge",second);out.pushKV("held_report_ms",held_time);out.pushKV("second_committed",advanced);out.pushKV("barrier_timed_out",timed_out);}return out;
}
void BeforeStop(Database& db) noexcept {try {Stage(db,"service-stop-boundary");const char* p=std::getenv("BTX_DIAG_SNAPSHOT");if(p)WritePrivate(NativePath(std::string(p)+".prestop.json"),Canonical(Snapshot(db))+"\n",true);}catch(const std::exception& e){std::fprintf(stderr,"DIAG_PRESTOP_FAILURE %s\n",e.what());}}
void Save(Database& db) noexcept {try {const char* p=std::getenv("BTX_DIAG_SNAPSHOT");if(p)WritePrivate(NativePath(p),Canonical(Snapshot(db))+"\n",true);}catch(const std::exception& e){std::fprintf(stderr,"DIAG_SNAPSHOT_FAILURE %s\n",e.what());}}
}
