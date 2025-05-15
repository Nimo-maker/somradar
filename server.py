from starlette.responses import FileResponse
from starlette.routing import Mount, Route
from shiny import App

from app import app as shiny_app  # import your Shiny app instance

def homepage(request):
    return FileResponse("launch.html")

routes = [
    Route("/", endpoint=homepage),
    Mount("/app", app=shiny_app)  # dashboard lives under /app
]

app = App(routes=routes)
