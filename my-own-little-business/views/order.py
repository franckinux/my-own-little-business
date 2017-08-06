from datetime import datetime
from datetime import timedelta

from aiohttp_security import authorized_userid
from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
import aiohttp_jinja2
from aiohttp_session_flash import flash
from wtforms import SelectField
from wtforms import SubmitField

from auth import require
from .csrf_form import CsrfForm
from views.utils import generate_csrf_meta
from views.utils import remove_special_data


class RollbackTransactionException(Exception):
    pass


class OrderForm(CsrfForm):
    batch_id = SelectField("Fournée", coerce=int)
    submit = SubmitField("Valider")


@require("client")
@aiohttp_jinja2.template("create-order.html")
async def create_order(request):
    login = await authorized_userid(request)

    async with request.app["db-pool"].acquire() as conn:
        client_id = await conn.fetchval(
            "SELECT id FROM client WHERE login = $1", login
        )

        # select opened batches whose date is 12 hours in the future and
        # load is inferior to its capacity
        # select opened batches whose date is 12 hours in the future and
        # that have no order on it
        q = (
            "SELECT batch_id, batch_date FROM ("
            "    SELECT o.batch_id, SUM(opa.quantity * p.load) AS batch_load, "
            "           b.capacity, b.date AS batch_date "
            "    FROM order_product_association AS opa "
            "    INNER JOIN product AS p ON opa.product_id = p.id "
            "    INNER JOIN order_ AS o ON opa.order_id = o.id "
            "    INNER JOIN batch AS b ON o.batch_id = b.id "
            "    WHERE b.opened "
            "    GROUP BY o.batch_id, b.capacity, b.date"
            "    UNION "
            "    SELECT b.id AS batch_id, 0 as batch_load, b.capacity, "
            "           b.date AS batch_date "
            "    FROM batch AS b "
            "    LEFT JOIN order_ AS o ON o.batch_id = b.id "
            "    WHERE b.opened AND o.batch_id IS NULL"
            ") AS sq  "
            "WHERE batch_load < capacity AND batch_date > (NOW() + INTERVAL '12 hour') "
            "ORDER BY batch_date"
        )
        rows = await conn.fetch(q)
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
            batch_id = int(data["batch_id"])

            for product in products:
                product_id = product["id"]
                quantity = data["product_qty_{}".format(product_id)]
                product["quantity"] = quantity

            # just for csrf !
            if not form.validate():
                flash(request, ("danger", "Ce formulaire comporte des erreurs."))
                return {"form": form, "products": products}

            q = "SELECT COUNT(*) FROM order_ WHERE client_id = $1 AND batch_id = $2"
            ret = await conn.fetchval(q, client_id, batch_id)
            if ret:
                flash(
                    request,
                    (
                        "warning",
                        "Vous avez déjà passé une commande sur cette même fournée, "
                        "veuillez modifier cette dernière."
                    )
                )
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
                        return {"form": form, "products": products}
                quantities[product_id] = qti

            if sum(quantities.values()) == 0:
                flash(request, ("warning", "Veuillez choisir au moins un produit"))
                return {"form": form, "products": products}

            try:
                async with conn.transaction():
                    # lock the batch record in the transaction
                    q = (
                        "SELECT capacity FROM batch WHERE id = $1 FOR UPDATE"
                    )
                    batch_capacity = await conn.fetchval(q, batch_id)

                    # create an order, total is set to 0
                    q = (
                        "INSERT INTO order_ (total, client_id, batch_id) "
                        "VALUES ($1, $2, $3) RETURNING id"
                    )
                    order_id = await conn.fetchval(q, 0, client_id, batch_id)

                    # create order to products
                    for product_id, quantity in quantities.items():
                        if quantity != 0:
                            q = (
                                "INSERT INTO order_product_association ("
                                "   quantity, order_id, product_id"
                                ") "
                                "VALUES ($1, $2, $3)"
                            )
                            await conn.execute(q, quantity, order_id, product_id)

                    # compute batch load
                    q = (
                        "SELECT SUM(opa.quantity * p.load) AS load "
                        "FROM order_product_association AS opa "
                        "INNER JOIN product AS p ON opa.product_id = p.id "
                        "INNER JOIN order_ AS o ON opa.order_id = o.id "
                        "WHERE o.batch_id = $1"
                    )
                    batch_load = await conn.fetchval(q, batch_id)

                    # check that the batch is not overloaded
                    if batch_load > batch_capacity:
                        # if so, roll back the changes
                        raise RollbackTransactionException()

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
                return {"form": form, "products": products}

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
            await conn.execute(q, order_id)

            flash(request, ("success", "Votre commande a été passée avec succès"))
            return HTTPFound(request.app.router["list_order"].url_for())
        elif request.method == "GET":
            form = OrderForm(meta=await generate_csrf_meta(request))
            form.batch_id.choices = batch_choices
            return {"form": form, "products": products}
        else:
            raise HTTPMethodNotAllowed()


@require("client")
@aiohttp_jinja2.template("edit-order.html")
async def edit_order(request):
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
            flash( request, ("warning", ("Il est trop tard pour modifier votre commande.")))
            return HTTPFound(request.app.router["list_order"].url_for())

        q = "SELECT batch_id FROM order_ WHERE id = $1"
        batch_id = await conn.fetchval(q, order_id)

        # select opened batches whose date is 12 hours in the future and
        # load is inferior to its capacity
        # select opened batches whose date is 12 hours in the future and
        # that have no order on it
        # select the batch id of the order
        q = (
            "SELECT batch_id, batch_date FROM ("
            "    SELECT o.batch_id, SUM(opa.quantity * p.load) AS batch_load, "
            "           b.capacity, b.date AS batch_date "
            "    FROM order_product_association AS opa "
            "    INNER JOIN product AS p ON opa.product_id = p.id "
            "    INNER JOIN order_ AS o ON opa.order_id = o.id "
            "    INNER JOIN batch AS b ON o.batch_id = b.id "
            "    WHERE b.opened AND b.id != $1"
            "    GROUP BY o.batch_id, b.capacity, b.date"
            "    UNION "
            "    SELECT b.id AS batch_id, 0 as batch_load, b.capacity, "
            "           b.date AS batch_date "
            "FROM batch AS b "
            "    LEFT JOIN order_ AS o ON o.batch_id = b.id "
            "    WHERE b.opened AND (o.batch_id IS NULL OR b.id = $1)"
            ") AS sq "
            "WHERE batch_load < capacity AND batch_date > (NOW() + INTERVAL '12 hour') "
            "ORDER BY batch_date"
        )
        rows = await conn.fetch(q, batch_id)
        batch_choices = [(row["batch_id"], row["batch_date"]) for row in rows]

        # select all available products
        rows = await conn.fetch(
            "SELECT id, name, description, price, load FROM product WHERE available"
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
                flash(request, ("danger", "Ce formulaire comporte des erreurs."))
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
                    q = (
                        "SELECT capacity FROM batch WHERE id = $1 FOR UPDATE"
                    )
                    batch_capacity = await conn.fetchval(q, new_batch_id)

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

                    # compute batch load
                    q = (
                        "SELECT SUM(opa.quantity * p.load) AS load "
                        "FROM order_product_association AS opa "
                        "INNER JOIN product AS p ON opa.product_id = p.id "
                        "INNER JOIN order_ AS o ON opa.order_id = o.id "
                        "WHERE o.batch_id = $1"
                    )
                    batch_load = await conn.fetchval(q, new_batch_id)

                    # check that the batch is not overloaded
                    if batch_load > batch_capacity:
                        # if so, roll back the changes
                        raise RollbackTransactionException()

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

            flash(request, ("success", ("Votre commande a bien été modifiée.")))
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

            return {"id": order_id, "form": form, "products": products}
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
            flash( request, ("warning", ("Il est trop tard pour annuler votre commande.")))
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

                flash( request, ("success", ("Votre commande a bien été supprimée.")))
        except RollbackTransactionException:
            flash( request, ("warning", ("Votre commande ne peut pas être supprimée.")))
    return HTTPFound(request.app.router["list_order"].url_for())


def translate_mode(value):
    if value is None:
        return "Non payée"
    elif value == "not_payed":
        return "Non payée"
    elif value == "payed_by_check":
        return "Payée par chèque"
    elif value == "payed_inline":
        return "Payée en ligne"


@require("client")
@aiohttp_jinja2.template("list-order.html")
async def list_order(request):
    login = await authorized_userid(request)

    async with request.app["db-pool"].acquire() as conn:
        client_id = await conn.fetchval(
            "SELECT id FROM client WHERE login = $1", login
        )

        q = (
            "SELECT o.id, o.placed_at, o.total, p.mode AS payment_mode, "
            "       b.date AS batch_date, b.date - INTERVAL '12 hour' AS cancellation_date "
            "FROM order_ AS o "
            "INNER JOIN batch AS b ON o.batch_id = b.id "
            "LEFT JOIN payment AS p ON o.payment_id = p.id "
            "WHERE o.client_id = $1 ORDER BY o.placed_at DESC"
        )
        orders = await conn.fetch(q, client_id)
    return {"orders": orders, "now": datetime.now()}
