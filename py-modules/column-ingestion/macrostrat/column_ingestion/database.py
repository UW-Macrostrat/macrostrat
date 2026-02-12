from pydantic import BaseModel



def get_or_create_project(name: str):
    """Get or create a project in the database."""
