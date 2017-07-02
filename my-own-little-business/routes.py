from views.admin import admin_menu
from views.batch import create_batch
from views.batch import edit_batch
from views.batch import delete_batch
from views.batch import list_batch
from views.repository import create_repository
from views.repository import edit_repository
from views.repository import delete_repository
from views.repository import list_repository

def setup_routes(app):
    app.router.add_static("/static", "static")

    app.router.add_get("/admin/", admin_menu)

    # batches
    app.router.add_route("*", "/batch/create/", create_batch)
    app.router.add_get("/batch/delete/{id:\d+}/", delete_batch)
    app.router.add_route("*", "/batch/edit/{id:\d+}/", edit_batch)
    app.router.add_get("/batch/list/", list_batch)

    # repositories
    app.router.add_route("*", "/repository/create/", create_repository)
    app.router.add_get("/repository/delete/{id:\d+}/", delete_repository)
    app.router.add_route("*", "/repository/edit/{id:\d+}/", edit_repository)
    app.router.add_get("/repository/list/", list_repository)
