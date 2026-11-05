#include <test/util/sdk_process.h>
#include <iostream>
int main() {
 const auto python=sdk_test::Python3();
 if(python.empty()) return 2;
 std::string out;
 int rc=sdk_test::Spawn({python,"-c","import sys; print('ok'); print('err',file=sys.stderr); sys.exit(7)"},out);
 if(rc!=7 || out.find("ok")==std::string::npos || out.find("err")==std::string::npos) return 3;
 out.clear();
 rc=sdk_test::Spawn({python,"-c","import sys; sys.stdout.write('x'*65536); sys.stderr.write('y'*65536)"},out,false);
 if(rc || out!=std::string(65536,'x')) return 4;
 std::cout << "native macOS Python/exit/stdout/stderr controls passed\n";
}
