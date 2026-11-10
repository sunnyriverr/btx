"""Resume verified Qt objects for the single relock-expiry correction."""
from pathlib import Path
import json,os,shutil,subprocess,tarfile
from checkpoint import create, restore_timestamps, sha, verify_restored
w=Path(os.environ["GITHUB_WORKSPACE"]).resolve()
out=w/"build-records";out.mkdir()
state={"source":"dac9aee53520bd49ed320ec7a49b9072fc7d88d9","phase":"restore"}
def run(args,label,limit=120,cwd=None):
    with (out/(label+".log")).open("wb") as log:
        subprocess.run(list(map(str,args)),stdout=log,stderr=subprocess.STDOUT,timeout=limit,cwd=cwd,check=True)
    return (out/(label+".log")).read_text()
try:
    archive=w/"saved-checkpoint/build-state.tar.gz"
    manifest=json.loads((w/"saved-checkpoint/manifest.json").read_text())
    prior=json.loads((w/"prior-build/result.json").read_text())
    assert prior["phase"]=="built"
    assert prior["patch_sha256"]=="0feec3c9eddcb419c948011e6aefb1743487e7d2711a31e0d65c224d6041be08"
    assert sha(archive)==manifest["archive_sha256"]==prior["successor_checkpoint_sha256"]
    assert manifest["identity"]["patch_sha256"]==prior["patch_sha256"]
    assert Path(manifest["workspace"])==w and shutil.disk_usage(w).free>10*1024**3
    with tarfile.open(archive) as tar:tar.extractall(w,filter="data")
    restore_timestamps(w,manifest);verify_restored(w,manifest)
    source=w/"product";build=w/"gui-pilot-runtime/qtbuild"
    old=json.loads((w/"prior-files.json").read_text())
    new=json.loads((w/"candidate-files.json").read_text())
    for name,h in old.items():assert sha(source/name)==h,name
    delta=sorted(n for n in new if new[n]!=old[n])
    assert delta==["doc/qt-wallet-recovery.md","src/qt/walletview.cpp","src/wallet/interfaces.cpp"]
    for name in run(["git","ls-files"],"accepted-files",cwd=w/"accepted-source").splitlines():
        if name not in old and (w/"accepted-source"/name).is_file():
            assert sha(source/name)==sha(w/"accepted-source"/name),name
    assert sha(build/"bin/btx-qt")==prior["candidate_qt"]
    assert run(["g++","-dumpfullversion"],"compiler").strip()=="11.4.0"
    assert "OpenSSL 3.5.9" in run([w/"gui-pilot-runtime/openssl/bin/openssl","version"],"openssl")
    for name in delta:
        target=source/name
        shutil.copyfile(w/"overlay"/name,target)
        target.touch()
    assert all(sha(source/name)==h for name,h in new.items())
    run(["cmake","-P",build/"CMakeFiles/VerifyGlobs.cmake"],"verify-globs",cwd=build)
    observed=out/"observed.ninja";shutil.copy2(build/"build.ninja",observed)
    plan=run(["ninja","-C",build,"-f",observed,"-n","btx-qt"],"build-plan")
    assert "interfaces.cpp.o" in plan
    state["planned_steps"]=sum(x.startswith("[") for x in plan.splitlines())
    assert state["planned_steps"]<=12
    state.update(phase="compile",patch_sha256=sha(w/"candidate.patch"),baseline_binaries=prior["baseline_binaries"])
    run(["ninja","-C",build,"-j2","btx-qt"],"compile",300)
    state["candidate_qt"]=sha(build/"bin/btx-qt")
    assert state["candidate_qt"]!=prior["candidate_qt"]
    assert all(sha(build/"bin"/n)==prior["baseline_binaries"][n] for n in ("btxd","btx-cli"))
    binaries=w/"compiled-binaries";binaries.mkdir()
    for n in ("btx-qt","btxd","btx-cli"):shutil.copy2(build/"bin"/n,binaries/n)
    state["phase"]="built"
except Exception as exc:
    state["error"]=repr(exc)
    raise
finally:
    if state.get("phase") in ("compile","built"):
        try:
            m=create(w,w/"compiled-checkpoint",{"source":state["source"],"patch_sha256":state["patch_sha256"]})
            state["successor_checkpoint_sha256"]=m["archive_sha256"]
        except Exception as exc:state["checkpoint_error"]=repr(exc)
    (out/"result.json").write_text(json.dumps(state,indent=2)+"\n")
