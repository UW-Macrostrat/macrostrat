from api import app
from database import Database
import uvicorn

if __name__ == "__main__":
    db = Database()
    db.create_project_table()
    uvicorn.run(app, host="0.0.0.0", port=8000)
