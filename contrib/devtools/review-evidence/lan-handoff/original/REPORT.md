# LAN receive-boundary candidate — private, tested on macOS

## Result

The **same final real-helper regression** fails against the original binary and passes against the final candidate. The failure is the demonstrated automatic connection after an off-scope beacon. Valid discovery still works on both binaries: a multicast beacon received on the selected LAN interface produces an automatic TCP connection and TLS ClientHello.

No PR, post, upload, deployment, shared-source edit or production change. This remains a candidate awaiting independent review and other-platform verification.

## Focused change

`candidate.patch` changes only `src/modelnet/native_discovery.cpp` and its private header state:

- Enable receive-interface/destination ancillary information and use it when reading a beacon. Missing or truncated metadata/datagrams are rejected. Failure to enable the needed facility reports `LAN_RECEIVE_SCOPE`; unsupported platforms fail closed for this optional discovery path.
- Retain the **exact interface index and IPv4 address successfully joined**, using indexed `MCAST_JOIN_GROUP`. Recheck current eligibility and netmask before admitting a packet. This avoids treating the same address on a different interface as the interface that was joined.
- Require a private source on that interface's subnet and a destination equal to the discovery multicast group or that selected interface's own unicast address. Valid on-interface unicast remains allowed by the predicate; the native positive test is multicast.
- Leave beacon format, transport ports, TTL/caps, explicit peers, PQ1 authentication, model acquisition, storage/spend policy and monetary code unchanged.

The header changes a private vector element, so `helper.cpp`, its other production user, was recompiled against the new header. **Its source body is byte-identical** to the original. No public API or consensus change.

## Identical native before/after test

macOS 26.5.1 arm64/M4, AppleClang 17 Release flags. Final harness SHA-256 `5935d886fd1643e28a30c6dae5373509806d5ddd872a612974cffb9c69e78731`.

| Same safety oracle | Original | Final candidate |
|---|---|---|
| LAN disabled + valid off-scope beacon | No hint/connection | No hint/connection |
| Before a beacon; wrong network; malformed padding | No connection in each six-second window | Same |
| Private-source beacon delivered through loopback | **FAIL:** hint retained, automatic TCP/TLS ClientHello after 2.236 s | **PASS:** hint 0, no connection for six seconds |
| Valid multicast on selected LAN interface | TCP/TLS ClientHello after 4.066 s | TCP/TLS ClientHello after 4.068 s |
| Health/stop | Unix RPC responsive; all helpers exit 0 | Same |

The final candidate hash is `22bdcb303bd64b4bb76bbf0d3d506de769931b44e639d5ac6b8e62a3b5f89916`; original is `ec92facce2c381daa59c4ddabafc9d3f7a7d69d2b44279c3014df50712acf200` at `cbf65894`.

The test is own-host only, without configured peers. Each helper uses a fresh disposable model directory, explicit storage 0, default follow-peers true and automatic spend 0. A process-local Seatbelt IP rule permits only this computer; the isolation control allows the assigned local address and refuses an unassigned loopback address with EPERM. The valid multicast sender sets TTL 0. An independent socket witness records the actual selected interface (`en0`) and multicast destination from kernel ancillary data. This is **real kernel interface evidence, not a fabricated interface in the native test**, but remains a same-host test, not physical-LAN qualification.

The dummy TCP listener only receives the ClientHello, then closes. Every final helper case reports authenticated peers 0 and acquired models 0. No authentication, model transfer, inference or wallet operation is performed.

One final baseline invocation and one final indexed-candidate invocation establish the comparison. The earlier address-only candidate passed the original oracle, but review exposed the duplicate/moved-address ambiguity; it is retained separately as a pilot, not presented as the final fix. The unchanged baseline and unchanged final harness were reused; only the revised candidate was rerun.

## Guard sensitivity

`policy_checks.cpp` exercises 15 **synthetic** ancillary/interface cases against the actual candidate code, separately from the native helper evidence. Selected multicast and selected unicast pass. Wrong interface, off-subnet private source, wrong destination, missing metadata, truncated metadata/data, removed/down/loopback interfaces, noncontiguous netmask and moved/duplicated addresses reject.

Four deliberate source mutations fail the relevant oracles: remove receive-index checks; remove the stored joined-index check; remove subnet comparison; remove destination comparison. These prove sensitivity of the focused tests, not native remote-topology behavior. No artificial interface metadata is claimed as OS qualification.

## Build and overlap verification

The existing untouched CMake library/object inputs first reproduced the **exact original normal-build helper hash**. The final candidate compiles the changed discovery translation unit and the byte-identical helper body against the changed header, using the recorded CMake flags, then relinks those objects with the same hashed common inputs. Original archive helper/discovery objects are excluded by symbol resolution. This is a scoped component replacement/relink, **not a clean full-tree rebuild**.

`verification.json` records all identities and checks. The patch passes a dry-run on the current preserved source and on #348's port-filter head. That is an apply check, not runtime qualification of the combined PR stack. Fresh opening/finishing surveys find the same 79 open heads and no matching receive-boundary fix; private unpublished work is unknown. See `dedup.json` and `finish-dedup.json`.

A final link with a large diagnostic map hit ENOSPC. The failed link is excluded. Only this task's duplicate baseline binary and oversized maps were removed after saving identities/object lists; the original cached baseline, sources and test results remain. Linking without the map succeeds. No active wallet, node, unrelated testing or shared build artifact was deleted. Earlier discovery investigation's setup corrections remain in its report.

## Limits before merge or release use

- **Not run:** native Linux or Windows build/runtime, BSD portability, full suite, sanitizers, long soak, physical multihost/routed/VPN tests, real network topology changes or release qualification.
- Linux/Windows ancillary receive branches are implemented, but not compiler/runtime-qualified here. Other platforms currently disable optional LAN discovery rather than accepting metadata-free hints. Independent platform checks are required before merging.
- On-interface unicast and topology-removal/moved-address cases are synthetic policy tests; only multicast and the original off-scope path have native process/socket coverage.
- This proves discovery admission and connection behavior. It does not prove full model acquisition, strict-PQ1 negotiation, remote exploitability, load/DoS cost, monetary impact or physical adjacency from a subnet match.

For reproduction on a compatible Mac: apply the patch and build the helper using the repository's normal process, then run `regression.py --binary /absolute/path/to/btx-modeld --output /absolute/disposable/results`. Use the same harness on the baseline. The expected original result is `FAIL_OFF_SCOPE_AUTOMATIC_CONNECTION`/exit 1; final result is `PASS_SAFE_DISCOVERY`/exit 0. The test refuses to start if discovery port 29448 is already in use. Do not run against a production model directory.

Private evidence and patch are ready for review. They are not independently approved, merged or deployed.
