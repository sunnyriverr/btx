"""Track an owned session plus observed descendants across job process groups.

Do not select processes by executable name. PID identities are checked before signals.
Ninja job groups stay in the owned session; observed new-session descendants are
retained after reparenting. A child which creates a session and disappears between
snapshots is outside the observation guarantee, not silently counted as observed.
"""
import os, signal, subprocess, time

def snapshot():
    raw = subprocess.check_output(['ps', '-axo', 'pid=,ppid=,pgid=,rss=,stat=,lstart='], text=True, timeout=10)
    result = {}
    for line in raw.splitlines():
        fields = line.split()
        if len(fields) < 10:
            continue
        pid, ppid, pgid, rss = map(int, fields[:4])
        try:
            sid = os.getsid(pid)
        except ProcessLookupError:
            continue
        result[pid] = dict(pid=pid, ppid=ppid, pgid=pgid, sid=sid,
                           rss_bytes=rss * 1024, stat=fields[4], identity=' '.join(fields[5:]))
    return result

class OwnedProcesses:
    def __init__(self, proc):
        self.proc = proc
        self.sid = proc.pid  # caller must use start_new_session=True
        self.known = {}
        self.peak_rss_bytes = 0
        self.update()
        assert self.known or proc.poll() is not None, 'Live owned launch was not observable'
        # A completed short command legitimately has no live process or RSS sample.

    def update(self):
        rows = snapshot()
        chosen = {pid for pid, row in rows.items()
                  if row['sid'] == self.sid or self.known.get(pid) == row['identity']}
        while True:
            more = {pid for pid, row in rows.items() if row['ppid'] in chosen}
            if more <= chosen:
                break
            chosen |= more
        for pid in chosen:
            self.known[pid] = rows[pid]['identity']
        live = [rows[pid] for pid in sorted(chosen) if not rows[pid]['stat'].startswith('Z')]
        rss = sum(row['rss_bytes'] for row in live)
        self.peak_rss_bytes = max(self.peak_rss_bytes, rss)
        return dict(rss_bytes=rss, peak_rss_bytes=self.peak_rss_bytes, processes=live,
                    process_groups=sorted({r['pgid'] for r in live}),
                    sessions=sorted({r['sid'] for r in live}))

    def stop(self):
        for sig, grace in [(signal.SIGINT, 5), (signal.SIGTERM, 3), (signal.SIGKILL, 3)]:
            for row in reversed(self.update()['processes']):
                fresh = snapshot().get(row['pid'])
                if fresh and fresh['identity'] == row['identity']:
                    try:
                        os.kill(row['pid'], sig)
                    except ProcessLookupError:
                        pass
            end = time.monotonic() + grace
            while time.monotonic() < end:
                self.proc.poll()
                if not self.update()['processes']:
                    return self.update()
                time.sleep(.1)
        raise RuntimeError('Owned processes remain; no mutable output snapshot allowed')
