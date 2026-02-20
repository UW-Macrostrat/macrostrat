import re
from typing import Optional

from pydantic import BaseModel

from macrostrat.core.database import get_database


class ProjectIdentifier(BaseModel):
    id: Optional[int] = None
    slug: Optional[str] = None
    name: Optional[str] = None

    # At least one of id, slug, or name must be provided
    def __init__(self, **data):
        super().__init__(**data)
        if not (self.id or self.slug or self.name):
            raise ValueError("At least one of id, slug, or name must be provided")


class ProjectData(ProjectIdentifier):
    id: int
    slug: str
    name: str


def get_macrostrat_model(db, table_name: str):
    """Get the SQLAlchemy model for a given table name."""
    name = "macrostrat_" + table_name
    if not hasattr(db.model, name):
        db.automap(schemas=["macrostrat"])
    return getattr(db.model, name)


def get_macrostrat_table(db, table_name: str):
    """Get the SQLAlchemy table for a given table name."""
    name = "macrostrat_" + table_name
    if not hasattr(db.table, name):
        db.automap(schemas=["macrostrat"])
    return getattr(db.table, name)


def get_or_create_project(
    db, project: ProjectIdentifier, create_if_not_exists: bool = True
) -> ProjectData:
    """Get or create a project in the database."""
    # map the project table
    Project = get_macrostrat_model(db, table_name="projects")

    # Try to find the project by id, slug, or name
    query = db.session.query(Project)
    if project.id is not None:
        query = query.filter(Project.id == project.id)
    elif project.slug is not None:
        query = query.filter(Project.slug == project.slug)
    elif project.name is not None:
        query = query.filter(Project.project == project.name)
    else:
        raise ValueError("At least one of id, slug, or name must be provided")

    existing_project = query.first()
    if existing_project:
        return ProjectData(
            id=existing_project.id,
            slug=existing_project.slug,
            name=existing_project.project,
        )

    if create_if_not_exists:
        # Create a new project
        # Remove parentheticals from the project name for the slug
        slug = None
        if project.name is not None:

            simple_name = re.sub(r"\s*\(.*?\)\s*", "", project.name)
            simple_name = re.sub(r"\s+", " ", simple_name).strip()
            slug = simple_name.lower().replace(" ", "-")

        new_project = Project(
            id=project.id,
            slug=slug,
            project=project.name,
            descrip="A random description",
            timescale_id=1,  # TODO: this should be set to a valid timescale ID
        )
        db.session.add(new_project)
        return ProjectData(
            id=new_project.id,
            slug=new_project.slug,
            name=new_project.project,
        )

    return None


def get_all_liths():
    """Get all lithologies from the database."""
    db = get_database()
    return db.run_query("SELECT id, lith name FROM macrostrat.liths").fetchall()


def get_all_lith_attributes():
    """Get all lithology attributes from the database."""
    db = get_database()
    return db.run_query("SELECT id, lith_att name FROM macrostrat.lith_atts").fetchall()
