# Native regression entry point

Exact local code commit: `b1be792041f9337b4d8e1156f8b6aa76b8e09277`, parent `fd3a905f`. The three committed files equal the executed inputs. See `execution/native-integration.json` for the exact configured overlay/source-root paths, compiler, SQLite and input identities used in this native run. Source inputs were independently compared with the immutable tree; this was a fresh component build, not a full-node build.

For a checkout with its bundled dependencies present, the new target uses the existing `test/util/model_security` CMake project. On this Mac it uses the existing Homebrew SQLite (the SDK SQLite has a separately reported declaration issue):

```sh
cmake -S test/util/model_security -B build-channel -DCMAKE_BUILD_TYPE=Release \
  -DSQLite3_INCLUDE_DIR=/opt/homebrew/opt/sqlite/include \
  -DSQLite3_LIBRARY=/opt/homebrew/opt/sqlite/lib/libsqlite3.dylib
cmake --build build-channel --target channel-recovery-tests --parallel 1
ctest --test-dir build-channel -R '^security-channel-recovery$' --output-on-failure
```

The recorded execution used equivalent explicit `BTX_SOURCE_ROOT`/`BTX_SECURITY_OVERLAY` paths and selected only this target/test; the full-checkout spelling above was not separately run. On another platform choose its supported SQLite/toolchain and record that native result separately. Do not infer cross-platform success from the Mac run.

Expected candidate: one CTest, six component cases pass. The unchanged matched acceptance harness linked to baseline produced four passes and two target failures. Preserve synthetic-canary, explicit-time and Database-reopen boundaries from the report.
