from views.admin import admin_menu
from views.repository import create_repository
from views.repository import edit_repository
from views.repository import delete_repository
from views.repository import list_repository

def setup_routes(app):
    app.router.add_static("/static", "static")

    app.router.add_get("/admin/", admin_menu)

    # repositories
    app.router.add_route("*", "/repository/create/", create_repository)
    app.router.add_get("/repository/delete/{id:\d+}/", delete_repository)
    app.router.add_route("*", "/repository/edit/{id:\d+}/", edit_repository)
    app.router.add_get("/repository/list/", list_repository)
