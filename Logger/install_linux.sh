#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "============================================="
echo " Screen Tracker - Linux Build"
echo "============================================="

echo ""
echo "[1/3] Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y \
    gcc \
    g++ \
    libsqlite3-dev \
    libx11-dev \
    libxss-dev \
    pkg-config \
    python3-pip \
    python3-pyqt5

echo "[OK] System dependencies installed."

mkdir -p dist

echo ""
echo "[2/3] Compiling sqlite3.c with gcc..."
gcc -c sqlite3.c -O2 -I . -o dist/sqlite3.o

echo "[3/3] Compiling logger with g++..."
g++ \
    main.cpp \
    dist/sqlite3.o \
    -o dist/screen_tracker \
    -std=c++17 \
    -O2 \
    -I . \
    $(pkg-config --cflags --libs sqlite3) \
    $(pkg-config --cflags --libs x11) \
    -lXss

rm -f dist/sqlite3.o

echo "[OK] dist/screen_tracker created."

echo ""
echo "Installing Python dependencies..."
if [ -f ../Frontedn/requirements.txt ]; then
    pip3 install -r ../Frontedn/requirements.txt
else
    echo "[WARNING] ../Frontedn/requirements.txt not found"
fi

echo ""
echo "============================================="
echo " Build complete!"
echo ""
echo " Run logger:"
echo "   ./dist/screen_tracker"
echo ""
echo " Run GUI in another terminal:"
echo "   cd ../Frontedn && python3 main.py"
echo "============================================="
