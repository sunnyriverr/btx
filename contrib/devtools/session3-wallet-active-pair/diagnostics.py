"""Bounded diagnostic hints only: never retain raw log text or wallet values."""
import os,re,stat
from pathlib import Path
from itertools import islice

# Keys and emitted values are fixed. Paths, messages, source lines and arbitrary
# exception names never leave this module.
FRAME_LIMITS={'wallet_active_pair_recovery.py':400,'test_framework.py':1400,
              'test_node.py':1300,'util.py':2000,'authproxy.py':600}
EXCEPTIONS=frozenset({'AssertionError','RuntimeError','FileNotFoundError','PermissionError',
                     'NotADirectoryError','OSError','ValueError','TypeError','KeyError',
                     'AttributeError','ImportError','ModuleNotFoundError','NoOptionError',
                     'NoSectionError','JSONDecodeError','UnicodeDecodeError',
                     'TimeoutError','ConnectionError','ConnectionRefusedError',
                     'JSONRPCException','CalledProcessError','InterruptedError'})
FRAME=re.compile(r'File "([^"\n]{1,2048})", line ([0-9]{1,6})')
EXCEPTION=re.compile(r'(?:^|\n)(?:[A-Za-z_][A-Za-z0-9_]*\.)*('+ '|'.join(sorted(EXCEPTIONS))+r')(?:\s*:|\s*(?:\n|$))')
CATEGORIES={
 'ARGUMENT_PARSER_REJECTION':('error: unrecognized arguments:','error: argument --'),
 'NODE_ARGUMENT_REJECTION':('error parsing command line arguments:','error: unknown configuration value'),
 'DYNAMIC_LOADER_FAILURE':('error while loading shared libraries:',),
 'DATADIR_LOCK_FAILURE':('cannot obtain a lock on data directory',),
 'NETWORK_BIND_FAILURE':('unable to bind to','unable to start http server'),
 'NODE_DATABASE_OPEN_FAILURE':('error opening block database',),
 'NODE_START_EXIT':('bitcoind exited with status','btxd exited with status'),
 'RPC_STARTUP_TIMEOUT':('unable to connect to bitcoind','unable to connect to btxd'),
 'PYTHON_IMPORT_FAILURE':('modulenotfounderror:','importerror:'),
}
MAX_BYTES=64*1024
MAX_STDERR_FILES=8
MAX_FRAMES=24


def exception_kind(name):
    return name if name in EXCEPTIONS else 'OtherError'


def sanitize_text(text):
    frames=[]
    for match in FRAME.finditer(text):
        path=match.group(1).replace('\\','/')
        name=path.rsplit('/',1)[-1]
        if name not in FRAME_LIMITS:continue
        if name!='wallet_active_pair_recovery.py' and not path.endswith('/test_framework/'+name):continue
        line=int(match.group(2))
        if not 1<=line<=FRAME_LIMITS[name]:continue
        frame={'file':name,'line':line}
        if frame not in frames:frames.append(frame)
        if len(frames)>=MAX_FRAMES:break
    classes=sorted({match.group(1)for match in EXCEPTION.finditer(text)})
    lower=text.lower()
    categories=sorted(k for k,needles in CATEGORIES.items()if any(n in lower for n in needles))
    return {'frames':frames,'exception_classes':classes,'categories':categories}


def bounded_read(path,root):
    # No symlinks in any selected component, no recursion, no FIFO/device read.
    relative=path.relative_to(root)
    current=root
    for component in relative.parts:
        current=current/component
        if current.is_symlink():return None,'SYMLINK_REFUSED'
    try:
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    except FileNotFoundError:return None,'ABSENT'
    except OSError:return None,'READ_UNAVAILABLE'
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):return None,'NONREGULAR_REFUSED'
        with os.fdopen(fd,'rb',closefd=False)as stream:
            if info.st_size<=MAX_BYTES:data=stream.read(MAX_BYTES)
            else:
                head=stream.read(MAX_BYTES//2)
                stream.seek(-MAX_BYTES//2,os.SEEK_END)
                data=head+b'\n'+stream.read(MAX_BYTES//2)
        return data.decode('utf-8',errors='replace'),'TRUNCATED'if info.st_size>MAX_BYTES else 'READ'
    finally:os.close(fd)


def collect_diagnostics(private):
    private=Path(private)
    result={'schema_version':1,'kind':'ALLOWLISTED_HINTS_NOT_PRODUCT_DIAGNOSIS','sources':[],
            'raw_logs_retained':False,'unknown_text_retained':False}
    selected=[('controller-output',private/'private-run.log')]
    for node in (0,1):
        directory=private/'regtest'/('node'+str(node))/'stderr'
        try:
            if any(p.is_symlink()for p in [private/'regtest',directory.parent,directory]):
                result['sources'].append({'source':'node'+str(node)+'-stderr','read_status':'SYMLINK_REFUSED'})
                continue
            if directory.is_dir():
                # Names remain private; enumeration and reads are both bounded.
                for path in islice(directory.iterdir(),MAX_STDERR_FILES):
                    selected.append(('node'+str(node)+'-stderr',path))
        except OSError:
            result['sources'].append({'source':'node'+str(node)+'-stderr','read_status':'READ_UNAVAILABLE'})
    for label,path in selected:
        try:
            text,status=bounded_read(path,private)
            entry={'source':label,'read_status':status}
            if text is not None:entry.update(sanitize_text(text))
        except Exception:
            # Never echo the exception message, path, raw input or custom name.
            entry={'source':label,'read_status':'SANITIZER_UNAVAILABLE'}
        result['sources'].append(entry)
    return result
