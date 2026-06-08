#!/bin/bash
cd /home/windows/cbse-app
exec python3 app.py > /tmp/server.log 2>&1
