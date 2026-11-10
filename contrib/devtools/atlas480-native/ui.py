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

def text(root=None):
    out=[]
    for n in descendants(root) if root is not None else controls():
        try:
            out.append(n.name or '')
            role=n.getRoleName().lower()
            if 'password' in role or n.getState().contains(pyatspi.STATE_EDITABLE):
                continue  # Never serialize editable values, especially credentials.
            try:
                value=n.queryText();out.append(value.getText(0,min(value.characterCount,20000)))
            except Exception:pass
        except Exception:pass
    return '\n'.join(out)

def descendants(root):
    result=[]
    def visit(n,depth=0):
        if depth>35 or len(result)>8000:return
        try:
            if n.getState().contains(pyatspi.STATE_SHOWING):result.append(n)
            for child in n:
                if child is not None:visit(child,depth+1)
        except Exception:pass
    visit(root);return result

def nodes(root=None):return descendants(root) if root is not None else controls()

def find(predicate,root=None):
    found=[]
    for n in nodes(root):
        try:
            if predicate(n):found.append(n)
        except Exception:pass
    return found

def unique(predicate,root=None):
    found=find(predicate,root)
    if len(found)!=1:raise TimeoutError('Control not uniquely accessible')
    return found[0]

def activate(node):
    action=node.queryAction()
    if not action.nActions or not action.doAction(0):raise TimeoutError('Control action unavailable')

def button(name,root=None,prefix=False):
    return unique(lambda n:n.getRoleName() in ('push button','button','toggle button') and (n.name.startswith(name) if prefix else n.name==name),root)

def press(name,root=None,prefix=False):activate(button(name,root,prefix))

def entry(name,root=None,prefix=False):
    return unique(lambda n:n.getState().contains(pyatspi.STATE_EDITABLE) and (n.name.startswith(name) if prefix else n.name==name),root)

def type_value(node,value,private_path,secret=False):
    from pathlib import Path
    import os
    if secret and 'password' not in node.getRoleName().lower():raise RuntimeError('Secret field is not protected')
    assert node.queryComponent().grabFocus(),'Input focus refused'
    path=Path(private_path);path.write_text(value);os.chmod(path,0o600)
    try:
        subprocess.run(['xdotool','key','--clearmodifiers','ctrl+a'],check=True,timeout=5)
        subprocess.run(['xdotool','type','--clearmodifiers','--file',str(path)],check=True,timeout=5)
    finally:path.unlink()

def web_dialog(title):
    return unique(lambda n:n.getRoleName()=='dialog' and any(c.getRoleName()=='heading' and c.name==title for c in descendants(n)))

def native_dialog(title):
    matches=find(lambda n:n.getRoleName() in ('frame','dialog','alert') and title in (n.name or ''))
    frames=[n for n in matches if n.getRoleName()=='frame']
    if len(frames)==1:return frames[0]
    if len(matches)==1:return matches[0]
    raise TimeoutError('Native target dialog not uniquely observed')

def native_press(root,name):
    wanted=name.lower()
    activate(unique(lambda n:n.getRoleName() in ('push button','button') and (n.name or '').replace('_','').lower()==wanted,root))

def metadata(root=None):
    rows=[]
    for n in nodes(root):
        try:rows.append({'name':n.name or '', 'role':n.getRoleName(),'enabled':n.getState().contains(pyatspi.STATE_ENABLED),'editable':n.getState().contains(pyatspi.STATE_EDITABLE)})
        except Exception:pass
    return rows

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
        (Path(os.environ['GITHUB_WORKSPACE'])/'atlas480-native-records/endpoint-accessibility.json').write_text(json.dumps(diagnostic,indent=2)+'\n')

def file_path(path):
    # Focus the independently observed native GTK picker, not the underlying web form.
    windows=subprocess.check_output(['xdotool','search','--onlyvisible','--name',"Choose this BTX node's RPC"],text=True,timeout=5).splitlines()
    if len(windows)!=1:raise TimeoutError('Native cookie picker not uniquely visible')
    subprocess.run(['xdotool','windowactivate','--sync',windows[0]],check=True,timeout=5)
    subprocess.run(['xdotool','key','--clearmodifiers','ctrl+l'],check=True,timeout=5)
    time.sleep(.3)
    subprocess.run(['xdotool','type','--clearmodifiers','--',str(path)],check=True,timeout=5)
    wait(lambda:str(path) in text(),10)
    click('Select')
