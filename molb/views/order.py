from datetime import datetime
from datetime import timedelta

from aiohttp_security import authorized_userid
from aiohttp.web import HTTPBadRequest
from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
from aiohttp.web import HTTPSeeOther
import aiohttp_jinja2
from aiohttp_session_flash import flash
from wtforms import SelectField
from wtforms import SubmitField

from molb.auth import require
from molb.views.csrf_form import CsrfForm
from molb.views.utils import generate_csrf_meta
from molb.views.utils import remove_special_data
from molb.views.utils import RollbackTransactionException


class CreateOrderForm(CsrfForm):
    batch_id = SelectField("Fournée", coerce=int)
    submit = SubmitField("Valider")


class FillOrderForm(CsrfForm):
    submit = SubmitField("Valider")


async def get_available_products_in_batch(conn, batch_id, excluded=None):
    """Return all the available products in the batch. Available quantities
    are updates with the already ordered products"""

    # select all available products in the batch
    q = (
        "SELECT p.id, p.name, p.description, p.price, quantity "
        "FROM batch_product_association AS bpa "
        "INNER JOIN product AS p ON bpa.product_id = p.id "
        "WHERE p.available AND bpa.batch_id = $1"
        "ORDER BY p.name"
    )
    rows = await conn.fetch(q, batch_id)
    products = {p["id"]: dict(p) for p in rows}

    # get summed quantities of all orders by product
    if excluded is not None:
        q = (
            "SELECT product_id, SUM(quantity) AS quantity "
            "FROM order_product_association "
            "INNER JOIN order_ AS o ON o.id = order_id "
            "INNER JOIN product AS p ON p.id = product_id "
            "WHERE p.available AND o.batch_id = $1 AND order_id != $2 "
            "GROUP BY product_id"
        )
        rows = await conn.fetch(q, batch_id, excluded)
    else:
        q = (
            "SELECT product_id, SUM(quantity) AS quantity "
            "FROM order_product_association "
            "INNER JOIN order_ AS o ON o.id = order_id "
            "INNER JOIN product AS p ON p.id = product_id "
            "WHERE p.available AND o.batch_id = $1 "
            "GROUP BY product_id"
        )
        rows = await conn.fetch(q, batch_id)
    order_products = {op["product_id"]:op["quantity"] for op in rows}

    # remove already ordered products from the batch products
    for product_id, quantity in order_products.items():
        if product_id in products:
            products[product_id]["quantity"] -= order_products[product_id]

    return products


@require("client")
@aiohttp_jinja2.template("create-order.html")
async def create_order(request):
    login = await authorized_userid(request)

    async with request.app["db-pool"].acquire() as conn:
        q = (
            "SELECT c.id, c.disabled, r.days "
            "FROM client AS c "
            "INNER JOIN repository AS r ON c.repository_id = r.id "
            "WHERE c.login = $1 "
        )
        client = await conn.fetchrow(q, login)
        client_id = client["id"]

        if client["disabled"]:
            flash(request, ("warning", "Vous ne pouvez pas passer de commande."))
            return HTTPFound(request.app.router["list_order"].url_for())

        # select opened batches that have no order from the client
        # select opened batches that have no order on them
        # from all above selected batrches, select batches :
        #    - whose date is 12 hours in the future
        #    - client's delivery days corresponds to the batch date
        q = (
            "SELECT batch_id, batch_date FROM ("
            "    SELECT o.batch_id, b.date AS batch_date "
            "    FROM order_product_association AS opa "
            "    INNER JOIN product AS p ON opa.product_id = p.id "
            "    INNER JOIN order_ AS o ON opa.order_id = o.id "
            "    INNER JOIN client AS c ON o.client_id = c.id "
            "    INNER JOIN batch AS b ON o.batch_id = b.id "
            "    WHERE b.opened AND c.id != $1 "
            "    GROUP BY o.batch_id, b.date "
            "    UNION "
            "    SELECT b.id AS batch_id, b.date AS batch_date "
            "    FROM batch AS b "
            "    LEFT JOIN order_ AS o ON o.batch_id = b.id "
            "    WHERE b.opened AND o.batch_id IS NULL"
            ") AS sq "
            "WHERE batch_date > (NOW() + INTERVAL '12 hour') "
            "      AND (string_to_array($2, ',')::boolean[])[EXTRACT(DOW FROM batch_date) + 1] "
            "ORDER BY batch_date"
        )
        rows = await conn.fetch(q, client_id, str(client["days"]).strip("[]"))
        batch_choices = [(row["batch_id"], row["batch_date"]) for row in rows]

        if request.method == "POST":
            form = CreateOrderForm(await request.post(), meta=await generate_csrf_meta(request))
            form.batch_id.choices = batch_choices

            data = remove_special_data(form.data.items())
            batch_id = int(data["batch_id"])

            # just for csrf !
            if not form.validate():
                flash(request, ("danger", "Le formulaire comporte des erreurs."))
                return HTTPFound(request.app.router["list_order"].url_for())

            url = request.app.router["create_fill_order"].url_for(id=str(batch_id))
            return HTTPSeeOther(url)

        elif request.method == "GET":
            form = CreateOrderForm(meta=await generate_csrf_meta(request))
            form.batch_id.choices = batch_choices
            return {"form": form}

        else:
            raise HTTPMethodNotAllowed()


@require("client")
@aiohttp_jinja2.template("create-fill-order.html")
async def fill_order(request):
    batch_id = int(request.match_info["id"])

    login = await authorized_userid(request)

    async with request.app["db-pool"].acquire() as conn:
        q = (
            "SELECT c.id, c.disabled, r.days "
            "FROM client AS c "
            "INNER JOIN repository AS r ON c.repository_id = r.id "
            "WHERE c.login = $1 "
        )
        client = await conn.fetchrow(q, login)
        client_id = client["id"]

        if client["disabled"]:
            flash(request, ("warning", "Vous ne pouvez pas passer de commande."))
            return HTTPFound(request.app.router["list_order"].url_for())

        # get the batch date
        q = "SELECT date FROM batch WHERE id = $1"
        batch_date = await conn.fetchval(q, batch_id)

        # check that the batch corresponds to the delivery days
        if not client["days"][(batch_date.weekday() + 1) % 7]:
            flash(request, ("warning", "La fournée choisie ne permet de vous livrer."))
            return HTTPFound(request.app.router["list_order"].url_for())

        # check that there is no order from that client to this batch
        q = (
            "SELECT * "
            "FROM order_ AS o "
            "INNER JOIN batch AS b ON batch_id = b.id "
            "INNER JOIN client AS c ON client_id = c.id "
            "WHERE c.id = $1 AND b.id = $2"
        )
        row = await conn.fetchrow(q, client_id, batch_id)
        if row:
            flash(
                request,
                (
                    "warning",
                    "Vous avez déjà effectué une commande pour cette fournée."
                )
            )
            return HTTPFound(request.app.router["list_order"].url_for())

        # get product quantities updated with other orders on the same batch
        products = await get_available_products_in_batch(conn, batch_id)

        template_context = {
            "batch_date": batch_date,
            "batch_id": batch_id,
            "products": products.values()
        }

        if request.method == "POST":
            form = FillOrderForm(await request.post(), meta=await generate_csrf_meta(request))
            data = remove_special_data(await request.post())

            template_context["form"] = form

            # just for csrf !
            if not form.validate():
                flash(request, ("danger", "Le formulaire comporte des erreurs."))
                return template_context

            # get the ordered quantities from the form
            for product_id, product in products.items():
                ordered = data["product_qty_{}".format(product_id)].strip()
                if ordered == '':
                    ordered = 0
                else:
                    try:
                        ordered = int(ordered)
                        if ordered < 0:
                            raise ValueError("negative quantity")
                    except ValueError:
                        flash(request, ("danger", "Quantité(s) invalide(s)."))
                        return template_context
                product["ordered"] = ordered

            # check that less products has been ordered than the batch can provide
            # compute total price
            total = 0
            for product in products.values():
                ordered = product["ordered"]
                total += ordered*products[product_id]["price"]

                if product["quantity"] < ordered:
                    flash(
                        request,
                        (
                            "warning",
                            (
                                "Il n'y a pas assez de produits disponibles "
                                "pour satisfaire votre commande ({} \"{}\" demandés "
                                "pour {} disponibles)."
                            ).format(product["ordered"], product["name"],
                                     product["quantity"])
                        )
                    )
                    return template_context

            # check that at least one product has been ordered
            if total == 0:
                flash(request, ("warning", "Veuillez choisir au moins un produit"))
                return template_context

            try:
                async with conn.transaction():
                    # create the order
                    q = (
                        "INSERT INTO order_ (total, client_id, batch_id) "
                        "VALUES ($1, $2, $3) RETURNING id"
                    )
                    order_id = await conn.fetchval(q, total, client_id, batch_id)

                    # create order to products
                    for product_id, product in products.items():
                        ordered = product["ordered"]
                        if ordered != 0:
                            q = (
                                "INSERT INTO order_product_association ("
                                "   quantity, order_id, product_id"
                                ") "
                                "VALUES ($1, $2, $3)"
                            )
                            await conn.execute(q, ordered, order_id, product_id)
            except:
                flash( request, ( "warning", ( "Votre commande n'a pas pu être passée.")))
                return template_context

            flash(request, ("success", "Votre commande a été passée avec succès"))
            return HTTPFound(request.app.router["list_order"].url_for())

        elif request.method == "GET":
            form = FillOrderForm(meta=await generate_csrf_meta(request))
            template_context["form"] = form

            return template_context

        else:
            raise HTTPMethodNotAllowed()


@require("client")
@aiohttp_jinja2.template("edit-order.html")
async def edit_order(request):
    order_id = int(request.match_info["id"])
    login = await authorized_userid(request)

    async with request.app["db-pool"].acquire() as conn:
        q = (
            "SELECT c.id, c.disabled, r.days "
            "FROM client AS c "
            "INNER JOIN repository AS r ON c.repository_id = r.id "
            "WHERE c.login = $1 "
        )
        client = await conn.fetchrow(q, login)
        client_id = client["id"]

        if client["disabled"]:
            flash(request, ("warning", "Vous ne pouvez pas modifier votre commande."))
            return HTTPFound(request.app.router["list_order"].url_for())

        # check that the order belongs to the right client
        q = (
            "SELECT * FROM order_ "
            "WHERE id = $1 AND client_id = $2 AND payment_id IS NULL"
        )
        row = await conn.fetchrow(q, order_id, client_id)
        if not row:
            return HTTPFound(request.app.router["list_order"].url_for())

        # get batch id and batch date
        row = await conn.fetchrow(
            "SELECT batch_id, b.date FROM order_ AS o "
            "INNER JOIN batch AS b ON b.id = batch_id "
            "WHERE o.id = $1", order_id
        )
        batch_date = row["date"]
        batch_id = row["batch_id"]

        # check that's its not too late too modify the order
        if datetime.now() > batch_date - timedelta(hours=12):
            flash(request, ("warning", "Il est trop tard pour modifier votre commande."))
            return HTTPFound(request.app.router["list_order"].url_for())

        # get product quantities updated with other orders on the same batch
        products = await get_available_products_in_batch(conn, batch_id, excluded=order_id)

        template_context = {
            "batch_date": batch_date,
            "batch_id": batch_id,
            "order_id": order_id,
            "products": products.values()
        }

        if request.method == "POST":
            form = FillOrderForm(await request.post(), meta=await generate_csrf_meta(request))
            data = remove_special_data(await request.post())

            template_context["form"] = form

            # just for csrf !
            if not form.validate():
                flash(request, ("danger", "Le formulaire comporte des erreurs."))
                return template_context

            # get the ordered quantities from the form
            for product_id, product in products.items():
                ordered = data["product_qty_{}".format(product_id)].strip()
                if ordered == '':
                    ordered = 0
                else:
                    try:
                        ordered = int(ordered)
                        if ordered < 0:
                            raise ValueError("negative quantity")
                    except ValueError:
                        flash(request, ("danger", "Quantité(s) invalide(s)."))
                        return template_context
                product["ordered"] = ordered

            # check that less products has been ordered than the batch can provide
            # compute total price
            total = 0
            for product in products.values():
                ordered = product["ordered"]
                total += ordered*products[product_id]["price"]

                if product["quantity"] < ordered:
                    flash(
                        request,
                        (
                            "warning",
                            (
                                "Il n'y a pas assez de produits disponibles "
                                "pour satisfaire votre commande ({} \"{}\" demandés "
                                "pour {} disponibles)."
                            ).format(product["ordered"], product["name"],
                                     product["quantity"])
                        )
                    )
                    return template_context

            # check that at least one product has been ordered
            if total == 0:
                flash(request, ("warning", "Veuillez choisir au moins un produit"))
                return template_context

            # delete and re-create the order in a transaction
            try:
                async with conn.transaction():
                    # delete order to products association records
                    q = "DELETE FROM order_product_association WHERE order_id = $1"
                    await conn.execute(q, order_id)

                    # and re-create them
                    # create order to products
                    for product_id, product in products.items():
                        ordered = product["ordered"]
                        if ordered != 0:
                            q = (
                                "INSERT INTO order_product_association ("
                                "   quantity, order_id, product_id"
                                ") "
                                "VALUES ($1, $2, $3)"
                            )
                            await conn.execute(q, ordered, order_id, product_id)

                    # update order total
                    q = (
                        "UPDATE order_ SET total = $1, date=NOW() "
                        "WHERE id = $2"
                    )
                    await conn.fetchval(q, total, order_id)

            except:
                flash( request, ( "warning", ( "Votre commande n'a pas pu être modifiée.")))
                return template_context

            flash(request, ("success", "Votre commande a bien été modifiée."))
            return HTTPFound(request.app.router["list_order"].url_for())

        elif request.method == "GET":
            # select all the products from the order
            q = (
                "SELECT p.id, quantity "
                "FROM order_product_association AS opa "
                "INNER JOIN product AS p ON opa.product_id = p.id "
                "WHERE p.available AND opa.order_id = $1"
            )
            rows = await conn.fetch(q, order_id)

            # update the batch products with the order products
            for row in rows:
                products[row["id"]]["ordered"] = row["quantity"]

            form = FillOrderForm(meta=await generate_csrf_meta(request))
            template_context["form"] = form
            return template_context

        else:
            raise HTTPMethodNotAllowed()


@require("client")
async def delete_order(request):
    order_id = int(request.match_info["id"])
    login = await authorized_userid(request)

    async with request.app["db-pool"].acquire() as conn:
        client_id = await conn.fetchval(
            "SELECT id FROM client WHERE login = $1", login
        )

        # get and batch date
        batch_date = await conn.fetchval(
            "SELECT b.date FROM order_ AS o "
            "INNER JOIN batch AS b ON o.batch_id = b.id "
            "WHERE o.id = $1", order_id
        )
        if datetime.now() > batch_date - timedelta(hours=12):
            flash(request, ("warning", "Il est trop tard pour annuler votre commande."))
            return HTTPFound(request.app.router["list_order"].url_for())

        try:
            async with conn.transaction():
                # needs to be deleted before the order
                q = "DELETE FROM order_product_association WHERE order_id = $1"
                await conn.execute(q, order_id)

                # delete and check that the order belongs to the right client
                q = (
                    "DELETE FROM order_ "
                    "WHERE id = $1 AND client_id = $2 AND payment_id IS NULL "
                    "RETURNING id"
                )
                id_ = await conn.fetchval(q, order_id, client_id)
                if not id_:
                    raise

                flash(request, ("success", "Votre commande a bien été supprimée."))
        except:
            flash(request, ("warning", "Votre commande n'a pas pu être supprimée."))
    return HTTPFound(request.app.router["list_order"].url_for())


def translate_mode(value):
    if value == "order":
        return "Commande"
    elif value == "payed_by_check":
        return "Payée par chèque"
    elif value == "payed_by_paypal":
        return "Payée par Paypal"
    elif value == "payed_in_cash":
        return "Payée en liquide"


@require("client")
@aiohttp_jinja2.template("list-order.html")
async def list_order(request):
    login = await authorized_userid(request)

    async with request.app["db-pool"].acquire() as conn:
        client = await conn.fetchrow(
            "SELECT id, disabled FROM client WHERE login = $1", login
        )

        q = (
            "SELECT CAST(o.id AS TEXT), o.date AS order_date, o.total, o.payment_id, "
            "       p.id AS payment_id, p.mode AS payment_mode, b.date AS batch_date, "
            "       b.date - INTERVAL '12 hour' AS cancellation_date "
            "FROM order_ AS o "
            "INNER JOIN batch AS b ON o.batch_id = b.id "
            "LEFT JOIN payment AS p ON o.payment_id = p.id "
            "WHERE o.client_id = $1 ORDER BY batch_date DESC"
        )
        orders = await conn.fetch(q, client["id"])
    return {"disabled": client["disabled"], "orders": orders, "now": datetime.now()}
