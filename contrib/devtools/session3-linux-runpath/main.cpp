#include <cstdio>

extern "C" int btx_s3_runpath_marker_a97af7b3();

int main()
{
    const int value = btx_s3_runpath_marker_a97af7b3();
    std::printf("btx-runpath-probe:%d\n", value);
    return value == 42 ? 0 : 1;
}
