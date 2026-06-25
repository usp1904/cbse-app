#!/bin/bash
cd /home/windows/cbse-app
exec python3 server.py > /tmp/server.log 2>&1
