extern void UnavailableProbeDependency();
void UnusedProbe() { UnavailableProbeDependency(); }
int main() { UnusedProbe(); return 0; }
