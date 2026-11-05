// Diagnostic controller for one owned, unchanged test child. No product writes.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <dbghelp.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <cstdint>
#include <chrono>
#include <cstring>
#include <iterator>
#include <algorithm>
#include <cctype>

static std::string utf8(const std::wstring& s) {
    if (s.empty()) return {};
    const int n = WideCharToMultiByte(CP_UTF8, 0, s.data(), (int)s.size(), nullptr, 0, nullptr, nullptr);
    std::string v(n, '\0');
    WideCharToMultiByte(CP_UTF8, 0, s.data(), (int)s.size(), v.data(), n, nullptr, nullptr);
    return v;
}
static std::wstring path_for(HANDLE file) {
    if (!file || file == INVALID_HANDLE_VALUE) return {};
    std::vector<wchar_t> b(32768);
    DWORD n = GetFinalPathNameByHandleW(file, b.data(), (DWORD)b.size(), FILE_NAME_NORMALIZED);
    return n && n < b.size() ? std::wstring(b.data(), n) : std::wstring{};
}
static void frame(std::ofstream& out, HANDLE proc, unsigned i, DWORD64 pc) {
    alignas(SYMBOL_INFO) unsigned char buf[sizeof(SYMBOL_INFO) + MAX_SYM_NAME]{};
    auto* sym = reinterpret_cast<SYMBOL_INFO*>(buf);
    sym->SizeOfStruct = sizeof(SYMBOL_INFO); sym->MaxNameLen = MAX_SYM_NAME;
    DWORD64 displacement = 0;
    bool found = SymFromAddr(proc, pc, &displacement, sym) != FALSE;
    out << "FRAME\t" << std::dec << i << '\t' << std::hex << pc << '\t'
        << SymGetModuleBase64(proc, pc) << '\t' << (found ? sym->Name : "?") << '\t'
        << displacement << '\n';
}
static void stack(std::ofstream& out, HANDLE proc, DWORD tid) {
    HANDLE thread = OpenThread(THREAD_GET_CONTEXT | THREAD_QUERY_INFORMATION, FALSE, tid);
    if (!thread) { out << "STACK_ERROR\tOpenThread\t" << GetLastError() << '\n'; return; }
    CONTEXT ctx{}; ctx.ContextFlags = CONTEXT_FULL;
    if (!GetThreadContext(thread, &ctx)) {
        out << "STACK_ERROR\tGetThreadContext\t" << GetLastError() << '\n'; CloseHandle(thread); return;
    }
    out << "CONTEXT\t" << std::hex << ctx.Rip << '\t' << ctx.Rsp << '\t' << ctx.Rbp
        << '\t' << ctx.Rcx << '\t' << ctx.Rdx << '\t' << ctx.R8 << '\t' << ctx.R9 << '\n';
    STACKFRAME64 sf{};
    sf.AddrPC.Offset = ctx.Rip; sf.AddrPC.Mode = AddrModeFlat;
    sf.AddrFrame.Offset = ctx.Rbp; sf.AddrFrame.Mode = AddrModeFlat;
    sf.AddrStack.Offset = ctx.Rsp; sf.AddrStack.Mode = AddrModeFlat;
    frame(out, proc, 0, ctx.Rip);
    DWORD64 previous = ctx.Rip;
    for (unsigned i = 1; i < 48; ++i) {
        if (!StackWalk64(IMAGE_FILE_MACHINE_AMD64, proc, thread, &sf, &ctx, nullptr,
                         SymFunctionTableAccess64, SymGetModuleBase64, nullptr)) break;
        if (!sf.AddrPC.Offset) break;
        if (sf.AddrPC.Offset == previous) { if (i == 1) continue; break; }
        frame(out, proc, i, sf.AddrPC.Offset); previous = sf.AddrPC.Offset;
    }
    CloseHandle(thread);
}
int wmain(int argc, wchar_t** argv) {
    if (argc != 4) return 2;
    const std::filesystem::path output(argv[3]);
    std::ifstream in(std::filesystem::path(argv[2]), std::ios::binary);
    std::vector<char> bytes((std::istreambuf_iterator<char>(in)), {});
    if (in.bad() || bytes.empty() || bytes.size() % sizeof(wchar_t)) return 3;
    std::wstring command(bytes.size() / sizeof(wchar_t), L'\0');
    memcpy(command.data(), bytes.data(), bytes.size()); command.push_back(L'\0');
    std::ofstream out(output / "trace.tsv");
    SECURITY_ATTRIBUTES sa{sizeof(sa), nullptr, TRUE};
    HANDLE log = CreateFileW((output / "child.log").c_str(), GENERIC_WRITE,
                             FILE_SHARE_READ, &sa, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (log == INVALID_HANDLE_VALUE) return 4;
    STARTUPINFOW si{}; si.cb = sizeof(si); si.dwFlags = STARTF_USESTDHANDLES;
    si.hStdOutput = log; si.hStdError = log;
    si.hStdInput = CreateFileW(L"NUL", GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE,
                              &sa, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    PROCESS_INFORMATION pi{};
    SetEnvironmentVariableW(L"_NT_SYMBOL_PATH", L"");
    SetEnvironmentVariableW(L"_NT_ALT_SYMBOL_PATH", L"");
    if (!CreateProcessW(argv[1], command.data(), nullptr, nullptr, TRUE,
                        DEBUG_ONLY_THIS_PROCESS, nullptr, nullptr, &si, &pi)) {
        out << "CREATE_ERROR\t" << GetLastError() << '\n'; CloseHandle(log); CloseHandle(si.hStdInput); return 5;
    }
    if (!DebugSetProcessKillOnExit(TRUE)) { TerminateProcess(pi.hProcess, 0xdead); return 7; }
    out << "CHILD\t" << std::dec << pi.dwProcessId << '\t' << utf8(argv[1]) << '\n'; out.flush();
    // All DbgHelp operations occur on this one debugger thread. No symbol server.
    SymSetOptions(SYMOPT_UNDNAME | SYMOPT_DEFERRED_LOADS | SYMOPT_FAIL_CRITICAL_ERRORS | SYMOPT_NO_PROMPTS);
    BOOL initialized = SymInitialize(pi.hProcess, "", FALSE);
    out << "SYMINIT\t" << initialized << '\t' << GetLastError() << '\n';
    const auto start = std::chrono::steady_clock::now();
    bool done = false, timeout = false, initial_break = false;
    DWORD child_exit = STILL_ACTIVE; unsigned exceptions = 0;
    while (!done) {
        if (std::chrono::steady_clock::now() - start > std::chrono::seconds(80)) {
            timeout = true; out << "TIMEOUT\n"; TerminateProcess(pi.hProcess, 0xdead); break;
        }
        DEBUG_EVENT ev{};
        if (!WaitForDebugEvent(&ev, 1000)) {
            if (GetLastError() == ERROR_SEM_TIMEOUT) continue;
            out << "WAIT_ERROR\t" << GetLastError() << '\n'; TerminateProcess(pi.hProcess, 0xdead); timeout = true; break;
        }
        DWORD continuation = DBG_CONTINUE;
        switch (ev.dwDebugEventCode) {
        case CREATE_PROCESS_DEBUG_EVENT: {
            auto& x = ev.u.CreateProcessInfo;
            auto name = path_for(x.hFile);
            DWORD64 loaded = SymLoadModuleExW(pi.hProcess, x.hFile, name.c_str(), nullptr,
                                  reinterpret_cast<DWORD64>(x.lpBaseOfImage), 0, nullptr, 0);
            out << "MAIN\t" << std::hex << reinterpret_cast<DWORD64>(x.lpBaseOfImage)
                << '\t' << loaded << '\t' << utf8(name) << '\n';
            if (x.hFile) CloseHandle(x.hFile); break;
        }
        case LOAD_DLL_DEBUG_EVENT: {
            auto& x = ev.u.LoadDll; auto name = path_for(x.hFile);
            auto loaded = SymLoadModuleExW(pi.hProcess, x.hFile, name.empty() ? nullptr : name.c_str(),
                            nullptr, reinterpret_cast<DWORD64>(x.lpBaseOfDll), 0, nullptr, 0);
            out << "MODULE\t" << std::hex << reinterpret_cast<DWORD64>(x.lpBaseOfDll)
                << '\t' << loaded << '\t' << utf8(name) << '\n';
            if (x.hFile) CloseHandle(x.hFile); break;
        }
        case UNLOAD_DLL_DEBUG_EVENT:
            SymUnloadModule64(pi.hProcess, reinterpret_cast<DWORD64>(ev.u.UnloadDll.lpBaseOfDll)); break;
        case EXCEPTION_DEBUG_EVENT: {
            auto& x = ev.u.Exception; auto& r = x.ExceptionRecord;
            IMAGEHLP_MODULE64 module{}; module.SizeOfStruct = sizeof(module);
            bool module_ok = SymGetModuleInfo64(pi.hProcess, reinterpret_cast<DWORD64>(r.ExceptionAddress), &module) != FALSE;
            std::string module_name = module_ok ? module.ModuleName : "";
            std::transform(module_name.begin(), module_name.end(), module_name.begin(), [](unsigned char c) { return (char)std::tolower(c); });
            if (r.ExceptionCode == EXCEPTION_BREAKPOINT && x.dwFirstChance && !initial_break &&
                ev.dwThreadId == pi.dwThreadId && module_name == "ntdll") {
                initial_break = true;
                out << "LOADER_BREAK\t" << std::hex << reinterpret_cast<DWORD64>(r.ExceptionAddress)
                    << '\t' << module_name << '\t' << std::dec << ev.dwThreadId << '\n'; break;
            }
            out << "EXCEPTION\t" << std::dec << ++exceptions << '\t' << ev.dwThreadId
                << '\t' << x.dwFirstChance << '\t' << std::hex << r.ExceptionCode
                << '\t' << reinterpret_cast<DWORD64>(r.ExceptionAddress);
            for (DWORD i = 0; i < r.NumberParameters; ++i) out << '\t' << r.ExceptionInformation[i];
            out << '\n';
            if (r.ExceptionCode == EXCEPTION_ILLEGAL_INSTRUCTION || r.ExceptionCode == EXCEPTION_ACCESS_VIOLATION ||
                r.ExceptionCode == EXCEPTION_BREAKPOINT || r.ExceptionCode == 0xc0000409 || !x.dwFirstChance) {
                stack(out, pi.hProcess, ev.dwThreadId);
            }
            continuation = DBG_EXCEPTION_NOT_HANDLED; break;
        }
        case EXIT_PROCESS_DEBUG_EVENT:
            child_exit = ev.u.ExitProcess.dwExitCode; done = true;
            out << "EXIT\t" << std::hex << child_exit << '\n'; SymCleanup(pi.hProcess); break;
        default: break;
        }
        out.flush();
        if (!ContinueDebugEvent(ev.dwProcessId, ev.dwThreadId, continuation)) {
            out << "CONTINUE_ERROR\t" << GetLastError() << '\n'; timeout = true;
            TerminateProcess(pi.hProcess, 0xdead); break;
        }
    }
    if (timeout) { WaitForSingleObject(pi.hProcess, 10000); if (initialized) SymCleanup(pi.hProcess); }
    CloseHandle(pi.hThread); CloseHandle(pi.hProcess); CloseHandle(log); CloseHandle(si.hStdInput);
    out << "COMPLETE\t" << (done && !timeout) << '\t' << exceptions << '\n';
    return done && !timeout ? 0 : 6;
}
