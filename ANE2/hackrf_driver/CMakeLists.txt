cmake_minimum_required(VERSION 3.10)

# Define the project name and language
project(c-psd-estimator C)

# Set the C standard to C99
set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Define the name of the final executable
set(EXECUTABLE_NAME "c-psd-estimator")

# List all your source and header files
set(SOURCE_FILES
    Modules/psd-estimators.c
    Modules/utils.c
    main.c
)
set(HEADER_FILES
    Modules/psd-estimators.h
    Modules/utils.h
    Modules/datatypes.h
)

# Create the executable from the source and header files
# Note: Including headers here is not strictly required by modern CMake but helps IDEs find the files.
add_executable(${EXECUTABLE_NAME} ${SOURCE_FILES} ${HEADER_FILES})

# Add the 'Modules' directory to the include path so #include "psd-estimators.h" works
target_include_directories(${EXECUTABLE_NAME} PUBLIC
    ${PROJECT_SOURCE_DIR}/Modules
)

# Link the necessary libraries: fftw3 and the standard math library (m)
target_link_libraries(${EXECUTABLE_NAME}
    PRIVATE
    fftw3
    m
)

# --- Output Directory Configuration ---
# This is the line that places the final executable in your project's root directory.
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR})