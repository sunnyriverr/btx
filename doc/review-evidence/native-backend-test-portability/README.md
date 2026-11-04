# Native Windows backend-capability test portability

Scoped fix/test commit: `c3af59dfea2dd3ca9ed2e3efb7677f706b4196ad` on accepted46caec76. One test-source change. See REPORT.md first.

The identical real generated unit target fails on the original source and compiles with the candidate. Native cl/clang-cl isolated exact-case restoration controls pass; a dropped-restoration mutant fails. Mac original/candidate exact-helper controls pass. Full test_btx/node link or unit execution, GPU execution, Linux and MinGW are unqualified. The earlier incomplete candidate and fixture error are disclosed in the report.

Executed native recipe: https://github.com/sunnyriverr/btx/actions/runs/41761879608 at orchestration f87ef56b4741b8acb7e877dda8537fc2abf38512. native-recipe contains byte-identical executed control inputs; their original paths/hashes are in dispatch.json and remote-input-verification.json. They ran from contrib/devtools/windows-root-configure beside candidate.cpp/manifest/cases/fixture/probe, with separate stock checkout btx/ as shown in workflow.yml. These copies are for inspection; no rerun of this evidence branch's root, relocated workflow, or entire project is claimed.

native-records contains actual compiler/runtime logs, flags and identity receipts. All26 logs are hashed in result.json; the full14,307-file source catalogs and retained object/executables are in the original run artifact, also preserved locally by the contributor. Its ZIP digest is in native-records/artifacts.json. Artifact expiry does not replace the contributor's retained evidence. The small selected command is from the full unchanged compile database; no manually imitated root compile command supplied the pass.

No upstream handoff is authorized yet. This local evidence packaging changes none of the tested code, inputs or logs. Product credit and platform limits remain unchanged.
