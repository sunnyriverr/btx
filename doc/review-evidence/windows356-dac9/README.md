# #356 Windows acceptance evidence on dac9aee5

The native clang-cl build and the stock node's offline genesis regtest lifecycle pass. Full Windows acceptance remains open.

- [Build](https://github.com/sunnyriverr/btx/actions/runs/42584109380): nine targets linked. [Lifecycle](https://github.com/sunnyriverr/btx/actions/runs/42596010732): two boots, startup/RPC/restart and clean shutdown. The stock node-owned guard did not become ready. Native Windows Modelnet helper operation remains unqualified.
- [Stock changed-path run](https://github.com/sunnyriverr/btx/actions/runs/42730441619) and [RC diagnostic](https://github.com/sunnyriverr/btx/actions/runs/42735908793): 30 passed, one registration failure, and 15,372 case names unrun on this stock binary. The unrun count includes one default-disabled case. Earlier run results remain attributed to their own sources.
- [#485](https://github.com/btxchain/btx/pull/485) supplies a tested guard startup/restart candidate. [#487](https://github.com/btxchain/btx/pull/487) supplies the Windows RC fixture repair and duplicate rejection control. [#478](https://github.com/btxchain/btx/pull/478#issuecomment-6763108220) supplies separate scoped persistence evidence. These results use candidate code.
- [JPP's report](https://github.com/btxchain/btx/pull/432#issuecomment-6750408409) gives 2,544 passing suites out of 2,608 on Windows 11 at 36ab4300, with a different MSVC library version. Our mapping of the 28 named failure suites to the current inventory transfers no pass verdicts. The report here tests the release tree dac9aee5. Numair's separate d522af52 swarm target and the full unit requirement remain open.

[Stock profile, binary hashes and executed case names](stock-acceptance.json) · [Older-source comparison](older-windows-comparison.json)
