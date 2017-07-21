from views.admin import admin_menu
from views.auth import login
from views.auth import logout
from views.auth.password import confirm as confirm_password
from views.auth.password import handler as password
from views.auth.register import confirm as confirm_register
from views.auth.register import handler as register
from views.batch import create_batch
from views.batch import edit_batch
from views.batch import delete_batch
from views.batch import list_batch
from views.client import client_menu
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

    app.router.add_get("/admin/", admin_menu, name="admin")
    app.router.add_get("/client/", client_menu, name="client")

    # auth
    app.router.add_route('*', "/", login, name="login")
    app.router.add_route('*', "/logout/", logout, name="logout")
    app.router.add_route('*', "/register/", register, name="register")
    app.router.add_get("/register/{token}/", confirm_register, name="confirm_register")
    app.router.add_route('*', "/password/", password, name="password")
    app.router.add_route('*', "/password/{token}/", confirm_password, name="confirm_password")

    # batches
    app.router.add_route("*", "/batch/create/", create_batch, name="create_batch")
    app.router.add_get("/batch/delete/{id:\d+}/", delete_batch, name="delete_batch")
    app.router.add_route("*", "/batch/edit/{id:\d+}/", edit_batch, name="edit_batch")
    app.router.add_get("/batch/list/", list_batch, name="list_batch")

    # products
    app.router.add_route("*", "/product/create/", create_product, name="create_product")
    app.router.add_get("/product/delete/{id:\d+}/", delete_product, name="delete_product")
    app.router.add_route("*", "/product/edit/{id:\d+}/", edit_product, name="edit_product")
    app.router.add_get("/product/list/", list_product, name="list_product")

    # repositories
    app.router.add_route("*", "/repository/create/", create_repository, name="create_repository")
    app.router.add_get("/repository/delete/{id:\d+}/", delete_repository, name="delete_repository")
    app.router.add_route("*", "/repository/edit/{id:\d+}/", edit_repository, name="edit_repository")
    app.router.add_get("/repository/list/", list_repository, name="list_repository")
