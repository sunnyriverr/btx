#define BOOST_TEST_MODULE CloudCompletionEnvelope
#include <boost/test/included/unit_test.hpp>
#include <modelnet/s3_client.h>
#include <util/translation.h>
const TranslateFn G_TRANSLATION_FUN{nullptr};
BOOST_AUTO_TEST_CASE(s3_multipart_completion_requires_success_envelope)
{
    using modelnet::S3MultipartCompletionSucceeded;
    const char* valid[] = {
        "<CompleteMultipartUploadResult><ETag>ok</ETag></CompleteMultipartUploadResult>",
        " \r\n\t<?xml version=\"1.0\"?>\n<CompleteMultipartUploadResult xmlns=\"http://s3.amazonaws.com/doc/2006-03-01/\"><ETag>ok</ETag></CompleteMultipartUploadResult>\n",
        "<s3:CompleteMultipartUploadResult xmlns:s3=\"http://s3.amazonaws.com/doc/2006-03-01/\"><s3:ETag>ok</s3:ETag></s3:CompleteMultipartUploadResult>",
        "\xef\xbb\xbf<?xml version=\"1.0\"?><!-- progress --><CompleteMultipartUploadResult><ETag>ok</ETag></CompleteMultipartUploadResult><!-- done -->",
    };
    for (const auto* xml : valid) BOOST_CHECK_MESSAGE(S3MultipartCompletionSucceeded(xml), xml);
    const char* refused[] = {
        "<Error><Code>InternalError</Code></Error>",
        "<s3:Error xmlns:s3=\"http://s3.amazonaws.com/doc/2006-03-01/\"><s3:Code>InternalError</s3:Code></s3:Error>",
        "<Error><Message><![CDATA[<CompleteMultipartUploadResult></CompleteMultipartUploadResult>]]></Message></Error>",
        "", " \r\n", "<Unknown></Unknown>", "<CompleteMultipartUploadResult>",
        "<CompleteMultipartUploadResult/>", "<CompleteMultipartUploadResultOther></CompleteMultipartUploadResultOther>",
        "<CompleteMultipartUploadResult></other:CompleteMultipartUploadResult>",
        "<CompleteMultipartUploadResult></CompleteMultipartUploadResultExtra>",
        "<CompleteMultipartUploadResult></CompleteMultipartUploadResult><Error></Error>",
        "<!-- incomplete", "<?xml version=\"1.0\"",
    };
    for (const auto* xml : refused) BOOST_CHECK_MESSAGE(!S3MultipartCompletionSucceeded(xml), xml);
}
