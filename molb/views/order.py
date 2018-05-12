from datetime import datetime
from datetime import timedelta

from aiohttp_security import authorized_userid
from aiohttp.web import HTTPBadRequest
from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
from aiohttp.web import HTTPSeeOther
import aiohttp_jinja2
from aiohttp_session_flash import flash
from wtforms import HiddenField
from wtforms import SelectField
from wtforms import SubmitField

from molb.auth import require
from molb.views.csrf_form import CsrfForm
from molb.views.utils import generate_csrf_meta
from molb.views.utils import remove_special_data
from molb.views.utils import RollbackTransactionException


class FillForm(CsrfForm):
    batch_id = HiddenField(id="batch_id")
    submit = SubmitField("Valider")


class OrderForm(CsrfForm):
    batch_id = SelectField("Fournée", coerce=int)
    submit = SubmitField("Valider")


async def get_available_products_in_batch(conn, products, batch_id):
    """Return the availble quantities in the batch by product"""

    # get summed quantities of all orders by product
    q = (
        "SELECT product_id, SUM(quantity) AS quantity "
        "FROM order_product_association "
        "INNER JOIN order_ AS o ON o.id = order_id "
        "WHERE o.batch_id = $1 "
        "GROUP BY product_id"
    )
    rows = await conn.fetch(q, batch_id)
    order_products = {op["product_id"]:op["quantity"] for op in rows}

    # remove already ordered products from the batch
    for product_id, quantity in order_products.items():
        if product_id in products:
            try:
                products[product_id]["quantity"] -= order_products[product_id]
            except KeyError:
                pass

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

        if request.method == "POST":
            form = OrderForm(await request.post(), meta=await generate_csrf_meta(request))
            data = remove_special_data(form.data.items())
            batch_id = int(data["batch_id"])

            url = request.app.router["fill_order"].url_for()
            url = url.with_query({"batch_id": batch_id})
            return HTTPSeeOther(url)

        elif request.method == "GET":
            # select opened batches that have no order from the client
            # select opened batches that have no order on them
            # from all selected, select batched :
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
                "    WHERE b.opened AND b.id NOT IN ( "
                "          SELECT b_.id FROM order_ AS o_ "
                "          INNER JOIN batch AS b_ ON o_.batch_id = b_.id "
                "          INNER JOIN client AS c_ ON o_.client_id = c_.id "
                "          WHERE c_.id = $1 "
                "    ) "
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

            form = OrderForm(meta=await generate_csrf_meta(request))
            form.batch_id.choices = batch_choices
            return {"form": form}

        else:
            raise HTTPMethodNotAllowed()


@require("client")
@aiohttp_jinja2.template("fill-order.html")
async def fill_order(request):
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

        if request.method == "POST":
            form = FillForm(await request.post(), meta=await generate_csrf_meta(request))

            data = remove_special_data(await request.post())
            batch_id = int(data["batch_id"])

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

            products = await get_available_products_in_batch(
                conn, products, batch_id
            )

            # just for csrf !
            if not form.validate():
                flash(request, ("danger", "Le formulaire comporte des erreurs."))
                return {"form": form, "batch_id": batch_id, "products": products.values()}

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
                        return {"form": form, "batch_id": batch_id, "products": products.values()}
                product["ordered"] = ordered

            # check that at least one product has been ordered
            if sum([p["ordered"] for p in products.values()]) == 0:
                flash(request, ("warning", "Veuillez choisir au moins un produit"))
                return {"form": form, "batch_id": batch_id, "products": products.values()}

            # check that
            for product in products.values():
                if product["quantity"] < product["ordered"]:
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
                    return {"form": form, "batch_id": batch_id, "products": products.values()}

            # compute total price
            total = 0
            for product in products.values():
                ordered = product["ordered"]
                if ordered != 0:
                    total += ordered*products[product_id]["price"]

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
                return {"form": form, "batch_id": batch_id, "products": products}

            flash(request, ("success", "Votre commande a été passée avec succès"))
            return HTTPFound(request.app.router["list_order"].url_for())

        elif request.method == "GET":
            form = FillForm(meta=await generate_csrf_meta(request))

            # get the batch id from the request
            try:
                batch_id = int(request.rel_url.query["batch_id"])
            except:
                raise HTTPBadRequest()

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

            products = await get_available_products_in_batch(conn, products, batch_id)

            return {"form": form, "batch_id": batch_id, "products": products.values()}
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

        batch_date = await conn.fetchval(
            "SELECT b.date FROM order_ AS o "
            "INNER JOIN batch AS b ON o.batch_id = b.id "
            "WHERE o.id = $1", order_id
        )
        if datetime.now() > batch_date - timedelta(hours=12):
            flash(request, ("warning", "Il est trop tard pour modifier votre commande."))
            return HTTPFound(request.app.router["list_order"].url_for())

        q = "SELECT batch_id FROM order_ WHERE id = $1"
        batch_id = await conn.fetchval(q, order_id)

        # select opened batches that have no order from the client
        # select opened batches that have no order on them
        # from all selected, select batched :
        #    - whose date is 12 hours in the future
        #    - client's delivery days corresponds to the batxh date
        # select the batch id of the order
        q = (
            "SELECT batch_id, batch_date FROM ("
            "    SELECT o.batch_id, b.date AS batch_date "
            "    FROM order_product_association AS opa "
            "    INNER JOIN product AS p ON opa.product_id = p.id "
            "    INNER JOIN order_ AS o ON opa.order_id = o.id "
            "    INNER JOIN client AS c ON o.client_id = c.id "
            "    INNER JOIN batch AS b ON o.batch_id = b.id "
            "    WHERE b.opened AND b.id != $1 AND b.id NOT IN ( "
            "          SELECT b_.id FROM order_ AS o_ "
            "          INNER JOIN batch AS b_ ON o_.batch_id = b_.id "
            "          INNER JOIN client AS c_ ON o_.client_id = c_.id "
            "          WHERE c_.id = $2 "
            "    ) "
            "    GROUP BY o.batch_id, b.date "
            "    UNION "
            "    SELECT b.id AS batch_id, b.date AS batch_date "
            "    FROM batch AS b "
            "    LEFT JOIN order_ AS o ON o.batch_id = b.id "
            "    WHERE b.opened AND (o.batch_id IS NULL OR b.id = $2)"
            ") AS sq "
            "WHERE batch_date > (NOW() + INTERVAL '12 hour') "
            "      AND (string_to_array($3, ',')::boolean[])[EXTRACT(DOW FROM batch_date) + 1] "
            "ORDER BY batch_date"
        )
        rows = await conn.fetch(q, batch_id, client_id, str(client["days"]).strip("[]"))
        batch_choices = [(row["batch_id"], row["batch_date"]) for row in rows]

        # select all available products
        rows = await conn.fetch(
            "SELECT id, name, description, price FROM product WHERE available"
        )
        products = [dict(p) for p in rows]

        if request.method == "POST":
            form = OrderForm(await request.post(), meta=await generate_csrf_meta(request))
            form.batch_id.choices = batch_choices

            data = remove_special_data(await request.post())
            new_batch_id = int(data["batch_id"])

            for product in products:
                product_id = product["id"]
                quantity = data["product_qty_{}".format(product_id)]
                product["quantity"] = quantity

            # just for csrf !
            if not form.validate():
                flash(request, ("danger", "Le formulaire comporte des erreurs."))
                return {"form": form, "products": products}

            # 2 separate loops for correct form rendering
            quantities = {}
            for product in products:
                product_id = product["id"]
                qti = product["quantity"].strip()
                if qti == '':
                    qti = 0
                else:
                    try:
                        qti = int(qti)
                        if qti < 0:
                            raise ValueError("negative quantity")
                    except ValueError:
                        flash(request, ("danger", "Quantité(s) invalide(s)."))
                        return {"id": order_id, "form": form, "products": products}
                quantities[product_id] = qti

            if sum(quantities.values()) == 0:
                flash(request, ("warning", "Veuillez choisir au moins un produit"))
                return {"form": form, "products": products}

            # delete and re-create the order in a transaction
            try:
                async with conn.transaction():
                    # first step : delete the order

                    # needs to be deleted before the order
                    q = "DELETE FROM order_product_association WHERE order_id = $1"
                    await conn.execute(q, order_id)

                    # check that the order belongs to the right client
                    q = (
                        "DELETE FROM order_ "
                        "WHERE id = $1 AND client_id = $2 AND payment_id IS NULL "
                        "RETURNING id"
                    )
                    deleted = await conn.fetchval(q, order_id, client_id)
                    if not deleted:
                        raise RollbackTransactionException()

                    # second step : re-create it

                    # lock the batch record in the transaction
                    # q = (
                    #     "SELECT capacity FROM batch WHERE id = $1 FOR UPDATE"
                    # )
                    # batch_capacity = await conn.fetchval(q, new_batch_id)

                    # create an order, total is set to 0
                    q = (
                        "INSERT INTO order_ (total, client_id, batch_id) "
                        "VALUES ($1, $2, $3) RETURNING id"
                    )
                    new_order_id = await conn.fetchval(q, 0, client_id, new_batch_id)

                    # create order to products
                    for product_id, quantity in quantities.items():
                        if quantity != 0:
                            q = (
                                "INSERT INTO order_product_association ("
                                "   quantity, order_id, product_id"
                                ") "
                                "VALUES ($1, $2, $3)"
                            )
                            await conn.execute(q, quantity, new_order_id, product_id)

                    # # compute batch load
                    # q = (
                    #     "SELECT SUM(opa.quantity * p.load) AS load "
                    #     "FROM order_product_association AS opa "
                    #     "INNER JOIN product AS p ON opa.product_id = p.id "
                    #     "INNER JOIN order_ AS o ON opa.order_id = o.id "
                    #     "WHERE o.batch_id = $1"
                    # )
                    # batch_load = await conn.fetchval(q, new_batch_id)
                    #
                    # # check that the batch is not overloaded
                    # if batch_load > batch_capacity:
                    #     # if so, roll back the changes
                    #     raise RollbackTransactionException()

            except RollbackTransactionException:
                flash(
                    request,
                    (
                        "warning",
                        (
                            "Votre commande dépasse la capacité de la fournée, "
                            "veuillez supprimer des produits ou reduire des "
                            "quantités."
                        )
                    )
                )
                return {"id": order_id, "form": form, "products": products}

            # update order total
            q = (
                "UPDATE order_ SET total = ("
                "    SELECT SUM(opa.quantity * p.price) AS total "
                "    FROM order_product_association AS opa "
                "    INNER JOIN product AS p ON opa.product_id = p.id "
                "    WHERE opa.order_id = $1"
                ") "
                "WHERE id = $1"
            )
            await conn.execute(q, new_order_id)

            flash(request, ("success", "Votre commande a bien été modifiée."))
            return HTTPFound(request.app.router["list_order"].url_for())
        elif request.method == "GET":
            data = {"batch_id": batch_id}

            form = OrderForm(data=data, meta=await generate_csrf_meta(request))
            form.batch_id.choices = batch_choices

            async with conn.transaction():
                # get all products, setting quantity to 0 and put them in a
                # temporary table who lives only in the transaction
                q = (
                    "CREATE TEMPORARY TABLE product_quantity_tmp ON COMMIT DROP AS "
                    "SELECT id, name, description, price, 0 AS quantity "
                    "FROM product WHERE available"
                )
                await conn.execute(q)

                # update all products quantity with order products
                q = (
                    "UPDATE product_quantity_tmp AS pqt SET quantity = op.quantity "
                    "FROM ("
                    "    SELECT p.id, p.name, p.description, p.price, opa.quantity "
                    "    FROM order_product_association AS opa "
                    "    INNER JOIN product AS p ON opa.product_id = p.id "
                    "    WHERE opa.order_id = $1"
                    ") AS op "
                    "WHERE pqt.id = op.id"
                )
                await conn.execute(q, order_id)

                q = "SELECT * FROM product_quantity_tmp ORDER BY name"
                rows = await conn.fetch(q)
                products = [dict(p) for p in rows]

            return {"id": str(order_id), "form": form, "products": products}
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

                # check that the order belongs to the right client
                q = (
                    "DELETE FROM order_ "
                    "WHERE id = $1 AND client_id = $2 AND payment_id IS NULL "
                    "RETURNING id"
                )
                deleted = await conn.fetchval(q, order_id, client_id)
                if not deleted:
                    raise RollbackTransactionException()

                flash(request, ("success", "Votre commande a bien été supprimée."))
        except RollbackTransactionException:
            flash(request, ("warning", "Votre commande ne peut pas être supprimée."))
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
