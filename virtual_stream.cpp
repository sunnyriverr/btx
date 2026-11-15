// Test-only adapters around byte-identical production PutStream; no network.
#include <algorithm>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <map>
#include <span>
#include <stdexcept>
#include <streambuf>
#include <string>
#include <vector>
template<class T> using Span = std::span<T>;
constexpr size_t kCloudStreamChunkBytes = size_t{8} << 20;
constexpr int kS3HttpsMaxParts = 10000;
constexpr uint64_t kS3HttpsMaxControlBytes = uint64_t{1} << 20;
struct SigV4Request {std::string method;std::map<std::string,std::string> query;};
struct S3HttpResult {std::vector<unsigned char> body;std::string etag;bool ok=true;};
struct Recording {uint64_t parts=0,bytes=0,begins=0,aborts=0,completes=0,direct=0;size_t largest=0;int fail_part=0;};
Recording rec;
std::string FailCloud(const std::string& e,const std::string& = {}) {return e;}
bool XmlTagValue(const std::string&,const std::string&,std::string& v){v="recording-upload";return true;}
bool FinishS3Http(const S3HttpResult& r,std::string&){return r.ok;}
bool PerformS3Http(int,const SigV4Request& q,Span<const unsigned char> body,bool sign,bool,size_t,Span<const unsigned char>,S3HttpResult& r,std::string& err){
 if(!sign)throw std::runtime_error("unsigned path");
 if(q.method=="DELETE"){++rec.aborts;return true;}
 if(q.query.contains("uploads")){++rec.begins;return true;}
 if(q.method=="PUT"){
  const auto n=std::stoull(q.query.at("partNumber"));
  if(n!=rec.parts+1)throw std::runtime_error("nonsequential part");
  ++rec.parts;rec.bytes+=body.size();rec.largest=std::max(rec.largest,body.size());
  if(rec.fail_part==int(n)){err="injected backend failure";return false;}
  r.etag="recording-etag";return true;
 }
 if(q.method=="POST"){++rec.completes;return true;}
 throw std::runtime_error("unexpected HTTP adapter path");
}
struct FakeForbidden {
 bool BeginMultipart(const std::string&,std::string&,std::string&){throw std::runtime_error("FakeS3 forbidden");}
 bool UploadPart(const std::string&,int,Span<const unsigned char>,std::string&){throw std::runtime_error("FakeS3 forbidden");}
 bool CompleteMultipart(const std::string&,std::string&){throw std::runtime_error("FakeS3 forbidden");}
};
class S3Client {
public:
 FakeForbidden* m_fake=nullptr;int m_cfg=0;size_t m_last_put_max_buffer=0;int m_errors=0;bool m_saw_put=false;std::string m_secret,m_write_secret;
 bool EnsureReady(std::string&){return true;}
 SigV4Request BaseSigned(const std::string& method,const std::string&,Span<const unsigned char>,const std::string&,const std::string&,bool){return {method,{}};}
 bool Put(const std::string&,Span<const unsigned char> b,std::string&){++rec.direct;rec.bytes+=b.size();return true;}
 bool PutStream(const std::string&,std::istream&,uint64_t,std::string&);
};
#include "putstream.inc"
class VirtualBytes:public std::streambuf {
public:
 uint64_t remaining,consumed=0;
 explicit VirtualBytes(uint64_t n):remaining(n){}
 std::streamsize xsgetn(char* dst,std::streamsize n) override {
  auto got=std::min<uint64_t>(remaining,uint64_t(n));
  std::memset(dst,0,size_t(got));remaining-=got;consumed+=got;return std::streamsize(got);
 }
 int_type underflow() override {return remaining?traits_type::to_int_type('\0'):traits_type::eof();}
};
int main(){
 constexpr uint64_t B=uint64_t(kCloudStreamChunkBytes)*kS3HttpsMaxParts;
 struct Case{const char* name;uint64_t actual,declared;int fail;};
 const Case cases[]={
 {"known_over",B+1,B+1,0},{"known_exact",B,B,0},
 {"unknown_exact",B,0,0},{"unknown_over",B+1,0,0},
 {"normal_two_parts",2*kCloudStreamChunkBytes,2*kCloudStreamChunkBytes,0},
 {"short_read",kCloudStreamChunkBytes,2*kCloudStreamChunkBytes,0},
 {"backend_failure",2*kCloudStreamChunkBytes,2*kCloudStreamChunkBytes,2},
 {"normal_direct",1024,1024,0}};
 for(const auto& c:cases){
  rec={};rec.fail_part=c.fail;S3Client client;VirtualBytes buf(c.actual);std::istream in(&buf);std::string err;
  bool ok=client.PutStream("bounded-test",in,c.declared,err);
  std::cout<<"{\"case\":\""<<c.name<<"\",\"ok\":"<<(ok?"true":"false")
   <<",\"branch\":\"live-adapted\",\"fake\":false,\"parts\":"<<rec.parts
   <<",\"bytes\":"<<rec.bytes<<",\"consumed\":"<<buf.consumed<<",\"begins\":"<<rec.begins
   <<",\"aborts\":"<<rec.aborts<<",\"completes\":"<<rec.completes<<",\"direct\":"<<rec.direct
   <<",\"max_buffer\":"<<client.m_last_put_max_buffer<<",\"error\":\""<<err<<"\"}\n"<<std::flush;
 }
}
