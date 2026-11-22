from dotenv import load_dotenv

load_dotenv()

from api.tiles.tests.fixtures import (  # noqa
    app,
    client,
    db,
    test_database_url,
)
