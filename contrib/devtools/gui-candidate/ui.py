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
    def matches():
        found=[]
        for n in controls():
            try:
                edit=n.queryEditableText()
                label=n.name or ''
                for relation in n.getRelationSet():
                    if relation.getRelationType()==pyatspi.RELATION_LABELLED_BY:
                        label+=' '+ ' '.join(relation.getTarget(i).name or '' for i in range(relation.getNTargets()))
                if 'Loopback endpoint' in label:
                    found.append((n,edit))
            except Exception:
                pass
        return found
    wait(lambda:len(matches())==1,15)
    n,edit=matches()[0]
    if not edit.setTextContents(value):
        raise TimeoutError('Endpoint edit unavailable')
    wait(lambda:n.queryText().getText(0,-1)==value,5)

def file_path(path):
    # Standard GTK location entry, after independently observing the chooser title.
    subprocess.run(['xdotool', 'key', '--clearmodifiers', 'ctrl+l'], check=True, timeout=5)
    subprocess.run(['xdotool', 'type', '--clearmodifiers', '--', str(path)], check=True, timeout=5)
    subprocess.run(['xdotool', 'key', '--clearmodifiers', 'Return'], check=True, timeout=5)
