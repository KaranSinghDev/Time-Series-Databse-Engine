cmake_minimum_required(VERSION 3.10)
project(insight_engine)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Add shard.cpp to the source lists for both targets.
add_library(insight SHARED insight.cpp shard.cpp)
add_executable(engine_test test_engine.cpp insight.cpp shard.cpp)

# Explicitly tell our targets where to find header files.
target_include_directories(insight PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_include_directories(engine_test PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})