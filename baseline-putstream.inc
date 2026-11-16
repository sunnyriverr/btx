bool S3Client::PutStream(const std::string& key, std::istream& body, uint64_t content_length, std::string& err)
{
    if (!EnsureReady(err)) return false;
    m_last_put_max_buffer = 0;
    const size_t chunk = kCloudStreamChunkBytes;
    auto read_n = [&](std::vector<unsigned char>& buf, size_t n) -> bool {
        buf.resize(n);
        if (n == 0) return true;
        body.read(reinterpret_cast<char*>(buf.data()), static_cast<std::streamsize>(n));
        const auto got = static_cast<size_t>(body.gcount());
        buf.resize(got);
        m_last_put_max_buffer = std::max(m_last_put_max_buffer, got);
        return got == n || body.eof();
    };

    auto live_abort = [&](const std::string& upload_id) {
        if (upload_id.empty() || m_fake) return;
        SigV4Request abort = BaseSigned("DELETE", key, {}, {}, {}, /*write=*/true);
        abort.query["uploadId"] = upload_id;
        S3HttpResult ignored;
        std::string aerr;
        (void)PerformS3Http(m_cfg, abort, {}, /*sign=*/true, /*read_body=*/true, kS3HttpsMaxControlBytes, {}, ignored,
                            aerr);
    };

    auto live_begin = [&](std::string& upload_id) -> bool {
        SigV4Request req = BaseSigned("POST", key, {}, {}, {}, /*write=*/true);
        req.query["uploads"] = "";
        S3HttpResult res;
        if (!PerformS3Http(m_cfg, req, {}, /*sign=*/true, /*read_body=*/true, kS3HttpsMaxControlBytes, {}, res, err) ||
            !FinishS3Http(res, err)) {
            err = FailCloud(err, m_write_secret.empty() ? m_secret : m_write_secret);
            return false;
        }
        const std::string xml(res.body.begin(), res.body.end());
        if (!XmlTagValue(xml, "UploadId", upload_id)) {
            err = FailCloud("s3 https multipart missing upload id");
            return false;
        }
        return true;
    };

    auto live_part = [&](const std::string& upload_id, int part, Span<const unsigned char> buf, std::string& etag) -> bool {
        SigV4Request req = BaseSigned("PUT", key, buf, {}, {}, /*write=*/true);
        req.query["partNumber"] = std::to_string(part);
        req.query["uploadId"] = upload_id;
        S3HttpResult res;
        if (!PerformS3Http(m_cfg, req, buf, /*sign=*/true, /*read_body=*/true, kS3HttpsMaxControlBytes, {}, res, err) ||
            !FinishS3Http(res, err)) {
            err = FailCloud(err, m_write_secret.empty() ? m_secret : m_write_secret);
            return false;
        }
        etag = res.etag;
        if (etag.empty()) {
            err = FailCloud("s3 https multipart missing etag");
            return false;
        }
        return true;
    };

    auto live_complete = [&](const std::string& upload_id, const std::vector<std::pair<int, std::string>>& parts) -> bool {
        std::string xml = "<CompleteMultipartUpload>";
        for (const auto& p : parts) {
            xml += "<Part><PartNumber>";
            xml += std::to_string(p.first);
            xml += "</PartNumber><ETag>";
            xml += p.second;
            xml += "</ETag></Part>";
        }
        xml += "</CompleteMultipartUpload>";
        const Span<const unsigned char> body_span{reinterpret_cast<const unsigned char*>(xml.data()), xml.size()};
        SigV4Request req = BaseSigned("POST", key, body_span, {}, {}, /*write=*/true);
        req.query["uploadId"] = upload_id;
        S3HttpResult res;
        if (!PerformS3Http(m_cfg, req, body_span, /*sign=*/true, /*read_body=*/true, kS3HttpsMaxControlBytes, {}, res,
                           err) ||
            !FinishS3Http(res, err)) {
            err = FailCloud(err, m_write_secret.empty() ? m_secret : m_write_secret);
            return false;
        }
        return true;
    };

    if (content_length > 0 && content_length <= chunk) {
        std::vector<unsigned char> buf;
        if (!read_n(buf, static_cast<size_t>(content_length)) || buf.size() != content_length) {
            err = "short cloud put";
            return false;
        }
        return Put(key, buf, err);
    }

    if (m_fake) {
        if (content_length == 0) {
            std::vector<unsigned char> first;
            if (!read_n(first, chunk)) {
                err = "cloud put read failed";
                return false;
            }
            if (body.eof() || first.size() < chunk) {
                return Put(key, first, err);
            }
            std::string upload_id;
            if (!m_fake->BeginMultipart(key, upload_id, err)) return false;
            int part = 1;
            if (!m_fake->UploadPart(upload_id, part++, first, err)) return false;
            while (body) {
                std::vector<unsigned char> buf;
                if (!read_n(buf, chunk)) {
                    err = "cloud put chunk read failed";
                    return false;
                }
                if (buf.empty()) break;
                if (!m_fake->UploadPart(upload_id, part++, buf, err)) return false;
                if (buf.size() < chunk) break;
            }
            const bool ok = m_fake->CompleteMultipart(upload_id, err);
            if (ok) m_saw_put = true;
            return ok;
        }

        std::string upload_id;
        if (!m_fake->BeginMultipart(key, upload_id, err)) return false;
        int part = 1;
        uint64_t remaining = content_length;
        while (remaining > 0) {
            const size_t n = static_cast<size_t>(std::min<uint64_t>(remaining, chunk));
            std::vector<unsigned char> buf;
            if (!read_n(buf, n) || buf.size() != n) {
                err = "cloud put chunk read failed";
                return false;
            }
            if (!m_fake->UploadPart(upload_id, part++, buf, err)) return false;
            remaining -= n;
        }
        const bool ok = m_fake->CompleteMultipart(upload_id, err);
        if (ok) m_saw_put = true;
        return ok;
    }

    std::vector<std::pair<int, std::string>> parts;
    std::string upload_id;
    int part = 1;

    if (content_length == 0) {
        std::vector<unsigned char> first;
        if (!read_n(first, chunk)) {
            err = "cloud put read failed";
            ++m_errors;
            return false;
        }
        if (body.eof() || first.size() < chunk) {
            return Put(key, first, err);
        }
        if (!live_begin(upload_id)) {
            ++m_errors;
            return false;
        }
        std::string etag;
        if (!live_part(upload_id, part, first, etag)) {
            live_abort(upload_id);
            ++m_errors;
            return false;
        }
        parts.emplace_back(part, std::move(etag));
        ++part;
        while (body) {
            if (part > kS3HttpsMaxParts) {
                live_abort(upload_id);
                err = FailCloud("s3 https too many multipart parts");
                ++m_errors;
                return false;
            }
            std::vector<unsigned char> buf;
            if (!read_n(buf, chunk)) {
                live_abort(upload_id);
                err = "cloud put chunk read failed";
                ++m_errors;
                return false;
            }
            if (buf.empty()) break;
            if (!live_part(upload_id, part, buf, etag)) {
                live_abort(upload_id);
                ++m_errors;
                return false;
            }
            parts.emplace_back(part, std::move(etag));
            ++part;
            if (buf.size() < chunk) break;
        }
        if (!live_complete(upload_id, parts)) {
            live_abort(upload_id);
            ++m_errors;
            return false;
        }
        m_saw_put = true;
        return true;
    }

    if (!live_begin(upload_id)) {
        ++m_errors;
        return false;
    }
    uint64_t remaining = content_length;
    while (remaining > 0) {
        if (part > kS3HttpsMaxParts) {
            live_abort(upload_id);
            err = FailCloud("s3 https too many multipart parts");
            ++m_errors;
            return false;
        }
        const size_t n = static_cast<size_t>(std::min<uint64_t>(remaining, chunk));
        std::vector<unsigned char> buf;
        if (!read_n(buf, n) || buf.size() != n) {
            live_abort(upload_id);
            err = "cloud put chunk read failed";
            ++m_errors;
            return false;
        }
        std::string etag;
        if (!live_part(upload_id, part, buf, etag)) {
            live_abort(upload_id);
            ++m_errors;
            return false;
        }
        parts.emplace_back(part, std::move(etag));
        ++part;
        remaining -= n;
    }
    if (!live_complete(upload_id, parts)) {
        live_abort(upload_id);
        ++m_errors;
        return false;
    }
    m_saw_put = true;
    return true;
}
