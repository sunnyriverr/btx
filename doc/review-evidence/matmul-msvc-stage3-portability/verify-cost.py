"""Run both exact CheckedCost bodies with synthetic width inputs on macOS."""
import hashlib
from pathlib import Path
import re
import subprocess

root = Path(__file__).resolve().parent
source = root.parent / "focused-source/src"
build = root / "build"
records = root / "records"
name = "matmul_v4_rc_stage3_relation_local_sharding"
header = (source / f"matmul/{name}.h").read_text()
constants = "\n".join(line for line in header.splitlines()
                      if re.search(r"kRelationLocal(ShardQueries|Fp3Bytes)V1 =",line))
assert len(constants.splitlines()) == 2
prefix = r"""
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
"""
suffix = r"""
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
"""
fixtures = {}
for label, tree in (("stock", source), ("candidate", root / "candidate-src/src")):
    product = (tree / f"matmul/{name}.cpp").read_text()
    body = product[product.index("bool CheckedCost("):product.index("\nstd::pair<uint32_t, uint32_t>")]
    fixtures[label] = records / f"{label}-cost-fixture.cpp"
    fixtures[label].write_text(prefix + constants + "\n" + body + suffix)
    print(label, "function SHA-256", hashlib.sha256(body.encode()).hexdigest(), flush=True)
outputs = []
for label, version, extra in (("stock-native", "stock", []), ("candidate-native", "candidate", []),
                              ("candidate-portable", "candidate", ["-U__SIZEOF_INT128__"])):
    binary = build / label
    flags = ["clang++", "-std=c++20", "-O1", "-g0", "-I", str(source), *extra]
    subprocess.run([*flags, str(fixtures[version]), "-o", str(binary)], check=True, timeout=30)
    output = subprocess.check_output([str(binary)], timeout=10)
    (records / f"{label}.log").write_bytes(output)
    outputs.append(output)
assert outputs[0] == outputs[1] == outputs[2]
print(outputs[0].decode(), end="")
