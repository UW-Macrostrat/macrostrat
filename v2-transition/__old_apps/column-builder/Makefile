start:
	docker-compose --profile dev --profile frontend_dev up -d

local-dev:
	docker-compose --profile dev up -d && cd dacite && npm run dev

local-dev-birdseye:
	docker-compose --profile dev up -d && cd BirdsEye/frontend && npm start

down:
	docker-compose down

test:
	database/tests/bin/run-tests

dump-burwell:
	database/bin/dump-burwell

dump-schema:
	database/tests/bin/dump-schema

upgrade-db:
	database/bin/run-alterations

create-fixtures:
	database/bin/run-fixtures