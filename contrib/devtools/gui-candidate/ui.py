"""Ordinary AT-SPI controls; no JS, bridge invocation or success-state injection."""
import time
import subprocess
import pyatspi

def controls():
    result = []
    def visit(n, depth=0):
        if depth > 35 or len(result) > 8000:
            return
        try:
            if n.getState().contains(pyatspi.STATE_SHOWING):
                result.append(n)
            for child in n:
                if child is not None:
                    visit(child, depth+1)
        except Exception:
            pass
    visit(pyatspi.Registry.getDesktop(0))
    return result

def text():
    out = []
    for n in controls():
        try:
            out.append(n.name or '')
            try:
                t = n.queryText()
                out.append(t.getText(0, min(t.characterCount, 20000)))
            except Exception:
                pass
        except Exception:
            pass
    return '\n'.join(out)

def wait(predicate, seconds=30):
    end = time.monotonic()+seconds
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(.5)
    raise TimeoutError('Expected GUI observation unavailable')

def click(name):
    matches = [n for n in controls() if n.name == name and n.getRoleName() in ('push button', 'button')]
    if len(matches) != 1:
        raise TimeoutError('Control not uniquely accessible: '+name)
    action = matches[0].queryAction()
    if not action.nActions or not action.doAction(0):
        raise TimeoutError('Control action unavailable: '+name)

def endpoint(value):
    import json,os
    from pathlib import Path
    diagnostic=[]
    def matches():
        found=[]
        diagnostic.clear()
        for n in controls():
            try:
                role=n.getRoleName();state=n.getState();name=n.name or ''
                editable=state.contains(pyatspi.STATE_EDITABLE)
                if editable or role in ('entry','text','password text'):
                    diagnostic.append({'role':role,'name':name,'editable':editable})
                inside=False;parent=n
                for _ in range(15):
                    if parent is None:break
                    if parent.getRoleName()=='dialog':inside=True;break
                    parent=parent.parent
                if role in ('entry','text') and editable and state.contains(pyatspi.STATE_ENABLED) and (inside or 'RPC_PORT' in name or 'Loopback endpoint' in name):
                    found.append(n)
            except Exception as error:
                diagnostic.append({'error':type(error).__name__})
        return found
    try:
        wait(lambda:len(matches())==1,15)
        n=matches()[0]
        assert n.queryComponent().grabFocus(), 'Endpoint focus refused'
        subprocess.run(['xdotool','key','--clearmodifiers','ctrl+a'],check=True,timeout=5)
        subprocess.run(['xdotool','type','--clearmodifiers','--',value],check=True,timeout=5)
        wait(lambda:n.queryText().getText(0,-1)==value,5)
    finally:
        (Path(os.environ['GITHUB_WORKSPACE'])/'atlas-window-results/endpoint-accessibility.json').write_text(json.dumps(diagnostic,indent=2)+'\n')

def file_path(path):
    # Focus the independently observed native GTK picker, not the underlying web form.
    windows=subprocess.check_output(['xdotool','search','--onlyvisible','--name',"Choose this BTX node's RPC"],text=True,timeout=5).splitlines()
    if len(windows)!=1:raise TimeoutError('Native cookie picker not uniquely visible')
    subprocess.run(['xdotool','windowactivate','--sync',windows[0]],check=True,timeout=5)
    subprocess.run(['xdotool','key','--clearmodifiers','ctrl+l'],check=True,timeout=5)
    time.sleep(.3)
    subprocess.run(['xdotool','type','--clearmodifiers','--',str(path)],check=True,timeout=5)
    wait(lambda:str(path) in text(),10)
    click('Open')
