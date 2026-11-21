#include <logging.h>
#include <node/resource_governor.h>

#include <iostream>

// Logging is the only stub. The component under test is linked from its
// unchanged or patched production translation unit.
BCLog::Logger& LogInstance()
{
    static BCLog::Logger logger;
    return logger;
}

void BCLog::Logger::LogPrintStr(std::string_view, std::source_location&&,
                                BCLog::LogFlags, BCLog::Level, bool)
{
}

int main()
{
    const node::SystemSignals signals = node::SampleHostSignals();
    if (!signals.on_ac || signals.gpu.utilization_pct != 0) return 2;

    node::ResourceGovernor governor;
    governor.SetAutoSchedule(false);
    governor.SetMiningConsent(true);
    governor.Observe(signals, 1000);
    const auto permit = governor.Permit(node::GovernorJob::MINING);
    std::cout << "{\"swap_pressure\":" << std::boolalpha << signals.swap_pressure
              << ",\"memory_available_bytes\":" << signals.memory_available_bytes
              << ",\"memory_pressure\":" << static_cast<int>(signals.memory_pressure)
              << ",\"mining_allowed\":" << permit.allowed
              << ",\"pause_reason\":\"" << node::PauseReasonName(permit.reason) << "\"}\n";
}
