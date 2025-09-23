cmake_minimum_required(VERSION 3.16)
project(ANE2-rpi-fog C)

# Use C11
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Allow out-of-source builds
if("${CMAKE_SOURCE_DIR}" STREQUAL "${CMAKE_BINARY_DIR}")
  message(WARNING "It's recommended to build out-of-source (use a 'build/' directory).")
endif()

# Find pkg-config (we'll use it for libhackrf and fftw3)
find_package(PkgConfig REQUIRED)

# Check for libhackrf
pkg_check_modules(HACKRF REQUIRED libhackrf)
# Check for fftw3 (double precision)
pkg_check_modules(FFTW3 REQUIRED fftw3)

# Find curl via CMake module
find_package(CURL REQUIRED)

# Collect project sources automatically
file(GLOB SRCS
    "${CMAKE_SOURCE_DIR}/*.c"
    "${CMAKE_SOURCE_DIR}/Drivers/*.c"
    "${CMAKE_SOURCE_DIR}/Modules/*.c"
)

file(GLOB HEADERS
    "${CMAKE_SOURCE_DIR}/*.h"
    "${CMAKE_SOURCE_DIR}/Drivers/*.h"
    "${CMAKE_SOURCE_DIR}/Modules/*.h"
)

# Create the executable
add_executable(${PROJECT_NAME} ${SRCS} ${HEADERS})

# Include directories from pkg-config + local include dirs
target_include_directories(${PROJECT_NAME} PRIVATE
    ${HACKRF_INCLUDE_DIRS}
    ${FFTW3_INCLUDE_DIRS}
    ${CMAKE_SOURCE_DIR}/Drivers
    ${CMAKE_SOURCE_DIR}/Modules
)

# Compiler flags from pkg-config (if any)
if(HACKRF_CFLAGS)
  target_compile_options(${PROJECT_NAME} PRIVATE ${HACKRF_CFLAGS})
endif()
if(FFTW3_CFLAGS)
  target_compile_options(${PROJECT_NAME} PRIVATE ${FFTW3_CFLAGS})
endif()

# Link libraries and link dirs from pkg-config
target_link_directories(${PROJECT_NAME} PRIVATE ${HACKRF_LIBRARY_DIRS} ${FFTW3_LIBRARY_DIRS})
target_link_libraries(${PROJECT_NAME} PRIVATE
    ${HACKRF_LIBRARIES}
    ${FFTW3_LIBRARIES}
    CURL::libcurl
)

# If pkg-config gave extra libflags like -pthread, pass them along
if(HACKRF_LDFLAGS_OTHER)
  target_link_options(${PROJECT_NAME} PRIVATE ${HACKRF_LDFLAGS_OTHER})
endif()
if(FFTW3_LDFLAGS_OTHER)
  target_link_options(${PROJECT_NAME} PRIVATE ${FFTW3_LDFLAGS_OTHER})
endif()

# Useful user-facing messages
message(STATUS "HACKRF include dirs: ${HACKRF_INCLUDE_DIRS}")
message(STATUS "FFTW3 include dirs: ${FFTW3_INCLUDE_DIRS}")
message(STATUS "Linking with CURL: ${CURL_LIBRARIES}")

# Install rules (optional)
install(TARGETS ${PROJECT_NAME}
        RUNTIME DESTINATION bin)

# Add a build-type default
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()
