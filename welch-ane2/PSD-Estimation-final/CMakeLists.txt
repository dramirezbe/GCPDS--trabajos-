cmake_minimum_required(VERSION 3.10)

project(c-psd-estimator C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

set(EXECUTABLE_NAME "c-psd-estimator")
set(SOURCE_FILES
    Modules/psd-estimators.c 
    Modules/utils.c          
    main.c                   
)
set(HEADER_FILES
    Modules/psd-estimators.h 
    Modules/utils.h         
)

add_executable(${EXECUTABLE_NAME} ${SOURCE_FILES} ${HEADER_FILES})

target_include_directories(${EXECUTABLE_NAME} PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/Modules 
)

target_link_libraries(${EXECUTABLE_NAME}
    PRIVATE
    fftw3
)


set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY
    ${CMAKE_CURRENT_SOURCE_DIR}
)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY
    ${CMAKE_CURRENT_SOURCE_DIR}
)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY
    ${CMAKE_CURRENT_SOURCE_DIR}
)