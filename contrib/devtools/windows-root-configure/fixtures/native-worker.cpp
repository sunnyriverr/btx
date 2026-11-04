#include <cstdlib>
#include <fstream>
#include <iostream>
int main()
{
    const char* marker = std::getenv("FIXTURE_MARKER");
    if (!marker) return 2;
    std::ofstream out(marker, std::ios::app);
    out << "invoked\n";
    out.close();
    if (!out) return 3;
    std::cout << "{\"ok\":true}\n";
    return 0;
}
