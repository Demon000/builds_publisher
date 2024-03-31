#!/bin/bash

BUILDS_TXT_FILE="$1"
BUILDS_ROOT_DIR="$2"

echo "$BUILDS_TXT_FILE"
echo "$BUILDS_ROOT_DIR"

if [ "$#" -ne 2 ]; then
    echo "usage: $0 builds.txt ./build"
    exit 1
fi

mkdir -p "$BUILDS_ROOT_FILE"

while read BUILD_FILE; do
    BUILD_FILE_DIR=$(dirname "$BUILD_FILE")
    BUILD_FILE_NAME=$(basename "$BUILD_FILE")
    echo "$BUILD_FILE"
    echo "$BUILD_FILE_DIR"
    echo "$BUILD_FILE_NAME"
    mkdir -p "$BUILDS_ROOT_DIR/$BUILD_FILE_DIR"
    echo "$BUILD_FILE_NAME" > "$BUILDS_ROOT_DIR/$BUILD_FILE"
done < "$BUILDS_TXT_FILE"
