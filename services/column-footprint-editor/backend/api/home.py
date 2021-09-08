from starlette.endpoints import HTTPEndpoint
from starlette.responses import PlainTextResponse

class HomePage(HTTPEndpoint):
    async def get(self, request):
        return PlainTextResponse("Home Page")
