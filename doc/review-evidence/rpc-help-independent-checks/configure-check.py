from pathlib import Path
import subprocess,configparser,json
R=Path(__file__).resolve().parent
cmake='/opt/homebrew/bin/cmake'
original=(R/'source/test/CMakeLists.txt').read_text()

results=[]
for variant in ['baseline','candidate']:
 s=R/('config-'+variant);s.mkdir(exist_ok=True)
 source=original if variant=='candidate' else subprocess.check_output(['git','-C',str(R.parents[4]/'btx-contributions'),'show','666673a3:test/CMakeLists.txt']).decode()
 function=source[source.index('function(create_test_config)'):source.index('endfunction()')+len('endfunction()')]
 template=(R/'source/test/config.ini.in').read_text() if variant=='candidate' else subprocess.check_output(['git','-C',str(R.parents[4]/'btx-contributions'),'show','666673a3:test/config.ini.in']).decode()
 (s/'config.ini.in').write_text(template)
 (s/'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.22)\nproject(ConfigProof NONE)\noption(WITH_MODELNET "" ON)\n'+function+'\ncreate_test_config()\n')
 for flag in ['ON','OFF','Y','NO']:
  b=s/flag
  z=subprocess.run([cmake,'-S',str(s),'-B',str(b),'-DWITH_MODELNET='+flag],capture_output=True,text=True)
  (s/(flag+'.log')).write_text(z.stdout+z.stderr);assert z.returncode==0
  c=configparser.ConfigParser();c.read(b/'config.ini');observed=c.getboolean('components','ENABLE_MODELNET',fallback=None)
  ok=observed==(flag in ['ON','Y']);results.append(dict(variant=variant,flag=flag,observed=observed,acceptance=ok))
assert [x['acceptance'] for x in results]==[False]*4+[True]*4
(R/'config-verification.json').write_text(json.dumps({'cmake':subprocess.check_output([cmake,'--version']).decode().splitlines()[0],'scope':'Actual per-variant create_test_config functions and actual templates in compiler-free CMake project; not root node configuration','results':results},indent=2))
print('Actual CMake template generation: baseline 0/4, candidate 4/4 (ON/OFF/Y/NO).')
