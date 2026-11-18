
# Qualification-only target: full maintained economy translation unit with the
# normal test main and normal test_btx support libraries; not aggregate test_btx.
get_target_property(_s2_test_links test_btx LINK_LIBRARIES)
get_target_property(_s2_test_defs test_btx COMPILE_DEFINITIONS)
add_executable(s2_visibility_tests main.cpp modelnet_economy_tests.cpp)
target_link_libraries(s2_visibility_tests PRIVATE ${_s2_test_links})
if(_s2_test_defs)
  target_compile_definitions(s2_visibility_tests PRIVATE ${_s2_test_defs})
endif()
