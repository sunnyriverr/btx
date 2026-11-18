
# Qualification-only consumer of the existing cloud/first-run translation units.
# Uses normal test_btx main/support libraries; not aggregate test_btx.
get_target_property(_s2_cloud_links test_btx LINK_LIBRARIES)
get_target_property(_s2_cloud_defs test_btx COMPILE_DEFINITIONS)
add_executable(s2_cloud_control_tests main.cpp modelnet_cloud_tests.cpp modelnet_first_run_tests.cpp)
target_link_libraries(s2_cloud_control_tests PRIVATE ${_s2_cloud_links})
if(_s2_cloud_defs)
  target_compile_definitions(s2_cloud_control_tests PRIVATE ${_s2_cloud_defs})
endif()
