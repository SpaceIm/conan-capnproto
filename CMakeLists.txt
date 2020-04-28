cmake_minimum_required(VERSION 2.8.11)
project(cmake_wrapper)

include(conanbuildinfo.cmake)
conan_basic_setup()

add_definitions(-DKJ_NO_COMPILER_CHECK)
add_subdirectory("source_subfolder")
