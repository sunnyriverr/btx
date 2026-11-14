from pathlib import Path
import os,json,shlex,subprocess
w=Path(os.environ['GITHUB_WORKSPACE']);b=w/'gui-pilot-runtime/qtbuild';rows=json.loads((b/'compile_commands.json').read_text());row=next(r for r in rows if r['file'].endswith('/src/modeld.cpp'));args=shlex.split(row['command']);oi=args.index('-o')+1
for source,target in [(w/'component-checks.cpp',w/'candidate/component-checks.o'),(w/'product/src/test/modelnet_file_stream_tests.cpp',w/'candidate/maintained-file-stream-tests.o')]:
 a=args.copy();a[oi]=str(target);a[a.index(row['file'])]=str(source);a.append('-UNDEBUG');subprocess.run(a,cwd=b,check=True,timeout=180)
commands=subprocess.check_output(['ninja','-C',str(b),'-t','commands','btx-modeld'],text=True);line=next(l for l in commands.splitlines() if ' -o bin/btx-modeld ' in l);a=shlex.split(line)
assert a[:2]==[':','&&'] and a[-2:]==['&&',':'];a=a[2:-2];obj=next(x for x in a if x.endswith('/btx-modeld.dir/modeld.cpp.o'));a[a.index(obj)]=str(w/'candidate/component-checks.o');a[a.index('-o')+1]=str(w/'candidate/component-checks');subprocess.run(a,cwd=b,check=True,timeout=180)
subprocess.run([str(w/'candidate/component-checks'),str(w/'component-runtime')],check=True,timeout=90)
