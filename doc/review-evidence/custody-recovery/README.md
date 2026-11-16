# Custody recovery qualification

Code commit: bfe7704578aacdd61a923acfda77c339b180d535. Base release-0.34.17 1e2f8b5f12295002334d3390c12cac0bb4ae2aff. One maintained functional test plus one runner entry; no product change.

Normal runner wallet_custody_recovery.py --descriptors PASS12s / ALL12s on Ubuntu24.04 CPU/wallet profile. Run: https://github.com/sunnyriverr/btx/actions/runs/43794753474 at workflow d1849596b2914761e9c8dc45c51296d9494b7747. Retained binaries, no rebuild; framework exit0, no selected skips. Artifact14193801937 digest and candidate inputs verified. Total47.08s, processgroup absent/private data removed, peak41295450bytes. Raw wallet/RPC logs intentionally not uploaded; machine-readable result and provenance retained.

Cases: older watch-only backup plus retained public inventory/rescan; missed chain events reconciled from orphaned cursor without node restart; retained unsigned reservations across reload/restart, disjoint allocation and cancellation preserving unrelated reservation.

First run43794093893 failed fixture setup KeyError desc before recovery assertions; corrected public-key setup was reviewed. This is not a product-failure baseline.

Limits: stable final tip, retry branch unforced; default account/deposit indices; fixture consumer, no ZMQ transport reconnect; no signing/broadcast/product-managed durable queue; no crash/powerloss/fullsuite/other-platform or production qualification. No product defect shown.

Credit JPP's maintained regression work, Numair's documented recovery/locking paths and repch1c's pool/withdrawal evidence. Existing753/755 evidence remains separately scoped.
