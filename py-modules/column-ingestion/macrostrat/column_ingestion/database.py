import re
from typing import Optional

from macrostrat.core.database import get_database
from pydantic import BaseModel


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

def get_or_create_project(project: ProjectIdentifier, create_if_not_exists: bool = True) -> ProjectData:
    """Get or create a project in the database."""
    db = get_database()
    # map the project table
    if not hasattr(db.model, "macrostrat_projects"):
        db.automap(schemas=["macrostrat"])
    Project = db.model.macrostrat_projects

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
        db.session.commit()
        return ProjectData(
            id=new_project.id,
            slug=new_project.slug,
            name=new_project.project,
        )

    return None
