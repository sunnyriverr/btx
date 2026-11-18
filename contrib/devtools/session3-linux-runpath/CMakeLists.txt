cmake_minimum_required(VERSION 3.22)
project(btx_packaged_runpath_probe LANGUAGES CXX)

# Match the Linux parent setting; the imported production function must supply
# the relative linker path itself, without CMake's build-tree fallback.
set(CMAKE_SKIP_INSTALL_RPATH TRUE)
if(NOT DEFINED BTX_MODULE_FILE OR NOT EXISTS "${BTX_MODULE_FILE}")
  message(FATAL_ERROR "Supply the hash-checked production module")
endif()
include("${BTX_MODULE_FILE}")

add_library(btx_s3_runpath_marker_a97af7b3 SHARED marker.cpp)
set_target_properties(btx_s3_runpath_marker_a97af7b3 PROPERTIES
  SOVERSION 1
  LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib")
add_executable(probe main.cpp)
set_target_properties(probe PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
target_link_libraries(probe PRIVATE btx_s3_runpath_marker_a97af7b3)
btx_set_packaged_lib_runpath(probe)
