#include <crypto/sha384.h>
#include <modelnet/file_stream.h>
#include <modelnet/store.h>
#include <modelnet/types.h>
#include <span.h>
#include <util/fs.h>
#include <iostream>
#include <stdexcept>
#include <vector>
#define BOOST_REQUIRE(x) do { if (!(x)) throw std::runtime_error(#x); } while (0)
#define BOOST_CHECK(x) BOOST_REQUIRE(x)
#define BOOST_CHECK_EQUAL(a,b) BOOST_REQUIRE((a)==(b))
#define BOOST_REQUIRE_MESSAGE(x,m) do { if (!(x)) throw std::runtime_error(std::string(#x)+": "+(m)); } while(0)
fs::path m_path_root;
modelnet::Digest48 DigestOf(const std::vector<unsigned char>& bytes) { modelnet::Digest48 d;CSHA384 h;if(!bytes.empty())h.Write(bytes.data(),bytes.size());h.Finalize(d.data.data());return d;}
fs::path Scratch(const fs::path& root,const std::string& name){auto p=root/name;fs::create_directories(p);return p;}
void job_cleanup_failure_preserves_valid_eof_checkpoint()
{
    using namespace modelnet;
    const std::vector<unsigned char> file(PIECE_SIZE, 0x35);
    Digest48 artifact{};
    artifact.data[0] = 0x83;
    const fs::path jobs = Scratch(m_path_root, "job-cleanup-jobs");
    ModelStore live(Scratch(m_path_root, "job-cleanup-live"), 64 << 20);
    ModelStore q(Scratch(m_path_root, "job-cleanup-q"), 64 << 20);
    std::string err;
    FileStreamHydration first(artifact, 0, file.size(), live, q);
    first.SetJobDir(jobs);
    first.SetExpectedSha384(DigestOf(file));
    BOOST_REQUIRE(first.Feed(Span<const unsigned char>{file.data(), file.size()}, err));
    FileStreamJobRecord rec;
    BOOST_REQUIRE(LoadFileStreamJob(jobs, artifact, 0, rec, err));

    // A nonempty directory at the job path makes removal fail on every platform.
    const fs::path job = FileStreamJobPath(jobs, artifact, 0);
    BOOST_REQUIRE(fs::remove(job));
    fs::create_directories(job / "blocker");
    BOOST_CHECK(!first.Finish(err));
    BOOST_CHECK_EQUAL(err, "failed to delete file stream job");
    BOOST_CHECK(!first.IntegrityFailed());
    BOOST_CHECK(live.HasPiece(artifact, 0, 0));
    BOOST_CHECK(q.HasPiece(artifact, 0, 0));

    // Reconstruct the saved EOF job after the cleanup obstruction is removed.
    fs::remove_all(job);
    BOOST_REQUIRE(SaveFileStreamJob(jobs, artifact, 0, rec, err));
    FileStreamHydration resumed(artifact, 0, file.size(), live, q);
    resumed.SetJobDir(jobs);
    BOOST_REQUIRE(resumed.ApplyRecord(rec, err));
    BOOST_REQUIRE_MESSAGE(resumed.Finish(err), err);
    BOOST_CHECK(resumed.IsAdvertisable());
    BOOST_CHECK(!fs::exists(job));
    BOOST_CHECK(!q.HasPiece(artifact, 0, 0));
    std::vector<unsigned char> stored;
    BOOST_REQUIRE(live.GetPiece(artifact, 0, 0, stored, err));
    BOOST_CHECK(stored == file);
}
void missing_eof_quarantine_does_not_advance_resume_cursor()
{
    using namespace modelnet;
    const std::vector<unsigned char> file(PIECE_SIZE + 123, 0x35);
    Digest48 artifact{};
    artifact.data[0] = 0x84;
    ModelStore live(Scratch(m_path_root, "missing-eof-live"), 64 << 20);
    ModelStore q(Scratch(m_path_root, "missing-eof-q"), 64 << 20);
    FileStreamJobRecord rec;
    rec.artifact = artifact;
    rec.file_index = 0;
    rec.expected_size = file.size();
    rec.next_piece = 2;
    rec.resume_offset = 2 * PIECE_SIZE;
    rec.have_sha = true;
    rec.expected_sha384 = DigestOf(file);
    std::string err;
    // One valid quarantine piece remains; the other was removed by old cleanup.
    FileStreamHydration partial(artifact, 0, file.size(), live, q);
    BOOST_REQUIRE(partial.Feed(Span<const unsigned char>{file.data(), PIECE_SIZE}, err));
    FileStreamHydration resumed(artifact, 0, file.size(), live, q);
    BOOST_CHECK(!resumed.ApplyRecord(rec, err));
    BOOST_CHECK_EQUAL(err, "file stream EOF checkpoint missing piece");
    BOOST_CHECK_EQUAL(resumed.Progress().next_piece, 0U);
    BOOST_CHECK_EQUAL(resumed.Progress().bytes_ingested, 0U);
    BOOST_CHECK(q.HasPiece(artifact, 0, 0));
    // A caller can start fresh without weakening the final digest check.
    resumed.SetExpectedSha384(DigestOf(file));
    BOOST_REQUIRE(resumed.Feed(Span<const unsigned char>{file.data(), file.size()}, err));
    BOOST_REQUIRE_MESSAGE(resumed.Finish(err), err);
    BOOST_CHECK(resumed.IsAdvertisable());
}
void short_final_checkpoint_survives_publication_quota_failure()
{
    using namespace modelnet;
    std::vector<unsigned char> file(PIECE_SIZE + 123, 0x35);
    Digest48 artifact{};
    artifact.data[0] = 0x71;
    const fs::path jobs = Scratch(m_path_root, "short-eof-jobs");
    ModelStore live(Scratch(m_path_root, "short-eof-live"), PIECE_SIZE);
    ModelStore q(Scratch(m_path_root, "short-eof-q"), 64 << 20);
    std::string err;
    FileStreamHydration first(artifact, 0, file.size(), live, q);
    first.SetJobDir(jobs);
    first.SetExpectedSha384(DigestOf(file));
    BOOST_REQUIRE(first.Feed(Span<const unsigned char>{file.data(), file.size()}, err));
    BOOST_CHECK(!first.Finish(err));
    BOOST_CHECK_EQUAL(err, "disk quota");
    BOOST_CHECK(!first.IntegrityFailed());
    FileStreamJobRecord rec;
    BOOST_REQUIRE(LoadFileStreamJob(jobs, artifact, 0, rec, err));
    BOOST_CHECK_EQUAL(rec.next_piece, 2U);
    live.SetQuotaBytes(64 << 20);
    FileStreamHydration resumed(artifact, 0, file.size(), live, q);
    resumed.SetJobDir(jobs);
    BOOST_REQUIRE(resumed.ApplyRecord(rec, err));
    BOOST_CHECK_EQUAL(resumed.Progress().bytes_ingested, file.size());
    BOOST_REQUIRE_MESSAGE(resumed.Finish(err), err);
    BOOST_CHECK(resumed.IsAdvertisable());
    BOOST_CHECK(!fs::exists(FileStreamJobPath(jobs, artifact, 0)));
}
void only_complete_file_integrity_mismatches_mark_rejection()
{
    using namespace modelnet;
    const std::vector<unsigned char> file(123, 0x12);
    for (const bool bad_root : {false, true}) {
        Digest48 artifact{};
        artifact.data[0] = bad_root ? 0x72 : 0x73;
        ModelStore live(Scratch(m_path_root, bad_root ? "root-live" : "hash-live"), 64 << 20);
        ModelStore q(Scratch(m_path_root, bad_root ? "root-q" : "hash-q"), 64 << 20);
        FileStreamHydration hyd(artifact, 0, file.size(), live, q);
        Digest48 expected = DigestOf(file);
        if (!bad_root) expected.data[0] ^= 1;
        hyd.SetExpectedSha384(expected);
        if (bad_root) hyd.SetExpectedPiecesRoot(Digest48{});
        std::string err;
        BOOST_REQUIRE(hyd.Feed(Span<const unsigned char>{file.data(), file.size()}, err));
        BOOST_CHECK(!hyd.Finish(err));
        BOOST_CHECK(hyd.IntegrityFailed());
        BOOST_CHECK_EQUAL(err, bad_root ? "pieces_root mismatch" : "file SHA-384 mismatch");
        BOOST_CHECK(!live.HasPiece(artifact, 0, 0));
    }
}
void finished_hydration_releases_its_quarantine_copy()
{
    using namespace modelnet;
    // Each hydration opens the quarantine with the -modelstorage quota and
    // recounts the pieces already in it. Room for one file there must be
    // enough for files hydrated one after another.
    const fs::path qdir = Scratch(m_path_root, "release-q");
    ModelStore live(Scratch(m_path_root, "release-live"), 64 << 20);
    for (const unsigned char tag : {0x81, 0x82}) {
        const std::vector<unsigned char> file(PIECE_SIZE + 1, tag);
        Digest48 artifact{};
        artifact.data[0] = tag;
        ModelStore q(qdir, PIECE_SIZE + PIECE_SIZE / 2);
        FileStreamHydration hyd(artifact, 0, file.size(), live, q);
        hyd.SetExpectedSha384(DigestOf(file));
        std::string err;
        BOOST_REQUIRE_MESSAGE(hyd.Feed(Span<const unsigned char>{file.data(), file.size()}, err), err);
        BOOST_REQUIRE_MESSAGE(hyd.Finish(err), err);
        BOOST_CHECK(live.HasPiece(artifact, 0, 0));
        BOOST_CHECK(live.HasPiece(artifact, 0, 1));
        BOOST_CHECK(!q.HasPiece(artifact, 0, 0));
        BOOST_CHECK(!q.HasPiece(artifact, 0, 1));
    }
}
int main(int argc,char**argv){try{if(argc!=3)return 2;m_path_root=argv[2];fs::create_directories(m_path_root);std::string name=argv[1];
if(name=="job_cleanup_failure_preserves_valid_eof_checkpoint") {job_cleanup_failure_preserves_valid_eof_checkpoint();std::cout<<"PASS job_cleanup_failure_preserves_valid_eof_checkpoint\n";return 0;}
if(name=="missing_eof_quarantine_does_not_advance_resume_cursor") {missing_eof_quarantine_does_not_advance_resume_cursor();std::cout<<"PASS missing_eof_quarantine_does_not_advance_resume_cursor\n";return 0;}
if(name=="short_final_checkpoint_survives_publication_quota_failure") {short_final_checkpoint_survives_publication_quota_failure();std::cout<<"PASS short_final_checkpoint_survives_publication_quota_failure\n";return 0;}
if(name=="only_complete_file_integrity_mismatches_mark_rejection") {only_complete_file_integrity_mismatches_mark_rejection();std::cout<<"PASS only_complete_file_integrity_mismatches_mark_rejection\n";return 0;}
if(name=="finished_hydration_releases_its_quarantine_copy") {finished_hydration_releases_its_quarantine_copy();std::cout<<"PASS finished_hydration_releases_its_quarantine_copy\n";return 0;}
return 2;}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<"\n";return 1;}}
