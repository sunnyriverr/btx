"""Exercise the actual rescan status propagation with controlled scan outcomes."""
import sys
from pathlib import Path
import subprocess
import tempfile

def section(s,a,b):
    return s[s.index(a):s.index(b,s.index(a))]

with tempfile.TemporaryDirectory(prefix="btx-review-rescan-") as name:
    tmp = Path(name)
    product = Path(sys.argv[1])
    candidate = sys.argv[2] == 'candidate'
    rpc_start = "                bool interrupted = false;" if candidate else "                const int64_t scanned_time = pwallet->RescanFromTime(0"
    rpc = section((product/"src/wallet/rpc/bcp1.cpp").read_text(), rpc_start, "            UniValue o(UniValue::VOBJ);")
    wallet = (product/"src/wallet/wallet.cpp").read_text()
    flags = (product/"src/wallet/wallet.h").read_text()
    abort_method = next(line for line in flags.splitlines() if "bool IsAbortingRescan() const" in line)
    time_wrapper = section(wallet,"int64_t CWallet::RescanFromTime(","/**\n * Scan the block chain")
    tail = section(wallet,'    if (fAbortRescan) {\n        WalletLogPrintf("Rescan aborted','bool CWallet::SubmitTxMemoryPoolAndRelay')
    source = r"""
#include <cassert>
#include <cstdint>
#include <iostream>
#include <optional>
#include <string>
#define WalletLogPrintf(...) ((void)0)
#define WITH_LOCK(m, statement) ([&] { statement; }())
#define CHECK_NONFATAL(expr) assert(expr)
constexpr int TIMESTAMP_WINDOW=7200, RPC_MISC_ERROR=-1, RPC_WALLET_ERROR=-4;
int JSONRPCError(int code, const char*) { return code; }
using uint256=int;
int SaturatingIntFromInt64(int64_t value) { return static_cast<int>(value); }
struct FoundBlock {
    int64_t* time{};
    FoundBlock& hash(int&) { return *this; }
    FoundBlock& height(int&) { return *this; }
    FoundBlock& maxTime(int64_t& val) { time=&val; return *this; }
};
struct Chain {
    bool stopping{};
    bool shutdownRequested() const { return stopping; }
    bool findFirstBlockWithTimeAndHeight(int64_t,int,FoundBlock) { return true; }
    bool findBlock(int,FoundBlock block) { *block.time=123; return true; }
};
struct WalletRescanReserver {};
struct CWallet {
    struct ScanResult {
        enum Status { SUCCESS, FAILURE, USER_ABORT } status=SUCCESS;
        int last_failed_block{};
    };
    Chain node;
    bool fAbortRescan{};
    bool failure{};
    Chain& chain() { return node; }
    int GetLastBlockHeight() const { return 10; }
    // ABORT_METHOD
    int64_t RescanFromTime(int64_t,const WalletRescanReserver&,bool /* OUT_PARAM */);
    ScanResult ScanForWalletTransactions(int,int,std::optional<int>,const WalletRescanReserver&,bool,bool)
    {
        ScanResult result;
        if (failure) result.status=ScanResult::FAILURE;
        // SCAN_TAIL
    int ImportResult()
    {
        auto* pwallet=this;
        WalletRescanReserver reserver;
        if (true) {
            // RPC_BRANCH
        return 0;
    }
};
// TIME_WRAPPER
int main()
{
    CWallet wallet;
    const auto test = [&](const std::string& mode,int expected) {
        int actual=0;
        try { actual=wallet.ImportResult(); } catch(int error) { actual=error; }
        assert(actual==expected);
        std::cout << mode << " result=" << actual << '\n';
    };
    test("complete",0);
    wallet.failure=true;
    test("unreadable_block",-4);
    wallet.failure=false;
    wallet.fAbortRescan=true;
    test("user_abort",-1);
    wallet.fAbortRescan=false;
    wallet.node.stopping=true;
    test("node_shutdown", EXPECTED_SHUTDOWN);
}
"""
    cpp=tmp/"probe.cpp"
    cpp.write_text(source.replace("/* OUT_PARAM */", ",bool* = nullptr" if candidate else "").replace("EXPECTED_SHUTDOWN", "-1" if candidate else "0").replace("// ABORT_METHOD",abort_method).replace("// SCAN_TAIL",tail)
                   .replace("// TIME_WRAPPER",time_wrapper).replace("// RPC_BRANCH",rpc))
    exe=tmp/"probe"
    subprocess.run(["c++","-std=c++20",cpp,"-o",exe],check=True)
    subprocess.run([exe],check=True,timeout=10)
