#include <modelnet/hcp.h>

#include <iostream>
#include <limits>

int main()
{
    std::cout << "stdlib_specialized=" << std::numeric_limits<__int128>::is_specialized
              << " stdlib_max_is_zero=" << (std::numeric_limits<__int128>::max() == 0) << '\n';

    struct Case {
        const char* tasks;
        const char* unit;
        int years;
        const char* upfront;
        const char* annual;
        const char* expected;
    };
    const Case cases[] = {
        {"20000000", "0.01", 3, "50000", "65000", "8166666.666666666666666666"},
        {"1", "100", 3, "50000", "65000", "816.666666666666666666"},
        {"1", "0.03", 1, "3", "0", "100"},
        {"1", "0", 1, "3", "0", nullptr},
        {"0", "0.000000000000000001", 1, "100000000000000000000", "0", nullptr},
    };
    bool matches = true;
    for (const auto& item : cases) {
        UniValue out;
        std::string err;
        if (!modelnet::Cr11Tco(item.tasks, item.unit, item.years, item.upfront, item.annual, true, true, out, err)) {
            std::cerr << err << '\n';
            return 2;
        }
        const auto& value = out["break_even_annual_tasks"];
        const bool ok = item.expected ? value.isStr() && value.get_str() == item.expected : value.isNull();
        std::cout << value.write() << " matched=" << ok << '\n';
        matches &= ok;
    }
    return matches ? 0 : 1;
}
