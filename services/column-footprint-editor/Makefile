serve:
	cd postgis-geologic-map && docker-compose up && cd .. & python3 backend/app.py 

kill:
	kill -9 $(lsof -i TCP:8000 | grep LISTEN | awk '{print $2}')
# command to kill the app on port 8000
