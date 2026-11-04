#include <modelnet/bounty.h>
#include <util/fs.h>
#include <fstream>
#include <iostream>
#include <iterator>
#include <cerrno>
#ifndef _WIN32
#include <sys/wait.h>
#endif

static int checks=0, failures=0;
static void check(bool ok, const char* label) {
    ++checks; if (!ok) ++failures;
    std::cout << (ok ? "PASS " : "FAIL ") << label << std::endl;
}
int main(int argc, char** argv) {
    if(argc!=2) return 2;
    const auto root=fs::PathFromString(argv[1]);
    if(!fs::is_directory(root) || !fs::is_empty(root)) return 2;
    const auto artifact=root/"artifact.txt";
    {std::ofstream f(artifact,std::ios::binary); f << "abc";}
    const std::string digest="cb00753f45a35e8bb5a03d699ac65007272c32ab0eded1631a8b605a43ff5bed8086072ba1e7cc2358baeca134c825a7";
    UniValue file(UniValue::VOBJ), files(UniValue::VARR), spec(UniValue::VOBJ), submission(UniValue::VOBJ), resources(UniValue::VOBJ), plan;
    file.pushKV("name","artifact.txt"); file.pushKV("sha384",digest); file.pushKV("max_bytes",3); files.push_back(file);
    spec.pushKV("profile_id","EXACT_CHECKS"); spec.pushKV("required_files",files);
    submission.pushKV("artifact_dir",fs::PathToString(root));
    resources.pushKV("timeout_ms",15000); resources.pushKV("memory_bytes",268435456);
    std::string err;
    check(modelnet::EvaluationProfileReady("EXACT_CHECKS"),"existing profile available");
    check(modelnet::PrepareEvaluation(spec,submission,resources,plan,err),"valid owned artifact prepared");
    check(!plan["wallet"].get_bool() && !plan["network"].get_bool(),"preparation permissions unchanged");
    check(plan["timeout_ms"].getInt<int64_t>()==15000 && plan["memory_bytes"].getInt<int64_t>()==268435456,"preparation limits unchanged");
    auto make_job=[&](const UniValue& p) { UniValue j(UniValue::VOBJ); j.pushKV("plan",p);j.pushKV("state","RUNNING");j.pushKV("sentinel","owned-component-job");return j;};
    UniValue absent(UniValue::VOBJ);
    check(!modelnet::RunEvaluationJob(absent,err) && err=="plan","common missing plan guard");
    auto uninstalled=plan;uninstalled.pushKV("profile_id","NOT_INSTALLED");auto uninstalled_job=make_job(uninstalled);
    check(!modelnet::RunEvaluationJob(uninstalled_job,err) && err=="unexecuted profile","common uninstalled profile guard");
    auto job=make_job(plan);
#ifdef _WIN32
    check(!modelnet::RunEvaluationJob(job,err),"Windows unavailable executor refuses");
    check(err=="isolated evaluation process is not supported on this platform","Windows explicit unsupported error");
    check(job["state"].get_str()=="FAILED","Windows caller-shaped job terminal FAILED");
    check(!job.exists("pid") && !job.exists("report") && !job.exists("pass") && !job.exists("isolated_process"),"Windows no process or success claim");
#else
    check(modelnet::RunEvaluationJob(job,err),"POSIX valid evaluation executed");
    check(job["state"].get_str()=="COMPLETE" && job["pass"].get_bool(),"POSIX valid file passes");
    check(job["report"]["tasks"][0]["sha384"].get_str()==digest && job["report"]["tasks"][0]["size"].getInt<int64_t>()==3,"POSIX real digest and size");
    check(job["isolated_process"].get_bool() && !job["wallet"].get_bool(),"POSIX isolation and wallet restriction");
    auto reaped=[&](const UniValue& j) {int status=0;errno=0;check(waitpid(static_cast<pid_t>(j["pid"].getInt<int64_t>()),&status,WNOHANG)==-1 && errno==ECHILD,"POSIX owned child already reaped");};
    reaped(job);
    auto cancelled=make_job(plan);cancelled.pushKV("cancel",true);
    check(!modelnet::RunEvaluationJob(cancelled,err) && err=="cancelled" && cancelled["state"].get_str()=="CANCELLED","POSIX pre-cancelled job remains cancelled");reaped(cancelled);
    auto check_file_failure=[&](const std::string& name,const std::string& hash,const char* label){
        auto changed=file;changed.pushKV("name",name);changed.pushKV("sha384",hash);UniValue list(UniValue::VARR);list.push_back(changed);
        auto s=spec;s.pushKV("required_files",list);UniValue p;
        check(modelnet::PrepareEvaluation(s,submission,resources,p,err),"POSIX failure control prepares");auto j=make_job(p);
        check(modelnet::RunEvaluationJob(j,err) && j["state"].get_str()=="FAILED" && !j["pass"].get_bool(),label);reaped(j);
    };
    check_file_failure("missing.txt",digest,"POSIX missing required file stays failed");
    check_file_failure("artifact.txt",std::string(96,'0'),"POSIX checksum mismatch stays failed");
#endif
    check(job["plan"].write()==plan.write() && job["sentinel"].get_str()=="owned-component-job","job plan and sentinel unchanged");
    UniValue logical(UniValue::VOBJ);logical.pushKV("pid",1);err="prior";
    check(modelnet::CancelEvaluationJob(logical,err) && logical["cancel"].get_bool() && logical["state"].get_str()=="CANCELLED" && err.empty(),"logical cancellation remains available");
    {std::ifstream f(artifact,std::ios::binary);std::string content((std::istreambuf_iterator<char>(f)),{});check(content=="abc","owned input unchanged");}
    check(std::distance(fs::directory_iterator(root),fs::directory_iterator())==1,"no extra artifact files");
    fs::remove(artifact);check(fs::is_empty(root),"owned artifacts cleaned");
    std::cout << "RESULT checks=" << checks << " failures=" << failures << std::endl;
    return failures ? 1 : 0;
}
