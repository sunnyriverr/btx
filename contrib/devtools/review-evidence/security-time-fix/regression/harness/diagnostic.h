// Investigation-only tracing and bounded scheduling controls; not a product fix.
#pragma once
#include <modelnet/security_v2/database.h>
namespace modelnet::security::diagnostic {
void Task(const std::string& id,const std::string& challenge);
void BeforePerform();
void Captured(int64_t now);
void Stage(Database& db,const std::string& stage,int64_t supplied=0,const std::string& error={});
void Clock(int64_t supplied,uint64_t persisted,bool accepted);
void ImportBegin(Database& db,const std::string& kind,int64_t now);
void ImportCommitted(Database& db,const std::string& kind,int64_t now);
void BeforeReport(Database& db,int64_t now);
void EvaluationCommitted(Database& db);
void BeforePersist(Database& db,const Json& record,int64_t supplied);
bool AwaitHeld();
void ReleaseHeld();
std::string LastError();
void Caught(Database& db);
void WorkerError(const fs::path& root,const std::string& error);
void Cancel();
Json Snapshot(Database& db);
void BeforeStop(Database& db) noexcept;
void Save(Database& db) noexcept;
}
