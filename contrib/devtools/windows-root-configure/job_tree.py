"""Contain this ephemeral runner and descendants in a non-breakaway Windows job.

The handle deliberately lives until interpreter/process exit. KILL_ON_JOB_CLOSE
then also covers error paths. No peer/agent ancestor is assigned to this job.
"""
import ctypes as c
from ctypes import wintypes as w


class BasicLimits(c.Structure):
    _fields_ = [('process_time', c.c_int64), ('job_time', c.c_int64),
                ('flags', w.DWORD), ('min_ws', c.c_size_t), ('max_ws', c.c_size_t),
                ('active_limit', w.DWORD), ('affinity', c.c_size_t),
                ('priority', w.DWORD), ('scheduling', w.DWORD)]


class IoCounters(c.Structure):
    _fields_ = [(x, c.c_uint64) for x in ['ro', 'wo', 'other', 'rb', 'wb', 'otherb']]


class ExtendedLimits(c.Structure):
    _fields_ = [('basic', BasicLimits), ('io', IoCounters),
                ('process_memory', c.c_size_t), ('job_memory', c.c_size_t),
                ('peak_process_memory', c.c_size_t), ('peak_job_memory', c.c_size_t)]


class Accounting(c.Structure):
    _fields_ = [(x, c.c_int64) for x in ['user', 'kernel', 'period_user', 'period_kernel']] + [
        (x, w.DWORD) for x in ['page_faults', 'total_processes', 'active_processes', 'terminated']]


class ProcessTree:
    def __init__(self):
        assert c.sizeof(c.c_void_p) == 8
        assert c.sizeof(ExtendedLimits) == 144 and c.sizeof(Accounting) == 48
        self.k = c.WinDLL('kernel32', use_last_error=True)
        self.k.CreateJobObjectW.argtypes = [c.c_void_p, w.LPCWSTR]
        self.k.CreateJobObjectW.restype = w.HANDLE
        self.k.SetInformationJobObject.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD]
        self.k.SetInformationJobObject.restype = w.BOOL
        self.k.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        self.k.AssignProcessToJobObject.restype = w.BOOL
        self.k.GetCurrentProcess.restype = w.HANDLE
        self.k.QueryInformationJobObject.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD, c.c_void_p]
        self.k.QueryInformationJobObject.restype = w.BOOL
        self.handle = self.k.CreateJobObjectW(None, None)
        if not self.handle: raise c.WinError(c.get_last_error())
        limits = ExtendedLimits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE; no breakaway.
        if not self.k.SetInformationJobObject(self.handle, 9, c.byref(limits), c.sizeof(limits)):
            raise c.WinError(c.get_last_error())
        if not self.k.AssignProcessToJobObject(self.handle, self.k.GetCurrentProcess()):
            raise c.WinError(c.get_last_error())
        assert self.active() == 1

    def active(self):
        info = Accounting()
        if not self.k.QueryInformationJobObject(self.handle, 1, c.byref(info), c.sizeof(info), None):
            raise c.WinError(c.get_last_error())
        return info.active_processes
