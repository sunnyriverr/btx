#!/bin/sh
set -eu
cd "$(dirname "$0")"
for v in before after; do
 g++ -std=c++20 -O1 -g0 -Wall -Wextra -pthread -I$v/include -Iinclude -Iunivalue/include -Iunivalue/lib driver.cpp $v/supervisor.cpp $v/transport.cpp univalue/lib/*.cpp -o $v/test-driver
 sha256sum $v/test-driver
done
