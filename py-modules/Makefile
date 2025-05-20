build:
	poetry --project tile-cache build --output ../dist
	mkdir -p ../services/legacy-tileserver/deps
	rm -f ../services/legacy-tileserver/deps/*.whl
	cp dist/*.whl ../services/legacy-tileserver/deps
