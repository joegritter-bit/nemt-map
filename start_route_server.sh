#!/bin/bash
source /home/joegritter/nemt_env/bin/activate
python /home/joegritter/nemt-scraper/route_server.py &
echo "Route server started PID $!"
