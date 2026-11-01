#pragma once
#include <string>
#include <algorithm>
#include <cctype>
inline std::string ToLower(std::string s){for(auto& c:s)c=std::tolower((unsigned char)c);return s;}
