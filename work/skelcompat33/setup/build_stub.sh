#!/bin/sh
# Builds build/Setup.stub.exe (x64 Windows GUI) with zig's clang + mingw-w64 (pip install ziglang).
set -e
cd "$(dirname "$0")/src"
python3 -m ziglang build-exe -target x86_64-windows-gnu -O ReleaseSmall --subsystem windows -municode -lc -lc++ \
  -cflags -std=c++17 -Wall -Wextra -Werror -Wno-unused-parameter -fno-exceptions -- Setup.cpp \
  -cflags -std=c99 -Wall -- ../third_party/puff/puff.c \
  Setup.rc -luser32 -lgdi32 -lcomctl32 -lshell32 -lole32 -luuid -ladvapi32 -lcomdlg32 \
  --name Setup.stub -femit-bin=../build/Setup.stub.exe
rm -f ../build/Setup.stub.pdb ../build/Setup.stub.lib
ls -la ../build/Setup.stub.exe
