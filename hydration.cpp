#include <crypto/sha384.h>
#include <modelnet/file_stream.h>
#include <util/readwritefile.h>

#include <csignal>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <sys/resource.h>

using namespace modelnet;

void Require(bool ok, const std::string& message)
{
    if (!ok) throw std::runtime_error(message);
}

void Check(const fs::path& root, bool fault)
{
    std::vector<unsigned char> file(PIECE_SIZE * 3, 0x46);
    file[0] = 0x01;
    file[PIECE_SIZE] = 0x02;
    file.back() = 0x03;
    const Span<const unsigned char> second{file.data() + PIECE_SIZE, PIECE_SIZE};
    Digest48 digest{}, artifact{};
    artifact.data[0] = 0x34;
    CSHA384{}.Write(file.data(), file.size()).Finalize(digest.data.data());
    const auto jobs = root / "jobs";
    const auto path = FileStreamJobPath(jobs, artifact, 0);
    const auto live_dir = root / "live";
    const auto q_dir = root / "quarantine";
    std::string err;
    std::pair<bool, std::string> old;
    {
        ModelStore live(live_dir, 64 << 20), q(q_dir, 64 << 20);
        FileStreamHydration hydration(artifact, 0, file.size(), live, q);
        hydration.SetJobDir(jobs);
        hydration.SetExpectedSha384(digest);
        Require(hydration.Feed({file.data(), PIECE_SIZE}, err), err);
        old = ReadBinaryFile(path);
        Require(old.first && old.second.size() > 8, "old job record missing");
        if (fault) {
            // Reuse a verified second piece so the size limit reaches the cursor save.
            Require(q.PutVerifiedPiece(artifact, 0, 1, second, ChunkLeaf(1, second), err), err);
            struct rlimit saved{};
            Require(getrlimit(RLIMIT_FSIZE, &saved) == 0, "getrlimit");
            auto previous = std::signal(SIGXFSZ, SIG_IGN);
            Require(previous != SIG_ERR, "signal");
            struct rlimit limited{saved};
            limited.rlim_cur = 8;
            Require(setrlimit(RLIMIT_FSIZE, &limited) == 0, "limit");
            bool ok;
            try {
                ok = hydration.Feed(second, err);
            } catch (...) {
                setrlimit(RLIMIT_FSIZE, &saved);
                std::signal(SIGXFSZ, previous);
                throw;
            }
            Require(setrlimit(RLIMIT_FSIZE, &saved) == 0, "restore limit");
            Require(std::signal(SIGXFSZ, previous) != SIG_ERR, "restore signal");
            Require(!ok && err == "failed to write file stream job", "fault missed cursor save: " + err);
            std::cout << "fault_error=" << err << '\n';
            Require(hydration.ResumeOffset() == 2 * PIECE_SIZE && !hydration.IsAdvertisable(), "unexpected in-memory progress");
        }
    }

    ModelStore live(live_dir, 64 << 20), q(q_dir, 64 << 20);
    auto observed = ReadBinaryFile(path);
    Require(observed.first, "cursor file disappeared");
    FileStreamJobRecord record;
    const bool loaded = LoadFileStreamJob(jobs, artifact, 0, record, err);
    if (fault) {
        Require(q.HasPiece(artifact, 0, 0) && q.HasPiece(artifact, 0, 1), "verified pieces lost");
        std::cout << "old_bytes=" << old.second.size() << " after_bytes=" << observed.second.size()
                  << " preserved=" << (old == observed) << " reopened=" << loaded << " reload_error=" << err << '\n';
        if (loaded) Require(old == observed && record.resume_offset == PIECE_SIZE, "reopened wrong cursor");
        else Require(old != observed && observed.second.size() == 8, "unexpected failed cursor contents");
    } else {
        Require(loaded && record.resume_offset == PIECE_SIZE && old == observed, "healthy reopen failed");
    }

    FileStreamHydration retry(artifact, 0, file.size(), live, q);
    retry.SetJobDir(jobs);
    retry.SetExpectedSha384(digest);
    if (loaded) Require(retry.ApplyRecord(record, err), err);
    const size_t start = retry.ResumeOffset();
    Require(start == (loaded ? PIECE_SIZE : 0), "unexpected retry offset");
    size_t pos = start;
    auto read = [&](size_t want, unsigned char* buf, size_t& got, std::string&) {
        got = std::min(want, file.size() - pos);
        std::memcpy(buf, file.data() + pos, got);
        pos += got;
        return true;
    };
    Require(retry.Ingest(read, loaded, err), err);
    Require(retry.IsAdvertisable() && retry.Progress().pieces_verified == 3, "retry did not verify all pieces");
    Require(retry.Progress().origin_range_ops == (loaded ? 1 : 0), "unexpected range count");
    Require(!fs::exists(path), "completed job record remains");
    for (uint32_t i = 0; i < 3; ++i) {
        std::vector<unsigned char> piece;
        Require(live.GetPiece(artifact, 0, i, piece, err), err);
        Require(piece.size() == PIECE_SIZE &&
                std::equal(piece.begin(), piece.end(), file.begin() + i * PIECE_SIZE), "promoted bytes differ");
    }
    std::cout << (fault ? "fault_retry" : "healthy_control") << " start=" << start
              << " bytes_read=" << pos - start << " verified_pieces=3 exact_bytes=1 cleaned=1\n";
    if (fault) Require(loaded && old == observed && start == PIECE_SIZE, "old cursor did not survive");
}

int main(int argc, char** argv)
{
    if (argc != 2) return 2;
    try {
        Check(fs::PathFromString(argv[1]) / "control", false);
        Check(fs::PathFromString(argv[1]) / "fault", true);
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
