start:
	docker-compose --profile dev --profile frontend_dev up -d

local_dev:
	docker-compose --profile dev up -d && cd dacite && npm run dev

down:
	docker-compose down

test:
	database/tests/bin/run-tests

dump-burwell:
	database/bin/dump-burwell

dump-schema:
	database/tests/bin/dump-schema

create-fixtures:
	database/bin/run-fixtures