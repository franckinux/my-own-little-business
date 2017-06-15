from view import handler

def setup_routes(app):
    app.router.add_static("/static", "static")

    app.router.add_get("/", handler)
