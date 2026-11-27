#include <matmul/matmul_v4_rc_stage3_bounded_semantic_codec.h>
#include <matmul/matmul_v4_rc_stage3_composition.h>
#include <matmul/matmul_v4_rc_fri_ext3_alg.h>

#include <algorithm>
#include <array>
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>

namespace {

namespace codec =
    matmul::v4::rc::bounded_semantic_codec;
namespace rc = matmul::v4::rc;

uint256 H(uint8_t value)
{
    std::array<unsigned char, 32> bytes{};
    bytes.fill(value);
    return uint256{
        Span<const unsigned char>{
            bytes.data(), bytes.size()}};
}

rc::RCStage3SuccinctProof Statement()
{
    rc::RCStage3SuccinctProof out;
    out.statement =
        rc::RCStage3StatementKind::Composed;
    out.public_inputs.height = 31;
    out.public_inputs.n_bits = 0x207fffffU;
    out.public_inputs.episode_profile = 2;
    out.public_inputs.coupled_profile = 4;
    out.public_inputs.transcript_version =
        rc::ENC_RC_V4;
    out.public_inputs.program_consensus_pin
        .recursive_alg_hash_root = H(0x11);
    out.public_inputs.program_consensus_pin
        .external_sha256d_audit_root = H(0x12);
    out.public_inputs.program_consensus_pin
        .registry_binding = H(0x13);
    out.public_inputs.header_commitment = H(0x21);
    out.public_inputs.params_commitment = H(0x22);
    out.public_inputs.target = H(0x23);
    out.public_inputs.sigma = H(0x24);
    out.public_inputs.episode_digest = H(0x25);
    out.public_inputs.coupled_digest = H(0x26);
    const auto roles =
        rc::RequiredRCStage3RelationRoles(
            out.statement);
    for (uint32_t i = 0;
         i < roles.size(); ++i) {
        out.commitments.push_back(
            {roles[i],
             H(static_cast<uint8_t>(
                 0x40 + i))});
        out.sections.push_back(
            {roles[i],
             {static_cast<uint8_t>(i),
              0xa5, 0x5a}});
    }
    out.public_inputs.final_digest =
        rc::ComputeRCStage3FinalDigest(out);
    out.public_inputs.transcript_commitment =
        rc::ComputeRCStage3TranscriptCommitment(
            out);
    return out;
}

} // namespace

int main(int argc, char** argv)
{
    if (argc < 2 || argc > 3) return 1;
    codec::EnvelopeV1 fixture;
    fixture.statement = Statement();
    fixture.composition.episode.gemm.collection_commitment = H(0x71);
    fixture.composition.coupled.gemm.product_commitment = H(0x72);
    auto& edge = fixture.composition.episode.tile_tree_hash_ctl.edges.emplace_back();
    auto& producer = edge.producer_proof.batch;
    auto& consumer = edge.consumer_proof.batch;
    producer.pow_grind_nonce = 0x0102030405060708ULL;
    producer.n_coeffs = 31;
    producer.column_len = {3, 7};
    producer.fold_layers.emplace_back().n_leaves = 11;
    producer.fold_challenges.push_back({13, 17, 19});
    producer.queries.emplace_back().index = 23;
    producer.queries.front().group_rows.emplace_back().values.push_back({29, 31, 37});
    consumer.pow_grind_nonce = 0x1122334455667788ULL;
    consumer.n_coeffs = 41;
    consumer.column_len = {43};
    consumer.fold_challenges.push_back({47, 53, 59});
    consumer.queries.emplace_back().index = 61;
    std::string why;
    std::vector<unsigned char> bytes;
    codec::SizeReportV1 report;
    if (!codec::SerializeEnvelopeV1(fixture, bytes, &report, &why) ||
        !report.direct_codec_fit || !report.consensus_payload_fit ||
        report.envelope_bytes != bytes.size() || report.episode_bytes == 0 || report.coupled_bytes == 0) {
        std::cerr << why << "\n";
        return 2;
    }
    if (argc == 3) {
        std::ifstream peer(argv[2], std::ios::binary);
        if (!peer) return 3;
        const std::vector<unsigned char> peer_bytes{std::istreambuf_iterator<char>(peer), {}};
        if (peer_bytes != bytes) return 4;
        bytes = peer_bytes;
    }
    const auto decoded = codec::DeserializeEnvelopeV1(bytes, &why);
    if (!decoded || decoded->statement != fixture.statement ||
        decoded->composition.episode.gemm.collection_commitment != H(0x71) ||
        decoded->composition.coupled.gemm.product_commitment != H(0x72)) return 5;
    const auto& edges = decoded->composition.episode.tile_tree_hash_ctl.edges;
    if (edges.size() != 1) return 6;
    const auto& p = edges[0].producer_proof.batch;
    const auto& c = edges[0].consumer_proof.batch;
    const auto same_fields = [](const auto& left, const auto& right) {
        return std::equal(left.begin(), left.end(), right.begin(), right.end(),
                          [](const auto& a, const auto& b) { return rc::gkr_field::Eq(a, b); });
    };
    if (p.pow_grind_nonce != producer.pow_grind_nonce || p.n_coeffs != 31 ||
        p.column_len != producer.column_len || p.fold_layers.size() != 1 ||
        p.fold_layers[0].n_leaves != 11 || !same_fields(p.fold_challenges, producer.fold_challenges) ||
        p.queries.size() != 1 || p.queries[0].index != 23 ||
        p.queries[0].group_rows.size() != 1 ||
        !same_fields(p.queries[0].group_rows[0].values, producer.queries[0].group_rows[0].values) ||
        c.pow_grind_nonce != consumer.pow_grind_nonce || c.n_coeffs != 41 ||
        c.column_len != consumer.column_len || !same_fields(c.fold_challenges, consumer.fold_challenges) ||
        c.queries.size() != 1 || c.queries[0].index != 61) return 7;
    auto invalid = bytes;
    invalid[6] = 1;
    if (codec::DeserializeEnvelopeV1(invalid, &why)) return 8;
    invalid = bytes;
    invalid.push_back(0);
    if (codec::DeserializeEnvelopeV1(invalid, &why)) return 9;
    invalid = bytes;
    invalid.pop_back();
    if (codec::DeserializeEnvelopeV1(invalid, &why)) return 10;
    std::ofstream out(argv[1], std::ios::binary);
    if (!out.write(reinterpret_cast<const char*>(bytes.data()), bytes.size())) return 11;
    std::cout << "V1 bytes " << bytes.size() << ", episode " << report.episode_bytes
              << ", coupled " << report.coupled_bytes
              << ", populated FRI fields and refusal controls passed\n";
}
