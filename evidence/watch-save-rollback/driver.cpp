#include <bitcoin-build-config.h>
#include <modelnet/model_watch.h>
#include <test/util/setup_common.h>
#include <boost/test/unit_test.hpp>
#include <fstream>
#include <iterator>
modelnet::ModelEvent MakeSigned(const std::string& publisher, const std::string& oid,
                                 modelnet::ModelEventType t = modelnet::ModelEventType::MODEL_PUBLISHED)
{
    modelnet::ModelEvent e;
    e.event_type = t;
    e.object_id = oid;
    e.model_id = oid;
    e.publisher_id = publisher;
    e.verification_state = "SIGNED_OK";
    e.source = "SEARCH";
    e.record_sequence = 1;
    e.match.family = "qwen";
    e.match.architecture = "transformer";
    e.match.display_name = "Qwen";
    e.match.canonical_name = "Qwen";
    e.match.tags = {"gguf"};
    return e;
}


BOOST_FIXTURE_TEST_SUITE(watch_put_rollback, BasicTestingSetup)

static void CheckFailedWatchPut(const fs::path& dir, bool replacing)
{
    using namespace modelnet;
    fs::create_directories(dir);
    ModelWatchStore store(dir);
    std::string err;
    ModelWatch other;
    other.watch_id = "other";
    other.kind = WatchKind::PUBLISHER;
    other.publisher_id = "other-publisher";
    other.action = ActionPolicy::FREE_DOWNLOAD;
    BOOST_REQUIRE(store.PutWatch(other, err));
    ModelWatch target = other;
    target.watch_id = "target";
    target.publisher_id = "old-publisher";
    if (replacing) BOOST_REQUIRE(store.PutWatch(target, err));
    store.NoteEvent(MakeSigned("other-publisher", "queued-other"));
    if (replacing) store.NoteEvent(MakeSigned("old-publisher", "queued-target"));
    const auto actions_json = [](const ModelWatchStore& s) {
        UniValue a(UniValue::VARR);
        for (const auto& item : s.PeekActions()) a.push_back(WatchActionToJson(item));
        return a.write();
    };
    const std::string queued = actions_json(store);
    const auto disk = [&]() {
        std::ifstream in(dir / "watches.json");
        return std::string(std::istreambuf_iterator<char>(in), {});
    };
    const std::string saved = disk();
    target.publisher_id = "new-publisher";
    fs::create_directory(dir / "watches.json.tmp");
    BOOST_CHECK(!store.PutWatch(target, err));
    BOOST_CHECK(!err.empty());
    BOOST_CHECK_EQUAL(disk(), saved);
    ModelWatch got;
    const bool found = store.GetWatch(target.watch_id, got);
    BOOST_CHECK_EQUAL(found, replacing);
    if (replacing && found) BOOST_CHECK_EQUAL(got.publisher_id, "old-publisher");
    BOOST_CHECK_EQUAL(actions_json(store), queued);
    store.DrainActions();
    store.NoteEvent(MakeSigned("new-publisher", "after-failure-new"));
    store.NoteEvent(MakeSigned("old-publisher", "after-failure-old"));
    store.NoteEvent(MakeSigned("other-publisher", "after-failure-other"));
    unsigned old_count = 0, new_count = 0, other_count = 0;
    for (const auto& a : store.DrainActions()) {
        BOOST_CHECK(!a.spends);
        if (a.publisher_id == "new-publisher") ++new_count;
        if (a.publisher_id == "old-publisher") ++old_count;
        if (a.publisher_id == "other-publisher") ++other_count;
    }
    BOOST_CHECK_EQUAL(new_count, 0U);
    BOOST_CHECK_EQUAL(old_count, replacing ? 1U : 0U);
    BOOST_CHECK_EQUAL(other_count, 1U);
    {
        ModelWatchStore reopened(dir);
        BOOST_CHECK_EQUAL(reopened.GetWatch(target.watch_id, got), replacing);
        if (replacing) BOOST_CHECK_EQUAL(got.publisher_id, "old-publisher");
        BOOST_REQUIRE(reopened.GetWatch(other.watch_id, got));
    }
    fs::remove(dir / "watches.json.tmp");
    store.NoteEvent(MakeSigned("other-publisher", "before-retry"));
    const std::string queued_retry = actions_json(store);
    err.clear();
    BOOST_REQUIRE(store.PutWatch(target, err));
    BOOST_CHECK_EQUAL(actions_json(store), queued_retry);
    store.DrainActions();
    store.NoteEvent(MakeSigned("new-publisher", "after-retry-new"));
    store.NoteEvent(MakeSigned("old-publisher", "after-retry-old"));
    const auto retry = store.DrainActions();
    BOOST_REQUIRE_EQUAL(retry.size(), 1U);
    BOOST_CHECK_EQUAL(retry[0].publisher_id, "new-publisher");
    BOOST_CHECK(!retry[0].spends);
    ModelWatchStore reopened(dir);
    BOOST_REQUIRE(reopened.GetWatch(target.watch_id, got));
    BOOST_CHECK_EQUAL(got.publisher_id, "new-publisher");
    BOOST_REQUIRE(reopened.GetWatch(other.watch_id, got));
}

BOOST_AUTO_TEST_CASE(failed_watch_creation_preserves_live_state_actions_and_retry)
{
    CheckFailedWatchPut(m_path_root / "failed-watch-create", false);
}

BOOST_AUTO_TEST_CASE(failed_watch_replacement_preserves_live_state_actions_and_retry)
{
    CheckFailedWatchPut(m_path_root / "failed-watch-replace", true);
}

BOOST_AUTO_TEST_SUITE_END()
