cmake_minimum_required(VERSION 3.10)
project(ProcessingModule C)

set(CMAKE_C_STANDARD 99)

# Add executable with sources
add_executable(processing_module
    main.c
    utils/cJSON.c
)

# Include headers from utils
target_include_directories(processing_module PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/utils)
