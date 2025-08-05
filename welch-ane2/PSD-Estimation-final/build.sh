#!/bin/bash

# This script automates the build process for the c-psd-estimator project.
# It can be executed from any subdirectory within the project.

# --- Configuration ---
# Define the name of your CMakeLists.txt file
CMAKE_LISTS_FILE="CMakeLists.txt"
# Define the name of the build directory
BUILD_DIR="build"
# Define the executable name (as specified in CMakeLists.txt)
EXECUTABLE_NAME="c-psd-estimator"

# --- Script Logic ---

# 1. Find the project root directory
# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Start searching for CMakeLists.txt from the script's directory upwards
PROJECT_ROOT=""
CURRENT_DIR="${SCRIPT_DIR}"
while [[ "${CURRENT_DIR}" != "/" ]]; do
    if [[ -f "${CURRENT_DIR}/${CMAKE_LISTS_FILE}" ]]; then
        PROJECT_ROOT="${CURRENT_DIR}"
        break
    fi
    CURRENT_DIR="$(dirname "${CURRENT_DIR}")"
done

if [[ -z "${PROJECT_ROOT}" ]]; then
    echo "Error: Could not find '${CMAKE_LISTS_FILE}' in the current directory or any parent directory."
    echo "Please ensure you are running this script from within your project directory."
    exit 1
fi

echo "Found project root: ${PROJECT_ROOT}"

# 2. Navigate to the project root
cd "${PROJECT_ROOT}" || { echo "Error: Failed to change to project root directory."; exit 1; }

# 3. Handle the build directory
if [[ -d "${BUILD_DIR}" ]]; then
    echo "Existing '${BUILD_DIR}' directory found. Removing its contents for a clean build..."
    # Remove the existing build directory to ensure a clean build.
    # This addresses the "replace the new files" requirement by starting fresh.
    rm -rf "${BUILD_DIR}"
    if [[ $? -ne 0 ]]; then
        echo "Error: Failed to remove existing '${BUILD_DIR}' directory. Please check permissions."
        exit 1
    fi
fi

echo "Creating new '${BUILD_DIR}' directory..."
mkdir "${BUILD_DIR}"
if [[ $? -ne 0 ]]; then
    echo "Error: Failed to create '${BUILD_DIR}' directory. Please check permissions."
    exit 1
fi

# 4. Navigate into the build directory
cd "${BUILD_DIR}" || { echo "Error: Failed to change to build directory."; exit 1; }

# 5. Run CMake to configure the project
echo "Running CMake to configure the project..."
cmake ..
if [[ $? -ne 0 ]]; then
    echo "Error: CMake configuration failed."
    exit 1
fi

# 6. Build the project
echo "Building the project..."
cmake --build .
if [[ $? -ne 0 ]]; then
    echo "Error: Project build failed."
    exit 1
fi

# 7. Provide success message and executable location
echo ""
echo "----------------------------------------------------"
echo "Build successful! The executable '${EXECUTABLE_NAME}' is located at:"
echo "${PROJECT_ROOT}/${BUILD_DIR}/${EXECUTABLE_NAME}"
echo "----------------------------------------------------"

exit 0
