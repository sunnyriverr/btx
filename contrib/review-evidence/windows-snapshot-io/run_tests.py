#!/usr/bin/env python3
"""Bounded component test using exact extracted snapshot reader and I/O helpers.
The offer/fs/hash adapters replace BTX types; full node integration is not tested.
"""
from pathlib import Path
import subprocess,json,hashlib,shutil,shlex
R=Path(__file__).resolve().parent
assert shutil.disk_usage(R).free >= 1342177280

def function(s, name):
    start=s.index(name);start=s.rfind('\n',0,start)+1
    brace=s.index('{',start);depth=1;i=brace+1
    while depth:
        depth+=(s[i]=='{')-(s[i]=='}');i+=1
    return s[start:i]+'\n'

pre=r'''
#include <cstdio>
#include <cstdint>
#include <vector>
#include <string>
#include <array>
#include <span>
#include <algorithm>
#include <limits>
#include <filesystem>
#include <stdexcept>
#include <sys/stat.h>
#include <openssl/sha.h>
#define Span std::span
using uint256=std::array<unsigned char,32>;
constexpr size_t ATTESTED_UTXO_SNAPSHOT_MAX_SERVE_BUFFER=(4u<<20)+256;
struct AttestedUTXOSnapshotOffer {uint64_t file_size;uint32_t chunk_size;uint32_t chunk_count;std::filesystem::path snapshot_path;};
namespace fsbridge { FILE* fopen(const std::filesystem::path& p,const char* m){return std::fopen(p.c_str(),m);} }
uint256 AttestedUTXOSnapshotBytesHash(std::span<const uint8_t> v){uint256 a,b;SHA256(v.data(),v.size(),a.data());SHA256(a.data(),a.size(),b.data());return b;}
void check(bool b,const char* message){if(!b)throw std::runtime_error(message);}
'''
main=r'''
int main(int argc,char**argv){try{
check(argc==2,"scratch path required");
const std::filesystem::path path=argv[1];
const auto small=path.string()+".small";
FILE* sf=std::fopen(small.c_str(),"wb");check(sf,"small open");
std::vector<uint8_t> normal(131072);for(size_t i=0;i<normal.size();++i)normal[i]=static_cast<uint8_t>(i/65536+17);
check(fwrite(normal.data(),1,normal.size(),sf)==normal.size(),"small write");check(fclose(sf)==0,"small close");
AttestedUTXOSnapshotOffer ordinary{normal.size(),65536,2,small};std::string ordinary_error;std::vector<uint8_t> ordinary_bytes;uint256 ordinary_hash;
for(uint32_t i=0;i<2;++i){check(ReadAttestedUTXOSnapshotChunk(ordinary,i,ordinary_bytes,ordinary_hash,ordinary_error),"normal read");check(ordinary_bytes==std::vector<uint8_t>(65536,static_cast<uint8_t>(17+i)),"normal bytes");check(ordinary_hash==AttestedUTXOSnapshotBytesHash(ordinary_bytes),"normal digest");}
std::filesystem::remove(small);std::puts("PASS: normal 128KiB file, both chunks and digests");
FILE* f=std::fopen(path.c_str(),"w+b");check(f,"open");
const uint32_t unit=65536;
const std::array<uint64_t,5> positions={0,(1ULL<<31)-unit,(1ULL<<31),(1ULL<<31)+unit,(1ULL<<32)+unit};
for(size_t i=0;i<positions.size();++i){check(fseeko(f,positions[i],SEEK_SET)==0,"fixture seek");std::vector<uint8_t> bytes(i==4?123:unit,static_cast<uint8_t>(0x31+i));check(fwrite(bytes.data(),1,bytes.size(),f)==bytes.size(),"fixture write");}
check(fclose(f)==0,"fixture close");
struct stat st{};check(stat(path.c_str(),&st)==0,"stat");check(st.st_blocks*512<1048576,"fixture must remain sparse");
AttestedUTXOSnapshotOffer offer{positions.back()+123,unit,static_cast<uint32_t>(positions.back()/unit+1),path};
std::string error;std::vector<uint8_t> bytes;uint256 digest;
for(size_t i=0;i<positions.size();++i){check(ReadAttestedUTXOSnapshotChunk(offer,positions[i]/unit,bytes,digest,error),"chunk read");check(bytes==std::vector<uint8_t>(i==4?123:unit,static_cast<uint8_t>(0x31+i)),"exact offset bytes");check(digest==AttestedUTXOSnapshotBytesHash(bytes),"chunk digest");}
#ifdef HAS_HELPERS
f=std::fopen(path.c_str(),"rb");check(f,"size open");check(SeekSnapshotFile(f,0,SEEK_END)==0,"seek end");check(TellSnapshotFile(f)==static_cast<int64_t>(offer.file_size),"64-bit size");check(SeekSnapshotFile(f,0,SEEK_SET)==0 && TellSnapshotFile(f)==0,"rewind");check(SeekSnapshotFile(f,-1,SEEK_SET)!=0,"negative seek rejected");check(fclose(f)==0,"size close");
#endif
check(!ReadAttestedUTXOSnapshotChunk(offer,offer.chunk_count,bytes,digest,error),"out of range");
auto short_offer=offer;short_offer.file_size++;check(!ReadAttestedUTXOSnapshotChunk(short_offer,offer.chunk_count-1,bytes,digest,error)&&bytes.empty(),"short read clears output");
auto missing=offer;missing.snapshot_path=path.string()+".missing";check(!ReadAttestedUTXOSnapshotChunk(missing,0,bytes,digest,error),"missing file");
auto large=offer;large.chunk_size=ATTESTED_UTXO_SNAPSHOT_MAX_SERVE_BUFFER+1;check(!ReadAttestedUTXOSnapshotChunk(large,0,bytes,digest,error),"buffer cap");
#ifdef HAS_HELPERS
auto overflow=offer;overflow.file_size=UINT64_MAX;overflow.chunk_size=UINT32_MAX;overflow.chunk_count=UINT32_MAX;check(!ReadAttestedUTXOSnapshotChunk(overflow,UINT32_MAX-1,bytes,digest,error) && error=="Chunk offset past end of file","unrepresentable offset");
#endif
std::filesystem::remove(path);
std::printf("PASS: five exact offsets including 2GiB and >4GiB; partial tail; errors; sparse allocated=%lld logical=%llu\n",static_cast<long long>(st.st_blocks*512),static_cast<unsigned long long>(offer.file_size));return 0;
}catch(const std::exception&e){std::fprintf(stderr,"FAIL: %s\n",e.what());return 1;}}
'''
results=[]
for variant in ['baseline','candidate','narrow-control']:
    source=(R/('baseline.cpp' if variant=='baseline' else 'candidate.cpp')).read_text()
    helpers='' if variant=='baseline' else function(source,'int SeekSnapshotFile(')+function(source,'int64_t TellSnapshotFile(')
    if variant=='narrow-control':helpers=helpers.replace('static_cast<off_t>(offset)','static_cast<off_t>(static_cast<int32_t>(offset))')
    tu=pre+helpers+function(source,'bool ReadAttestedUTXOSnapshotChunk(')+main
    cpp=R/(variant+'-test.cpp');cpp.write_text(tu);binary=R/(variant+'-test')
    cmd=['/usr/bin/c++','-std=c++20','-O1','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations','-I/opt/homebrew/opt/openssl@3/include',str(cpp),'-L/opt/homebrew/opt/openssl@3/lib','-lcrypto','-o',str(binary)]
    if variant!='baseline':cmd.insert(1,'-DHAS_HELPERS')
    b=subprocess.run(cmd,capture_output=True,text=True);(R/(variant+'-compile.log')).write_text(b.stdout+b.stderr)
    if b.returncode:raise RuntimeError(variant+' compile failed: '+b.stderr)
    p=subprocess.run([str(binary),str(R/'sparse.dat')],capture_output=True,text=True)
    (R/(variant+'-run.log')).write_text(p.stdout+p.stderr)
    (R/'sparse.dat').unlink(missing_ok=True)
    results.append({'variant':variant,'command':cmd,'exit':p.returncode,'output':p.stdout+p.stderr,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'harness_sha256':hashlib.sha256(cpp.read_bytes()).hexdigest(),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()})
    print(variant,p.returncode,p.stdout+p.stderr)
assert [x['exit'] for x in results]==[0,0,1]
(R/'test-results.json').write_text(json.dumps({'results':results,'free_after':shutil.disk_usage(R).free},indent=2))
