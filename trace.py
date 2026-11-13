"""Report exception classes and codes only from the maker's native worker."""
from pathlib import Path
import os
import re
import sys

print("SWAPNET_DIAGNOSTIC_TRACE_ACTIVE", file=sys.stderr, flush=True)
targets = {"receive_proposal", "watch_terms", "_call"}


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
