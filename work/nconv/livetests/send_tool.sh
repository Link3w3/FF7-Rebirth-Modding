#!/bin/bash
# send_tool.sh <lua file> <args lua table text>   -> prints a tool.lua command (seq = now ms)
f="$1"; a="${2:-{\}}"
printf 'return { seq = %s, op = "lua", name = "%s", args = %s, code = [==[\n' "$(date +%s%3N)" "$(basename "$f" .lua)" "$a"
cat "$f"
printf ']==] }\n'
