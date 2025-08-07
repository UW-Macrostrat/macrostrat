from .project import Project


def test_create_new_project():
    """Tests the creation of a new project."""
    project = Project(1, name="Test Project", description="This is a test project.")
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
