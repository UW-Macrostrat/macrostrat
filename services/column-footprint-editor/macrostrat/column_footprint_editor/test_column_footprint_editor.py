import os
from macrostrat.database import Database
from macrostrat.database.utils import temp_database
from macrostrat.utils import get_logger
from pytest import fixture

from .project import Project

testing_db = os.getenv("COLUMN_FOOTPRINTS_TEST_DATABASE")
if not testing_db:
    raise RuntimeError("COLUMN_FOOTPRINTS_TEST_DATABASE is not set")

log = get_logger(__name__)


@fixture(scope="session")
def db():
    # Check if we are dropping the database after tests
    with temp_database(testing_db, drop=False, ensure_empty=True) as engine:
        os.environ.update(
            {
                "GEOLOGIC_MAP_DATABASE": str(engine.url),
                "IMPORTER_API": "/import",
                "EXPORTER_API": "/export",
            }
        )
        yield Database(engine)


def test_create_new_project(db):
    """Tests the creation of a new project."""

    project = Project(
        db.engine.url, 1, name="Test Project", description="This is a test project."
    )
    project.create_new_project()

    assert project.id is not None, "Project ID should be set after creation."
    assert project.name == "Test Project", "Project name should match the input."
    assert (
        project.description == "This is a test project."
    ), "Project description should match the input."

    # Check if the project exists in the database
    assert (
        project.project_in_db()
    ), "Project should exist in the database after creation."

    # Clean up by removing the project
    project.db.remove_project({"project_id": project.id})
