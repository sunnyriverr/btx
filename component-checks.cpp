#include <modelnet/file_stream.h>
#include <modelnet/store.h>
#include <crypto/sha384.h>
#include <span.h>
#include <util/fs.h>
#include <cassert>
#include <vector>
#include <iostream>
fs::path m_path_root;
fs::path Scratch(const fs::path& root,const std::string& name){auto p=root/name;fs::create_directories(p);return p;}
modelnet::Digest48 DigestOf(const std::vector<unsigned char>& b){modelnet::Digest48 d;CSHA384 h;h.Write(b.data(),b.size());h.Finalize(d.data.data());return d;}

void short_eof()
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
    assert(first.Feed(Span<const unsigned char>{file.data(), file.size()}, err));
    assert(!first.Finish(err));
    assert(err == "disk quota");
    assert(!first.IntegrityFailed());
    FileStreamJobRecord rec;
    assert(LoadFileStreamJob(jobs, artifact, 0, rec, err));
    assert(rec.next_piece == 2U);
    live.SetQuotaBytes(64 << 20);
    FileStreamHydration resumed(artifact, 0, file.size(), live, q);
    resumed.SetJobDir(jobs);
    assert(resumed.ApplyRecord(rec, err));
    assert(resumed.Progress().bytes_ingested == file.size());
    assert(resumed.Finish(err));
    assert(resumed.IsAdvertisable());
    assert(!fs::exists(FileStreamJobPath(jobs, artifact, 0)));
}

void rejection_flags()
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
        assert(hyd.Feed(Span<const unsigned char>{file.data(), file.size()}, err));
        assert(!hyd.Finish(err));
        assert(hyd.IntegrityFailed());
        assert(err == (bad_root ? "pieces_root mismatch" : "file SHA-384 mismatch"));
        assert(!live.HasPiece(artifact, 0, 0));
    }
}


int main(int argc,char**argv){assert(argc==2);m_path_root=fs::PathFromString(argv[1]);short_eof();rejection_flags();std::cout<<"COMPONENT_EOF_QUOTA_AND_INTEGRITY_PASS\n";}
