#include <modelnet/supervisor.h>
#include <cstdio>
#include <type_traits>
static_assert(std::is_signed_v<pid_t>);
static_assert(!std::is_copy_constructible_v<modelnet::HelperSupervisor>);
int main(){std::printf("supervisor size=%zu align=%zu pid_t size=%zu\n",sizeof(modelnet::HelperSupervisor),alignof(modelnet::HelperSupervisor),sizeof(pid_t));}
