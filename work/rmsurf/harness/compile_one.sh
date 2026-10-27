#!/bin/sh
f=$1
printf '#include "../harness.hpp"\n#include "%s"\n' "$(basename $f)" > ${f%.cpp}.tu.cpp
g++ -std=c++17 -O0 -fsyntax-only -I. ${f%.cpp}.tu.cpp > ${f%.cpp}.err 2>&1 && rm -f ${f%.cpp}.err ${f%.cpp}.tu.cpp && echo ok || echo "FAIL $f"
