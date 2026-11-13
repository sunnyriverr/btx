"""Report exception classes and codes only from the maker's native worker."""
from pathlib import Path
import os
import re
import sys

import hashlib
mode = os.environ["SWAPNET_VARIANT"]
source, is_package = _sources["swapnet.embedded"]
assert hashlib.sha256(source.encode()).hexdigest() == "8506f4e3f1dd16fe76522c68fed2adb80cde2a4b08998e0d6ef3b191c8ba9b8f"
if mode == "candidate":
    source = Path("embedded_candidate.py").read_text()
    _sources["swapnet.embedded"] = (source, is_package)
print("SWAPNET_DIAGNOSTIC_TRACE_ACTIVE", mode, hashlib.sha256(source.encode()).hexdigest(),
      file=sys.stderr, flush=True)
targets = {"receive_proposal", "receive_agreement", "watch_terms", "_call", "prepare_funding", "prepare_refund"}


def events(frame, event, arg):
    if event == "exception":
        cls, error, _ = arg
        code = getattr(error, "code", "")
        if not isinstance(code, str) or not re.fullmatch(r"[A-Z_]{1,40}", code):
            code = "-"
        function = frame.f_code.co_name
        print(f"SWAPNET_DIAGNOSTIC {function}:{frame.f_lineno} {cls.__name__} {code}",
              file=sys.stderr, flush=True)
        if function == "watch_terms" and code == "WATCH_FAILED":
            fields = frame.f_locals
            descriptor = fields["checked"]
            assert re.fullmatch(r"addr\(bcrt1[a-z0-9]+\)#[a-z0-9]{8}", descriptor)
            path = Path(os.environ["SWAPNET_DIAGNOSTIC_DESCRIPTOR"])
            if not path.exists():
                with path.open("x") as stream:
                    stream.write(descriptor)
    return events


def trace(frame, event, arg):
    if event == "call" and frame.f_code.co_filename.startswith("<btxd-frozen>/") and frame.f_code.co_name in targets:
        return events
    return None


sys.settrace(trace)
