#!/bin/zsh

# Obtain current working directory
CURRENT_CWD=$(pwd)

# Create build folder
if [ ! -d build ]; then
    echo "[build-processing] 📂 Creating build dir..."
    mkdir build
fi

# GO build
cd build || exit 1

echo "[build-processing] ⚙️ Execute CMake..."
cmake ..

echo "[build-processing] 🔨 Compiling..."
make -j$(nproc)

echo "[build-processing] ✅ Build ready in $CURRENT_CWD/build"
