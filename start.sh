#!/bin/sh
cd /home/windows/cbse-app
nohup python3 app.py > /tmp/cbse-app.log 2>&1 &
echo $! > /tmp/cbse-app.pid
echo "Server PID: $(cat /tmp/cbse-app.pid)"
sleep 2
curl -s http://localhost:9090/health && echo "✅ Server running on port 9090"
