serve:
	uv run uvicorn macrostrat.column_footprint_editor:app --host 0.0.0.0 --port 8002 --reload
	#cd postgis-geologic-map && docker-compose up && cd .. & python3 backend/__init__.py

kill:
	kill -9 $(lsof -i TCP:8000 | grep LISTEN | awk '{print $2}')

run dev:
	docker-compose -f dev.yaml up --build
# command to kill the app on port 8000

