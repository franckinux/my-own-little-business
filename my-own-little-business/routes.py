from views.admin import admin_menu
from views.client import client_menu
from views.auth import confirm
from views.auth import login
from views.auth import logout
from views.auth import register
from views.batch import create_batch
from views.batch import edit_batch
from views.batch import delete_batch
from views.batch import list_batch
from views.product import create_product
from views.product import edit_product
from views.product import delete_product
from views.product import list_product
from views.repository import create_repository
from views.repository import edit_repository
from views.repository import delete_repository
from views.repository import list_repository

def setup_routes(app):
    app.router.add_static("/static", "static")

    app.router.add_get("/admin/", admin_menu)
    app.router.add_get("/client/", client_menu)

    # auth
    app.router.add_route("*", "/", login)
    app.router.add_route("*", "/logout/", logout)
    app.router.add_route("*", "/register/", register)
    app.router.add_get("/confirm/{token}/", confirm)

    # batches
    app.router.add_route("*", "/batch/create/", create_batch)
    app.router.add_get("/batch/delete/{id:\d+}/", delete_batch)
    app.router.add_route("*", "/batch/edit/{id:\d+}/", edit_batch)
    app.router.add_get("/batch/list/", list_batch)

    # products
    app.router.add_route("*", "/product/create/", create_product)
    app.router.add_get("/product/delete/{id:\d+}/", delete_product)
    app.router.add_route("*", "/product/edit/{id:\d+}/", edit_product)
    app.router.add_get("/product/list/", list_product)

    # repositories
    app.router.add_route("*", "/repository/create/", create_repository)
    app.router.add_get("/repository/delete/{id:\d+}/", delete_repository)
    app.router.add_route("*", "/repository/edit/{id:\d+}/", edit_repository)
    app.router.add_get("/repository/list/", list_repository)
