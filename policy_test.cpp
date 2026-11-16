#include <modelnet/s3_client.h>
#include <util/translation.h>
const TranslateFn G_TRANSLATION_FUN{nullptr};
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <cstdlib>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <poll.h>
void require(bool x,const char* s){if(!x)throw std::runtime_error(s);}
#define BOOST_AUTO_TEST_CASE(n) void n()
#define BOOST_CHECK_EQUAL(a,b) require((a)==(b),#a " == " #b)
#include "maintained-boundaries.inc"
class NoRead:public std::streambuf{public:size_t reads=0;std::streamsize xsgetn(char*,std::streamsize)override{++reads;return 0;}};
int main(){try{
 r2s_02_upload_capacity_boundaries();
 setenv("BTX_UPLOAD_UNIT_CREDS","aws_access_key_id=fixture-access\naws_secret_access_key=fixture-secret\n",1);
 int fd=socket(AF_INET,SOCK_STREAM,0);require(fd>=0,"listener socket");sockaddr_in addr{};addr.sin_family=AF_INET;addr.sin_addr.s_addr=htonl(INADDR_LOOPBACK);require(bind(fd,reinterpret_cast<sockaddr*>(&addr),sizeof(addr))==0,"bind");require(listen(fd,1)==0,"listen");socklen_t len=sizeof(addr);require(getsockname(fd,reinterpret_cast<sockaddr*>(&addr),&len)==0,"port");
 modelnet::S3ClientConfig cfg;cfg.endpoint="http://127.0.0.1:"+std::to_string(ntohs(addr.sin_port));cfg.bucket="fixture";cfg.region="us-east-1";cfg.allow_http_loopback=true;cfg.use_fake=false;cfg.creds.kind=modelnet::CredentialRefKind::ENV;cfg.creds.value="BTX_UPLOAD_UNIT_CREDS";
 modelnet::S3Client client;std::string err;require(client.Init(cfg,err),err.c_str());
 for(uint64_t size:{uint64_t{modelnet::kCloudMaxUploadPartBytes}*modelnet::kCloudMaxMultipartParts+1,std::numeric_limits<uint64_t>::max()}){
  NoRead buf;std::istream stream(&buf);err.clear();require(!client.PutStream("early-refusal",stream,size,err),"oversize refused");require(err=="s3 https multipart upload exceeds bounded capacity","refusal signature");require(buf.reads==0&&client.LastPutMaxBufferBytes()==0,"no input read/buffer");pollfd p{fd,POLLIN,0};require(poll(&p,1,0)==0,"no HTTP connection");
 }
 close(fd);
 cfg.use_fake=true;modelnet::S3Client fake;require(fake.Init(cfg,err),err.c_str());std::string bytes(16<<20,'f');std::istringstream in(bytes);require(fake.PutStream("normal",in,bytes.size(),err),err.c_str());require(fake.LastPutMaxBufferBytes()==modelnet::kCloudStreamChunkBytes,"FakeS3 keeps8MiB");std::vector<unsigned char> got;require(fake.Get("normal",got,err),err.c_str());require(std::string(got.begin(),got.end())==bytes,"FakeS3 bytes");
 std::cout<<"PASS maintained boundary assertions, actual no-read/no-HTTP refusals, FakeS3 unchanged bytes\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<"\n";return 1;}}
