#!/bin/bash
# Kill all existing DASH player instances before starting
for pid in $(ps aux | grep -E "simple_main|ffmpeg" | grep -v grep | awk '{print $2}'); do
    kill -9 $pid 2>/dev/null
done
sleep 1
rm -rf BBB-I-360p 2>/dev/null
cd "$(dirname "$0")"
python3 dash_qt/simple_main.py 2>/dev/null &
sleep 3
echo "SVC-DASH Player ready"
