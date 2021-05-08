from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse, JSONResponse
from pathlib import Path
import json
import uvicorn

from database import Database

here = Path(__file__).parent

db = Database()

middleware = [
    Middleware(CORSMiddleware, allow_origins=['*'])
]

app = Starlette(debug=True, middleware=middleware)

@app.route('/')
async def homepage(request):
    return PlainTextResponse("Home Page")

@app.route('/columns')
async def geometries(request):
    return JSONResponse({"Geoms": "Geometry Data"})

@app.route('/lines')
async def lines(request):
    q = here / "queries" / "get-linework.sql"
    sql = open(q).read()

    df = db.exec_query(sql)

    lines = []
    for i in range(0, len(df['lines'])):
        obj = {}
        obj['geometry'] = json.loads(df['lines'][i])
        obj['type'] = "Feature"
        obj['properties'] = {}
        lines.append(obj)

    return JSONResponse({"type": "FeatureCollection", "features": lines})

if __name__ == "__main__":
    db.print_hello()
    uvicorn.run(app, host='0.0.0.0', port=8000)

