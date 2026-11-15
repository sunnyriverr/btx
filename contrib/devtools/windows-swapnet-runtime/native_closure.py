from pathlib import Path
import ctypes, ctypes.wintypes as wt, json, os, struct, subprocess, zipfile, urllib.request, hashlib, shutil

def download(pin, dest):
    with urllib.request.urlopen(pin['url'], timeout=180) as r:
        payload=r.read()
    assert hashlib.sha256(payload).hexdigest()==pin['sha256'], 'Input digest mismatch'
    dest.write_bytes(payload)
    return payload

def prepare(fixture, runtime, records, work):
    pins=json.loads((fixture/'windows-runtime-inputs.json').read_text())
    payload=download(pins['python'],work/'python-embed.zip')
    with zipfile.ZipFile(work/'python-embed.zip') as z:z.extractall(runtime)
    wheels=work/'wheels';wheels.mkdir()
    for pin in pins['wheels']:download(pin,wheels/pin['filename'])
    site=runtime/'Lib/site-packages'
    args=[__import__('sys').executable,'-m','pip','install','--no-index','--no-deps','--no-compile','--target',str(site)]+[str(wheels/p['filename']) for p in pins['wheels']]
    result=subprocess.run(args,capture_output=True,text=True,timeout=120)
    (records/'stage-locked-wheels.log').write_text(result.stdout+result.stderr);result.check_returncode()
    installer=work/'LLVM-20.1.8-win64.exe';download(pins['llvm'],installer)
    omp=work/'official-openmp';omp.mkdir()
    result=subprocess.run(['7z','e','-y','-r','-o'+str(omp),str(installer),'libomp.dll'],capture_output=True,text=True,timeout=120)
    (records/'extract-openmp.log').write_text(result.stdout+result.stderr);result.check_returncode()
    assert (omp/'libomp.dll').is_file()
    download(pins['llvm_license'],omp/'LICENSE.txt')
    (records/'windows-runtime-inputs.json').write_text(json.dumps(pins,indent=2)+'\n')
    manifest={str(p.relative_to(runtime)):hashlib.sha256(p.read_bytes()).hexdigest() for p in runtime.rglob('*') if p.is_file()}
    manifest['OpenMP/libomp.dll']=hashlib.sha256((omp/'libomp.dll').read_bytes()).hexdigest()
    manifest['OpenMP/LICENSE.txt']=hashlib.sha256((omp/'LICENSE.txt').read_bytes()).hexdigest()
    (records/'prepared-runtime-files.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return omp

def imports(path):
    b=path.read_bytes();pe=struct.unpack_from('<I',b,60)[0];opt=pe+24
    assert struct.unpack_from('<H',b,opt)[0]==0x20b
    n=struct.unpack_from('<H',b,pe+6)[0];size=struct.unpack_from('<H',b,pe+20)[0]
    table=[struct.unpack_from('<8sIIII',b,opt+size+40*i)[1:] for i in range(n)]
    def off(rva):
        for vs,va,rs,rp in table:
            if va<=rva<va+max(vs,rs):return rva-va+rp
        raise AssertionError('Bad RVA')
    def string(i):return b[i:b.index(b'\0',i)].decode('ascii')
    rva=struct.unpack_from('<I',b,opt+120)[0];out={}
    if not rva:return out
    entry=off(rva)
    for _ in range(4096):
        orig,_,_,name,thunk=struct.unpack_from('<IIIII',b,entry)
        if not (orig or name or thunk):break
        symbols=[];i=off(orig or thunk)
        for _ in range(65536):
            value=struct.unpack_from('<Q',b,i)[0]
            if not value:break
            symbols.append(value&0xffff if value>>63 else string(off(value)+2));i+=8
        out[string(off(name)).lower()]=symbols;entry+=20
    return out

def qualify_openmp(root, records):
    path=root/'bin/libomp140.x86_64.dll'
    dll=ctypes.WinDLL(str(path),winmode=0x100|0x1000)
    get=ctypes.windll.kernel32.GetProcAddress;get.argtypes=[wt.HMODULE,ctypes.c_void_p];get.restype=ctypes.c_void_p
    checked={}
    for exe in (root/'bin').glob('*.exe'):
        symbols=imports(exe).get('libomp140.x86_64.dll',[])
        for symbol in symbols:
            name=ctypes.c_char_p(symbol.encode()) if isinstance(symbol,str) else ctypes.c_void_p(symbol)
            assert get(dll._handle,ctypes.cast(name,ctypes.c_void_p)), str(symbol)
        if symbols:checked[exe.name]=symbols
    assert len(checked)==5,checked
    # Real fork/join through the LLVM microtask ABI; two native workers.
    dll.omp_set_dynamic.argtypes=[ctypes.c_int];dll.omp_set_dynamic(0)
    dll.omp_set_num_threads.argtypes=[ctypes.c_int];dll.omp_set_num_threads(2)
    dll.omp_get_num_threads.restype=ctypes.c_int
    seen=[]
    callback=ctypes.CFUNCTYPE(None,ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int))
    @callback
    def microtask(gtid,btid):seen.append((btid[0],dll.omp_get_num_threads()))
    class Ident(ctypes.Structure):_fields_=[('reserved1',ctypes.c_int),('flags',ctypes.c_int),('reserved2',ctypes.c_int),('reserved3',ctypes.c_int),('source',ctypes.c_char_p)]
    ident=Ident(0,2,0,0,b';archive-test;parallel;0;0;;')
    fork=dll.__kmpc_fork_call;fork.argtypes=[ctypes.POINTER(Ident),ctypes.c_int,callback];fork.restype=None
    fork(ctypes.byref(ident),0,microtask)
    assert sorted(seen)==[(0,2),(1,2)],seen
    report={'imported_symbols':checked,'parallel_workers':seen,'dll_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'alias':'official libomp.dll exact bytes, one shipped compatibility filename'}
    (records/'openmp-compatibility.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

def loaded_modules(pid):
    k=ctypes.WinDLL('kernel32',use_last_error=True);ps=ctypes.WinDLL('psapi',use_last_error=True)
    k.OpenProcess.argtypes=[wt.DWORD,wt.BOOL,wt.DWORD];k.OpenProcess.restype=wt.HANDLE
    k.CloseHandle.argtypes=[wt.HANDLE]
    ps.EnumProcessModulesEx.argtypes=[wt.HANDLE,ctypes.POINTER(wt.HMODULE),wt.DWORD,ctypes.POINTER(wt.DWORD),wt.DWORD];ps.EnumProcessModulesEx.restype=wt.BOOL
    ps.GetModuleFileNameExW.argtypes=[wt.HANDLE,wt.HMODULE,wt.LPWSTR,wt.DWORD];ps.GetModuleFileNameExW.restype=wt.DWORD
    handle=k.OpenProcess(0x410,False,pid);assert handle
    try:
        modules=(wt.HMODULE*2048)();needed=wt.DWORD()
        assert ps.EnumProcessModulesEx(handle,modules,ctypes.sizeof(modules),ctypes.byref(needed),3)
        out=[]
        for module in modules[:needed.value//ctypes.sizeof(wt.HMODULE)]:
            buf=ctypes.create_unicode_buffer(32768);assert ps.GetModuleFileNameExW(handle,module,buf,len(buf));out.append(buf.value)
        return out
    finally:k.CloseHandle(handle)
