#!/bin/bash

# Compile using wildcards to ensure all source files are caught
gcc -o psd_app \
    main.c \
    psd-ane2/*.c \
    -I./psd-ane2 \
    -lcjson -lfftw3 -lm -lhackrf

if [ $? -eq 0 ]; then
    echo "Build successful: ./psd_app"
else
    echo "Build failed"
fi