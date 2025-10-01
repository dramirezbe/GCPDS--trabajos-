cmake_minimum_required(VERSION 3.10)
project(Processing C)

set(CMAKE_C_STANDARD 99)

# Add executable with sources
add_executable(myapp
    main.c
    utils/cJSON.c
)

# Include headers from utils
target_include_directories(myapp PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/utils)
