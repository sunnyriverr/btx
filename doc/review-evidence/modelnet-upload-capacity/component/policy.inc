size_t CloudUploadPartBytes(uint64_t content_length)
{
    size_t part_bytes = kCloudStreamChunkBytes;
    while (content_length > uint64_t{part_bytes} * kCloudMaxMultipartParts &&
           part_bytes < kCloudMaxUploadPartBytes) {
        part_bytes *= 2;
    }
    return content_length <= uint64_t{part_bytes} * kCloudMaxMultipartParts ? part_bytes : 0;
}
