bool MaterializeCompleteFile(const std::vector<std::vector<unsigned char>>& pieces, const std::string& dest,
                             Generation16 gen, std::string& err_code, std::string& err)
{
    if (dest.find("..") != std::string::npos) {
        err_code = "INVALID_PARAMETER";
        err = "dest";
        return false;
    }
    if (pieces.empty()) {
        err_code = "RANGE_UNVERIFIED";
        err = "complete file requires at least one verified piece";
        return false;
    }
    for (const auto& p : pieces) {
        if (p.empty()) {
            err_code = "RANGE_UNVERIFIED";
            err = "empty piece cannot be materialized as a complete file (no sparse holes)";
            return false;
        }
    }
    const int fd = ::open(dest.c_str(), O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0444);
    if (fd < 0) {
        err_code = "OVERWRITE_REFUSED";
        err = "exclusive dest";
        return false;
    }
    off_t off = 0;
    for (const auto& p : pieces) {
        const ssize_t n = ::pwrite(fd, p.data(), p.size(), off);
        if (n < 0 || static_cast<size_t>(n) != p.size()) {
            ::close(fd);
            ::unlink(dest.c_str());
            err_code = "IO_ERROR";
            err = "pwrite";
            return false;
        }
        off += static_cast<off_t>(p.size());
    }
    if (::fsync(fd) != 0) {
        ::close(fd);
        ::unlink(dest.c_str());
        err_code = "IO_ERROR";
        err = "fsync";
        return false;
    }
    if (::close(fd) != 0) {
        ::unlink(dest.c_str());
        err_code = "IO_ERROR";
        err = "close payload";
        return false;
    }
    const std::string sidecar = dest + ".gen";
    const std::string metadata = GenerationHex(gen) + "\n" + std::to_string(pieces.size()) + "\n";
    const int sidecar_fd = ::open(sidecar.c_str(), O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0666);
    if (sidecar_fd < 0) {
        ::unlink(dest.c_str());
        err_code = "IO_ERROR";
        err = "generation sidecar";
        return false;
    }
    size_t written = 0;
    while (written < metadata.size()) {
        const ssize_t count = ::write(sidecar_fd, metadata.data() + written, metadata.size() - written);
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) break;
        written += static_cast<size_t>(count);
    }
    const bool closed = ::close(sidecar_fd) == 0;
    if (written != metadata.size() || !closed) {
        ::unlink(sidecar.c_str());
        ::unlink(dest.c_str());
        err_code = "IO_ERROR";
        err = "generation sidecar";
        return false;
    }
    return true;
}
