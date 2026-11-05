"""Same maintained regression body against exact baseline, candidate and broken control."""
from pathlib import Path
import hashlib, json, platform, subprocess
BASE='666673a3153225ba264c7870e0e82e354df86765'
F=Path('contrib/devtools/model-search-text-object'); O=Path('records'); O.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def cmd(args,label,check=True):
 r=subprocess.run(args,capture_output=True,text=True,timeout=180)
 (O/(label+'.log')).write_text(r.stdout+r.stderr);print(label,r.returncode,flush=True)
 if check:assert r.returncode==0,label
 return r
original=subprocess.check_output(['git','show',BASE+':src/rpc/client.cpp']).decode()
assert Path('src/rpc/client.cpp').read_text()==original
oldtest=subprocess.check_output(['git','show',BASE+':src/test/rpc_tests.cpp']).decode()
test=(F/'rpc_tests.cpp').read_text();a=test.index('BOOST_AUTO_TEST_CASE(rpc_convert_values_model_search_text_or_object)');b=test.index('BOOST_AUTO_TEST_CASE(rpc_getblockstats_calculate_percentiles_by_weight)',a);case=test[a:b]
assert test.replace(case,'',1)==oldtest
expected=original;naive=original
for method in ['searchmodels','searchpublishers','searchcollections']:
 old='{ "'+method+'", 0, "query" },';assert original.count(old)==1
 expected=expected.replace(old,'{ "'+method+'", 0, "query", /*also_string=*/false, /*json_object=*/true },')
 naive=naive.replace(old,'{ "'+method+'", 0, "query", /*also_string=*/true },')
candidate=(F/'candidate-client.cpp').read_text();assert candidate==expected
controls=r'''
BOOST_AUTO_TEST_CASE(unaffected_conversion_controls)
{
 BOOST_CHECK_EQUAL(RPCConvertValues("setmocktime", {"7"})[0].getInt<int>(),7);
 BOOST_CHECK_EQUAL(RPCConvertNamedValues("setmocktime", {"timestamp=7"})["timestamp"].getInt<int>(),7);
 BOOST_CHECK_EQUAL(RPCConvertValues("getblock", {"plain-text"})[0].get_str(),"plain-text");
 BOOST_CHECK(RPCConvertValues("hostmodel", {"path","{}"})[1].isObject());
 BOOST_CHECK_EQUAL(RPCConvertValues("hostmodel", {"path","[]"})[1].get_str(),"[]");
 BOOST_CHECK_EQUAL(RPCConvertValues("getmodel", {"id","FREE_ONLY"})[1].get_str(),"FREE_ONLY");
 BOOST_CHECK(RPCConvertValues("getmodel", {"id","{}"})[1].isObject());
 BOOST_CHECK_THROW(RPCConvertValues("browsemodels", {"plain-text"}),std::runtime_error);
}
'''
wrapper=O/'regression.cpp';wrapper.write_text('#define BOOST_TEST_MODULE model_search_conversion\n#include <vector>\n#include <boost/test/included/unit_test.hpp>\n#include <rpc/client.h>\n'+case+controls)
flags=['g++','-std=c++20','-O0','-include','vector','-Isrc','-Isrc/univalue/include'];objects=[]
for name in ['univalue','univalue_get','univalue_read','univalue_write']:
 obj=O/(name+'.o');cmd(flags+['-c','src/univalue/lib/'+name+'.cpp','-o',str(obj)],'build-'+name);objects.append(str(obj))
obj=O/'regression.o';cmd(flags+['-c',str(wrapper),'-o',str(obj)],'build-regression');objects.append(str(obj))
summary={'base':BASE,'fixture_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'platform':platform.platform(),'compiler':subprocess.check_output(['g++','--version'],text=True),'case_sha256':hashlib.sha256(case.encode()).hexdigest(),'wrapper_sha256':sha(wrapper),'scope':'Exact maintained case body in standalone Boost runner; no full test_btx fixture, RPC, node or helper execution','runs':{}}
for name,text in [('baseline',original),('candidate',candidate),('naive_also_string',naive)]:
 src=O/(name+'.cpp');src.write_text(text);obj=O/(name+'.o');cmd(flags+['-c',str(src),'-o',str(obj)],'build-'+name)
 binary=O/(name+'-test');cmd(['g++',str(obj)]+objects+['-pthread','-o',str(binary)],'link-'+name)
 r=cmd([str(binary),'--log_level=test_suite','--report_level=detailed'],'test-'+name,False)
 summary['runs'][name]={'exit':r.returncode,'source_sha256':sha(src),'binary_sha256':sha(binary),'wrapper_object_sha256':sha(O/'regression.o')};(O/'result.json').write_text(json.dumps(summary,indent=2)+'\n')
assert summary['runs']['baseline']['exit']!=0 and summary['runs']['candidate']['exit']==0 and summary['runs']['naive_also_string']['exit']!=0
assert len({v['wrapper_object_sha256'] for v in summary['runs'].values()})==1
summary['paired_proof_pass']=True;(O/'result.json').write_text(json.dumps(summary,indent=2)+'\n')
for pattern in ['*.o','*-test','*.cpp']:
 for p in O.glob(pattern):p.unlink()
print('Paired proof and controls passed; naive fallback rejected by same case')
