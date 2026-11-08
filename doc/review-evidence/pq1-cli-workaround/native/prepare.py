from pathlib import Path
import hashlib,json
p=Path(__file__).resolve().parent;r=p.parent;runtime=(r/'pq1_runtime.cpp').read_text();tests=(r/'modelnet_tests.cpp').read_text()
def function(text,signature):
 start=text.index(signature);brace=text.index('{',start);depth=1;i=brace+1
 while depth:
  depth+=(text[i]=='{')-(text[i]=='}');i+=1
 return text[start:i]
parts=[function(runtime,x) for x in ['bool OpensslCliHasMlKem768(', 'std::string OpensslBin()', 'void Pq1SanitizeOpenSslEnv()', 'void Pq1InitOpenSsl()']]
(p/'runtime-extract.cpp').write_text('#include <openssl/ssl.h>\n#include <cstdlib>\n#include <cstdio>\n#include <string>\nnamespace modelnet {\n'+ '\n'.join(parts)+'\n}\n')
(p/'modelnet/pq1_runtime.h').write_text('#pragma once\nnamespace modelnet {void Pq1InitOpenSsl();}\n')
bodies=[function(tests,'BOOST_AUTO_TEST_CASE('+x+')') for x in ['pq1_handshake_mlkem768','pq1_rejects_hybrid_peer']]
preamble='''#define BOOST_TEST_MODULE pq1_component
#include <boost/test/included/unit_test.hpp>
#include <modelnet/transport_pq.h>
#include <openssl/ssl.h>
#include <openssl/bio.h>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <tinyformat.h>
namespace fs {using path=std::filesystem::path;using std::filesystem::create_directories;std::string PathToString(const path& p){return p.string();}}
namespace modelnet {std::string OpensslBin();}
const fs::path m_path_root=std::getenv("PQ1_TEST_ROOT");
std::string ReadAll(const fs::path& p){std::ifstream f(p);return std::string(std::istreambuf_iterator<char>(f),{});}
'''
(p/'test.cpp').write_text(preamble+'\n'.join(bodies)+'\n')
(p/'extraction.json').write_text(json.dumps({'source':'ff5f3f04ea11f044594987fc6be043ff68b136ad','runtime_functions':[{'signature':x.split('{')[0].strip(),'sha256':hashlib.sha256(x.encode()).hexdigest()} for x in parts],'unchanged_test_bodies':[hashlib.sha256(x.encode()).hexdigest() for x in bodies],'scope':'Exact two bodies with Boost assertions and real transport. Isolated filesystem/path adapter replaces full chain fixture; extracted runtime functions only. Not full test_btx.'},indent=2))
