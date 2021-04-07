from starlette.applications import Starlette
from starlette.responses import PlainTextResponse, JSONResponse
import uvicorn

from database import Database


db = Database()
app = Starlette(debug=True)

@app.route('/')
async def homepage(request):
    return PlainTextResponse("Home Page")

@app.route('/columns')
async def geometries(request):
    return JSONResponse({"Geoms": "Geometry Data"})

if __name__ == "__main__":
    db.print_hello()
    uvicorn.run(app, host='0.0.0.0', port=8000)

