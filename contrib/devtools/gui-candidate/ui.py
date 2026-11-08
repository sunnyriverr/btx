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
    matches = []
    for n in controls():
        try:
            t = n.queryEditableText()
            if '127.0.0.1' in n.queryText().getText(0, -1):
                matches.append(t)
        except Exception:
            pass
    if len(matches) != 1:
        raise TimeoutError('Endpoint field not uniquely accessible')
    matches[0].setTextContents(value)

def file_path(path):
    # Standard GTK location entry, after independently observing the chooser title.
    subprocess.run(['xdotool', 'key', '--clearmodifiers', 'ctrl+l'], check=True, timeout=5)
    subprocess.run(['xdotool', 'type', '--clearmodifiers', '--', str(path)], check=True, timeout=5)
    subprocess.run(['xdotool', 'key', '--clearmodifiers', 'Return'], check=True, timeout=5)
