#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get -o Acquire::Retries=1 update -qq
apt-get install -y -qq --no-install-recommends ca-certificates curl libgomp1 libsqlite3-0 libzmq5 libevent-core-2.1-7 libevent-extra-2.1-7 libevent-pthreads-2.1-7 libssl3 libffi8
mkdir -p /tmp/python-stage
curl -fsSL --retry 1 --max-time 150 https://github.com/actions/python-versions/releases/download/3.12.16-40260402378/python-3.12.16-linux-22.04-x64.tar.gz -o /tmp/python-stage/python.tar.gz
echo 'ebdd874c6bb02d1ade9069da60b6b09f8346ba0ae0db11e60e6ce90cf5542fb7  /tmp/python-stage/python.tar.gz' | sha256sum --check
mkdir /tmp/python-stage/unpack
tar -xzf /tmp/python-stage/python.tar.gz -C /tmp/python-stage/unpack
(cd /tmp/python-stage/unpack && RUNNER_TOOL_CACHE=/opt/hostedtoolcache bash setup.sh)
export LD_LIBRARY_PATH=/opt/hostedtoolcache/Python/3.12.16/x64/lib
py=/opt/hostedtoolcache/Python/3.12.16/x64/bin/python3
"$py" -m pip install --disable-pip-version-check cryptography==46.0.4
ldd admitted/gui-pilot-runtime/qtbuild/bin/btxd | tee records/dependencies.log
if grep -q 'not found' records/dependencies.log; then exit 1; fi
"$py" -VV | tee records/python.log
timeout --kill-after=15s 300s "$py" -B proposal/observe.py --node "$GITHUB_WORKSPACE/admitted/gui-pilot-runtime/qtbuild/bin/btxd" --out "$GITHUB_WORKSPACE/records/native"
