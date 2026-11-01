# Quota versus fixed delay — code-read answer, not a tested redesign

I agree that a per-netgroup request-admission check could avoid repeated downloads
while capacity stays unavailable. This candidate did not implement or test that
scheduler. It is the already tested bounded recovery patch: retain failure no
longer disconnects the requested-hole source, idle bypass cannot erase its1second
cooldown, and later background descendants do not refill that window during it.
A still-full store can cause another refused download after that delay.

At70e35da0, node/matmul_block_lifecycle.h Retain() lines238–274 prunes expired
entries and enforces per-source count/byte AND global count/byte limits under
m_mutex, with replacement accounting. OldestEvictable/ForSource lines1004–1034
skip active entries and pin_progress. Thus total count>=16 is not equivalent to
unavailable capacity: some entries can be evicted, while a pinned/queued/running
set cannot. Bytes and global pressure can refuse even below the source count cap.
Production code has no equivalent atomic download-capacity reservation query;
the per-source count access in this header is exposed as a ForTest method.

For a later quota-aware version I would restrict gating to requested uncovered
consensus background holes; account for outstanding requests/byte uncertainty;
avoid treating every full source as non-evictable; let other netgroups and the
foreground/acquisition progress lane proceed; and re-evaluate/wake when retained
capacity changes. A request-time observation alone is racy, so receive-time Retain
limits and the safe non-disconnect fallback remain necessary. A silent global
pause could strand the missing root. Those are design requirements, not validated
behavior or a reason to expand this handoff before your review.

Decision for JPP: review/fold the tested fallback, or agree the precise scheduler
variant first. I have not changed the candidate to claim an untested improvement.
The later1024-body rerun should follow the agreed change and report request counts
per hash, source retention, exact catch-up/restart and real validation evidence.
