"""Validate the recorded checkpoints from the HTTPS recovery fixture."""
import json
import sys
from pathlib import Path


def validate(result):
    required = {
        "real_minio", "trusted_tls", "healthy_bytes_match", "first_piece_match",
        "partial_export_refused", "retry_materialized_match", "restart_materialized_match",
        "retry_bytes_match", "restart_bytes_match", "saved_prefix_reused",
    }
    missing = sorted(name for name in required if result.get(name) is not True)
    if missing:
        raise ValueError(f"Missing or failing checks: {', '.join(missing)}")
    timing = result["timeout_window"]
    if not timing["piece_0_served"] <= timing["piece_1_wait_started"] < timing["rpc_returned"]:
        raise ValueError("Piece and timeout events arrived out of order")
    if not 4.5 <= timing["rpc_returned"] - timing["piece_1_wait_started"] < 8:
        raise ValueError("RPC did not fail within the TLS read-timeout window")
    if "s3 https read timed out" not in result["cloud_error"].lower():
        raise ValueError("BTX did not report an S3 HTTPS read timeout")
    if result["retry_cursor"] is not None or result["restart_cursor"] is not None:
        raise ValueError("Completed recovery left a cursor")
    if result["phase"] != "RECOVERED_BYTES_AND_RESTART":
        raise ValueError("The fixture did not reach its final phase")


if __name__ == "__main__":
    validate(json.loads(Path(sys.argv[1]).read_text()))
    print("All HTTPS recovery checkpoints verified.")
