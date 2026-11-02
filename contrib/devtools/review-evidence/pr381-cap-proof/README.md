# #381 submission-cap regression evidence

Test-only commit `3655ce1a9e6f9f41f9b4a37906701f045a2c46fd`, parent `6478f640`.

The stronger test passes cap2 and fails the cap99-only mutation at its final budget assertion, after all seven genuine native jobs complete in both variants. This addresses repch1c’s review finding that two running workers hid extra queued submissions.

[Results and scope](REPORT.md) · [Exact test patch](test-only.patch) · [Executed entry point and dependency instructions](reproducer/README.md) · [Raw results](linux/work/results.json).

One focused case per variant, first attempt. Configured native Alpine/aarch64 component; identical #384 timing prerequisite and explicit8MiB ELF stacks on both variants, identified reused dependency archives. The timing prerequisite is NOT in the test-only commit. This does not qualify unmodified #381, default stacks, the whole daemon, other platforms or a release. Existing starvation/restart tests were not repeated.

All identities and signed evidence are synthetic test fixtures. Internal review checked source/artifact consistency; it is not a second native execution or human replication. Absolute local paths are normalized in published text, with original/published hashes in normalization-manifest.json. Runnable test, patch and reproducer bytes are unchanged except post-run README documentation of dependency acquisition. No binaries, databases or keys are included.
