#!/bin/sh
# What the PC's link would refuse that the clang syntax check does not see: a function of the file's anonymous namespace
# used but defined nowhere in it (a declaration in the wrong namespace). linkcheck.sh <obj>
U=$(llvm-nm --undefined-only "$1" | grep "?A0x")
if [ -n "$U" ]; then echo "UNRESOLVED (anonymous namespace):"; echo "$U"; exit 1; fi
echo "$1: no unresolved anonymous-namespace symbols"
