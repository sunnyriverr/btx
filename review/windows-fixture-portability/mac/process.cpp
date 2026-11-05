#include <test/util/process.h>
#include <cassert>
#include <type_traits>
int main() {
    static_assert(std::is_same_v<decltype(test::ProcessId()), decltype(::getpid())>);
    assert(test::ProcessId() > 0);
    assert(test::ProcessId() == ::getpid());
}
