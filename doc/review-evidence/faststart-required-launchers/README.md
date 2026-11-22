# FastStart replacement launcher validation

Base: BTX release-0.34.17 at d9a9480484cea303649f3eab1e82f8e3d7572c21. macOS 26.5.1 ARM64, Python 3.12.14.

The same checksummed local replacement archive without btx-cli left the original install broken on the base. With the patch, the installer still rejected the archive and both old launchers ran with their original bytes. Both versions accepted the complete replacement on retry and preserved a separate data sentinel. The maintained missing-launcher cases cover both btxd and btx-cli and failed against the base installer. All 30 installer tests passed on the candidate. Applying JPP's #932 at c93e0b5fe1be9a1786b268ed0e28ebd4f5edc906 yielded 32 passing installer tests and the same paired-case result.

## Reproduce

1. Save observe.py locally and prepare a checkout at the base above. Use Python 3.12.
2. Run `python3 observe.py /path/to/checkout baseline.json`. Expect a nonzero exit at the old-launcher assertion. The script saves its receipt beside itself.
3. Apply validate-before-replacement.patch in the checkout. Run the same script with candidate.json as the second argument. Expect exit 0.
4. From the checkout run `PYTHONWARNINGS=ignore::DeprecationWarning python3 test/util/btx_agent_setup_test.py` to run the 30 installer cases.

These runs used local fixture archives and shell launchers, without an official archive, a running node or a native Linux or Windows run. The branch contains only this repair and its maintained regression. JPP's archive hard-link work is in [#932](https://github.com/btxchain/btx/pull/932).
