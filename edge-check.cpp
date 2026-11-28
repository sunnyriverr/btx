#include <compat/wide128.h>

#include <cstdint>
#include <iostream>
#include <type_traits>
#include <vector>

#if !defined(_MSC_VER) || defined(__clang__) || !defined(_M_X64) || _MSC_FULL_VER != 194435230
#error This receipt requires native MSVC 19.44.35230 on x64
#endif

static_assert(std::is_same_v<btx::U128, btx::wide_detail::Unsigned128>);
static_assert(std::is_same_v<btx::I128, btx::wide_detail::Signed128>);

using U = btx::U128;
using I = btx::I128;

void emit(const char* operation, U value)
{
    std::cout << operation << ' ' << std::hex << value.hi << ' ' << value.lo << '\n';
}

void emit(const char* operation, I value)
{
    emit(operation, static_cast<U>(value));
}

void flag(const char* operation, bool value)
{
    emit(operation, U{static_cast<uint64_t>(value)});
}

int main()
{
    std::vector<U> edges;
    U word;
    while (std::cin >> std::hex >> word.hi >> word.lo) {
        edges.push_back(word);
    }
    if (!std::cin.eof() || edges.size() != 13) return 2;

    for (const U a : edges) {
        const I sa{a};
        emit("u_narrow64", U{static_cast<uint64_t>(a)});
        emit("u_narrow32", U{static_cast<uint32_t>(a)});
        emit("i_roundtrip", sa);
        emit("i_narrow64", U{static_cast<uint64_t>(static_cast<int64_t>(sa))});
        emit("i_narrow_u64", U{static_cast<uint64_t>(sa)});
        emit("i_neg", -sa);
        for (int shift = 0; shift < 128; ++shift) {
            emit("u_left", a << shift);
            emit("u_right", a >> shift);
            emit("i_left", sa << shift);
            emit("i_right", sa >> shift);
        }
        for (const U b : edges) {
            const I sb{b};
            emit("u_add", a + b);
            emit("u_sub", a - b);
            emit("u_mul", a * b);
            emit("u_and", a & b);
            emit("u_or", a | b);
            emit("u_xor", a ^ b);
            flag("u_eq", a == b);
            flag("u_lt", a < b);
            flag("u_le", a <= b);
            flag("u_gt", a > b);
            flag("u_ge", a >= b);
            emit("i_add", sa + sb);
            emit("i_sub", sa - sb);
            emit("i_mul", sa * sb);
            emit("i_and", sa & sb);
            emit("i_or", sa | sb);
            flag("i_eq", sa == sb);
            flag("i_lt", sa < sb);
            flag("i_le", sa <= sb);
            flag("i_ge", sa >= sb);
            const bool nonzero = b.hi != 0 || b.lo != 0;
            if (nonzero) {
                emit("u_div", a / b);
                emit("u_mod", a % b);
            }
            const bool signed_overflow = a.hi == (uint64_t{1} << 63) && a.lo == 0 &&
                                         b.hi == ~uint64_t{0} && b.lo == ~uint64_t{0};
            if (nonzero && !signed_overflow) {
                emit("i_div", sa / sb);
                emit("i_mod", sa % sb);
            }
        }
    }
}
