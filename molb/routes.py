import os.path as op

from molb.views.auth import login
from molb.views.auth import logout
from molb.views.auth.email import confirm as confirm_email
from molb.views.auth.email import handler as email
from molb.views.auth.password import confirm as confirm_password
from molb.views.auth.password import handler as password
from molb.views.auth.profile import delete_profile
from molb.views.auth.profile import edit_profile
from molb.views.auth.register import confirm as confirm_register
from molb.views.auth.register import handler as register
from molb.views.batch import create_batch
from molb.views.batch import edit_batch
from molb.views.batch import delete_batch
from molb.views.batch import list_batch
from molb.views.client import confirm_client
from molb.views.client import list_client
from molb.views.client import toggle_client
from molb.views.home import home
from molb.views.order import create_order
from molb.views.order import edit_order
from molb.views.order import delete_order
from molb.views.order import list_order
from molb.views.plan import plan
from molb.views.product import create_product
from molb.views.product import edit_product
from molb.views.product import delete_product
from molb.views.product import list_product
from molb.views.repository import create_repository
from molb.views.repository import edit_repository
from molb.views.repository import delete_repository
from molb.views.repository import list_repository
from molb.views.start import start
from molb.views.unconfirmed import list_unconfirmed
from molb.views.unconfirmed import delete_unconfirmed
from molb.views.unconfirmed import send_unconfirmed


def setup_routes(app):
    development_mode = app["config"]["application"].get("development", False)
    if development_mode:
        static_dir = op.join(op.dirname(op.abspath(__file__)), "static")
        app.router.add_static("/static", static_dir)

    # starting page
    app.router.add_get('/', start, name="start")

    # auth
    app.router.add_route('*', "/login/", login, name="login")
    app.router.add_route('*', "/logout/", logout, name="logout")
    app.router.add_route('*', "/email/", email, name="email")
    app.router.add_get("/email/{token}/", confirm_email, name="confirm_email")
    app.router.add_route('*', "/password/", password, name="password")
    app.router.add_route('*', "/password/{token}/", confirm_password, name="confirm_password")
    app.router.add_route('*', "/profile/delete/", delete_profile, name="delete_profile")
    app.router.add_route('*', "/profile/edit/", edit_profile, name="edit_profile")
    app.router.add_route('*', "/register/", register, name="register")
    app.router.add_get("/register/{token}/", confirm_register, name="confirm_register")

    # batches
    app.router.add_route('*', "/batch/create/", create_batch, name="create_batch")
    app.router.add_get("/batch/delete/{id:\d+}/", delete_batch, name="delete_batch")
    app.router.add_route('*', "/batch/edit/{id:\d+}/", edit_batch, name="edit_batch")
    app.router.add_get("/batch/list/", list_batch, name="list_batch")

    # client
    app.router.add_get("/client/confirm/{id:\d+}/", confirm_client, name="confirm_client")
    app.router.add_route('*', "/client/list/", list_client, name="list_client")
    app.router.add_get("/client/toggle/{id:\d+}/", toggle_client, name="toggle_client")
    app.router.add_get("/client/unconfirmed/list/", list_unconfirmed, name="list_unconfirmed")
    app.router.add_get("/client/unconfirmed/delete/{id:\d+}/", delete_unconfirmed, name="delete_unconfirmed")
    app.router.add_get("/client/unconfirmed/send/{id:\d+}/", send_unconfirmed, name="send_unconfirmed")

    # home
    app.router.add_get("/home/", home, name="home")

    # orders
    app.router.add_route('*', "/order/create/", create_order, name="create_order")
    app.router.add_get("/order/delete/{id:\d+}/", delete_order, name="delete_order")
    app.router.add_route('*', "/order/edit/{id:\d+}/", edit_order, name="edit_fill_order")
    app.router.add_get("/order/list/", list_order, name="list_order")

    # plan
    app.router.add_route('*', "/plan/", plan, name="plan")

    # products
    app.router.add_route('*', "/product/create/", create_product, name="create_product")
    app.router.add_get("/product/delete/{id:\d+}/", delete_product, name="delete_product")
    app.router.add_route('*', "/product/edit/{id:\d+}/", edit_product, name="edit_product")
    app.router.add_get("/product/list/", list_product, name="list_product")

    # repositories
    app.router.add_route('*', "/repository/create/", create_repository, name="create_repository")
    app.router.add_get("/repository/delete/{id:\d+}/", delete_repository, name="delete_repository")
    app.router.add_route('*', "/repository/edit/{id:\d+}/", edit_repository, name="edit_repository")
    app.router.add_get("/repository/list/", list_repository, name="list_repository")
