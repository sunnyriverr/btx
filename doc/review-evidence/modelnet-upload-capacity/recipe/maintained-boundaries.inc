BOOST_AUTO_TEST_CASE(r2s_02_upload_capacity_boundaries)
{
    using namespace modelnet;
    const uint64_t base = kCloudStreamChunkBytes;
    const uint64_t parts = kCloudMaxMultipartParts;
    BOOST_CHECK_EQUAL(CloudUploadPartBytes(0), base);
    BOOST_CHECK_EQUAL(CloudUploadPartBytes(1), base);
    BOOST_CHECK_EQUAL(CloudUploadPartBytes(2 * base), base);
    for (uint64_t chunk = base; chunk <= kCloudMaxUploadPartBytes; chunk *= 2) {
        const uint64_t limit = chunk * parts;
        BOOST_CHECK_EQUAL(CloudUploadPartBytes(limit - 1), chunk);
        BOOST_CHECK_EQUAL(CloudUploadPartBytes(limit), chunk);
        BOOST_CHECK_EQUAL(CloudUploadPartBytes(limit + 1),
                          chunk == kCloudMaxUploadPartBytes ? 0 : chunk * 2);
    }
    BOOST_CHECK_EQUAL(CloudUploadPartBytes(std::numeric_limits<uint64_t>::max()), 0U);
}

