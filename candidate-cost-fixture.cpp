
#include <compat/wide128.h>
#include <cstdint>
#include <iostream>
#include <limits>
#include <vector>

// Supply size() directly so the overflow boundary does not allocate large arrays.
struct Columns {
    size_t width;
    size_t size() const { return width; }
};
struct RelationLocalShardV1 { Columns global_columns; };
struct RelationLocalCostModelV1 {
    uint32_t trace_rows;
    uint64_t sharded_trace_cells{101};
    uint64_t sharded_trace_bytes{102};
    uint64_t direct_opening_value_bytes_lower_bound{103};
};
inline constexpr uint32_t kRelationLocalShardQueriesV1 = 192;
inline constexpr uint32_t kRelationLocalFp3BytesV1 = 24;
bool CheckedCost(
    RelationLocalCostModelV1& cost,
    const std::vector<RelationLocalShardV1>& shards)
{
    btx::U128 cells = 0;
    btx::U128 openings = 0;
    for (const auto& shard : shards) {
        cells +=
            btx::U128{shard.global_columns.size()} *
            cost.trace_rows;
        openings +=
            btx::U128{
                shard.global_columns.size() + 1} *
            kRelationLocalShardQueriesV1 * 2 *
            kRelationLocalFp3BytesV1;
    }
    if (cells >
            std::numeric_limits<uint64_t>::max() ||
        openings >
            std::numeric_limits<uint64_t>::max() ||
        cells * kRelationLocalFp3BytesV1 >
            std::numeric_limits<uint64_t>::max()) {
        return false;
    }
    cost.sharded_trace_cells =
        static_cast<uint64_t>(cells);
    cost.sharded_trace_bytes =
        static_cast<uint64_t>(
            cells * kRelationLocalFp3BytesV1);
    cost.direct_opening_value_bytes_lower_bound =
        static_cast<uint64_t>(openings);
    return true;
}

int main()
{
    constexpr uint64_t max = std::numeric_limits<uint64_t>::max();
    constexpr uint64_t trace_rows = uint64_t{1} << 31;
    constexpr uint64_t trace_width = max / (24 * trace_rows);
    constexpr uint64_t opening_width = max / 9216;
    struct Case {
        const char* name;
        uint32_t rows;
        std::vector<RelationLocalShardV1> shards;
        bool valid;
        uint64_t cells, bytes, openings;
    };
    const std::vector<Case> cases{
        {"normal", 8, {{{2}}, {{2}}, {{2}}, {{2}}}, true, 64, 1536, 110592},
        {"empty", 8, {}, true, 0, 0, 0},
        {"trace bytes within limit", trace_rows, {{{trace_width}}}, true,
            trace_width * trace_rows, trace_width * trace_rows * 24, (trace_width + 1) * 9216},
        {"trace bytes above limit", trace_rows, {{{trace_width + 1}}}, false, 101, 102, 103},
        {"trace cells above limit", trace_rows, {{{uint64_t{1} << 33}}}, false, 101, 102, 103},
        {"trace accumulation carries", trace_rows, {{{(uint64_t{1} << 33) - 1}}, {{1}}},
            false, 101, 102, 103},
        {"opening bytes within limit", 0, {{{opening_width - 1}}}, true, 0, 0, opening_width * 9216},
        {"opening bytes above limit", 0, {{{opening_width}}}, false, 101, 102, 103},
        {"opening accumulation carries", 0, {{{opening_width - 1}}, {{0}}}, false, 101, 102, 103},
    };
    for (const auto& entry : cases) {
        RelationLocalCostModelV1 cost{entry.rows};
        const bool valid = CheckedCost(cost, entry.shards);
        if (valid != entry.valid || cost.sharded_trace_cells != entry.cells ||
            cost.sharded_trace_bytes != entry.bytes ||
            cost.direct_opening_value_bytes_lower_bound != entry.openings) {
            std::cerr << "Unexpected result in " << entry.name << "\n";
            return 1;
        }
        std::cout << entry.name << " " << valid << " " << cost.sharded_trace_cells << " "
                  << cost.sharded_trace_bytes << " " << cost.direct_opening_value_bytes_lower_bound << "\n";
    }
    const auto cap = btx::U128{max};
    if (btx::U128{max / 24} * 24 > cap || btx::U128{max / 24 + 1} * 24 <= cap) return 2;
    if (btx::U128{max} + 1 <= cap || btx::U128{uint64_t{1} << 63} * 2 <= cap) return 3;
    std::cout << "Exact UINT64_MAX / 24 cutoff, add carry and multiply high limb passed\n";
}
