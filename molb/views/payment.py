from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
from aiohttp_jinja2 import get_env
import aiohttp_jinja2
from aiohttp_security import authorized_userid
from aiohttp_session_flash import flash
from wtforms import DateTimeField
from wtforms import IntegerField
from wtforms import SelectField
from wtforms import StringField
from wtforms import SubmitField
from wtforms.validators import Required

from auth import require
from .csrf_form import CsrfForm
from views.auth.send_message import send_message
from views.utils import generate_csrf_meta
from views.utils import remove_special_data


class InvoiceForm(CsrfForm):
    date = DateTimeField("Date", validators=[Required()])
    submit = SubmitField("Soumettre")


@require("admin")
@aiohttp_jinja2.template("invoice.html")
async def invoice(request):
    if request.method == "POST":
        form = InvoiceForm(await request.post(), meta=await generate_csrf_meta(request))

        # just for csrf !
        if not form.validate():
            flash(request, ("danger", "Ce formulaire comporte des erreurs."))
            return {"form": form}

        invoice_date = form.date.data

        async with request.app["db-pool"].acquire() as conn:
            # get last invoice date
            q = "SELECT last_invoice_date FROM storage"
            last_invoice_date = await conn.fetchval(q)

            if last_invoice_date >= invoice_date:
                flash(
                    request,
                    (
                        "danger",
                        "La date doit être postérieure à celle de la dernière facturation."
                    )
                )
                return {"form": form}

            # look for clients whose order batch is between that period
            q = (
                "SELECT DISTINCT c.id "
                "FROM order_ AS o "
                "INNER JOIN client AS c ON o.client_id = c.id "
                "INNER JOIN batch AS b ON o.batch_id = b.id "
                "WHERE b.date BETWEEN $1 AND $2 AND o.payment_id IS NULL"
            )
            clients = await conn.fetch(q, last_invoice_date, invoice_date)

            try:
                async with conn.transaction():
                    client_data = {}

                    # update billing informations
                    for client in clients:
                        client_id = client["id"]

                        # compute total amount of client orders
                        q = (
                            "SELECT SUM(o.total) AS total "
                            "FROM order_ AS o "
                            "INNER JOIN batch AS b ON o.batch_id = b.id "
                            "WHERE b.date BETWEEN $1 AND $2 AND "
                            "      o.client_id = $3 AND o.payment_id IS NULL"
                        )
                        total = await conn.fetchval(
                            q, last_invoice_date, invoice_date, client_id
                        )

                        # create payment
                        q = (
                            "INSERT INTO payment (total) VALUES ($1) RETURNING id"
                        )
                        payment_id = await conn.fetchval(q, total)

                        # update payment for all client orders
                        q = (
                            "UPDATE order_ AS o "
                            "SET payment_id = $1 "
                            "FROM batch AS b "
                            "WHERE o.batch_id = b.id AND "
                            "      b.date BETWEEN $2 AND $3 AND "
                            "      o.client_id = $4 AND o.payment_id IS NULL"
                        )
                        await conn.execute(
                            q, payment_id, last_invoice_date, invoice_date, client_id
                        )

                        client_data[client_id] = payment_id

                    # update last invoice date
                    q = "UPDATE storage SET last_invoice_date = $1"
                    await conn.execute(q, invoice_date)
            except:
                flash(
                    request,
                    (
                        "warning",
                        (
                            "Un problème s'est produit pendant la mise à jour "
                            "des informations de facturation."
                        )
                    )
                )
                return {"form": form}

            # send invoices to clients
            for client_id, payment_id in client_data.items():
                q = "SELECT total FROM payment WHERE id = $1"
                total = await conn.fetchval(q, payment_id)

                # retrieve all orders of the client
                q = (
                    "SELECT b.date AS batch_date, o.total AS order_total, "
                    "       p.name AS product_name, opa.quantity "
                    "FROM order_product_association AS opa "
                    "INNER JOIN product AS p ON opa.product_id = p.id "
                    "INNER JOIN order_ AS o ON opa.order_id = o.id "
                    "INNER JOIN batch AS b ON o.batch_id = b.id "
                    "WHERE o.payment_id = $1 "
                    "ORDER BY o.id, p.id"
                )
                payment_details = await conn.fetch(q, payment_id)

                q = "SELECT first_name, email_address FROM client WHERE id = $1"
                client = await conn.fetchrow(q, client_id)

                await send_invoice(
                    request, client, total, payment_id, payment_details,
                    invoice_date
                )
        return {"form": form}

    elif request.method == "GET":
        form = InvoiceForm(meta=await generate_csrf_meta(request))
        return {"form": form}
    else:
        raise HTTPMethodNotAllowed()


async def send_invoice(request, client, total, payment_id, payment_details,
                       invoice_date):
    config = request.app["config"]

    env = get_env(request.app)
    template = env.get_template("invoice-details.txt")
    text_part = template.render(
        payment_id=payment_id, total=total, first_name=client["first_name"],
        payment_details=payment_details, invoice_date=invoice_date
    )
    text_message = MIMEText(text_part, "plain")
    template = env.get_template("invoice-details.html")
    html_part = template.render(
        payment_id=payment_id, total=total, first_name=client["first_name"],
        payment_details=payment_details, invoice_date=invoice_date
    )
    html_message = MIMEText(html_part, "html")

    message = MIMEMultipart("alternative")
    message["subject"] = "[{}] Votre facture du {}".format(
        config["application"]["site_name"], invoice_date.strftime("%d-%m-%Y")
    )
    message["to"] = client["email_address"]
    message["from"] = config["application"]["from"]
    message.attach(text_message)
    message.attach(html_message)
    await send_message(message, config["smtp"])


class PaymentIdForm(CsrfForm):
    payment_id = IntegerField("Numéro de facture", validators=[Required()])
    submit = SubmitField("Valider")


@require("admin")
@aiohttp_jinja2.template("list-payment.html")
async def list_payment(request):
    if request.method == "POST":
        form = PaymentIdForm(await request.post(), meta=await generate_csrf_meta(request))

        if form.validate():
            data = remove_special_data(await request.post())
            payment_id = int(data["payment_id"])

            async with request.app["db-pool"].acquire() as conn:
                q = (
                    "SELECT DISTINCT c.id, c.first_name, c.last_name, c.email_address, "
                    "       c.phone_number, p.id, p.claimed_at, p.total "
                    "FROM order_ AS o "
                    "INNER JOIN client AS c ON o.client_id = c.id "
                    "LEFT JOIN payment AS p ON o.payment_id = p.id "
                    "WHERE o.payment_id IS NOT NULL AND p.mode = 'not_payed' AND p.id = $1"
                )
                payments = await conn.fetch(q, payment_id)

                if not payments:
                    flash(request, ("warning", "Ce numéro de facture est invalide."))

            return {"form": form, "payments": payments}
        else:
            flash(request, ("danger", "Ce formulaire comporte des erreurs."))
            return {"form": form}

    elif request.method == "GET":
        form = PaymentIdForm(meta=await generate_csrf_meta(request))

        # get information on clients that have unpayed orders
        async with request.app["db-pool"].acquire() as conn:
            q = (
                "SELECT DISTINCT c.id, c.first_name, c.last_name, c.email_address, "
                "       c.phone_number, p.id, p.claimed_at, p.total "
                "FROM order_ AS o "
                "INNER JOIN client AS c ON o.client_id = c.id "
                "LEFT JOIN payment AS p ON o.payment_id = p.id "
                "WHERE o.payment_id IS NOT NULL AND p.mode = 'not_payed' "
                "ORDER BY p.claimed_at DESC, p.id, c.last_name, c.first_name"
            )
            payments = await conn.fetch(q)

        return {"form": form, "payments": payments}
    else:
        raise HTTPMethodNotAllowed()


class PaymentForm(CsrfForm):
    mode = SelectField("Mode de paiement")
    reference = StringField("Référence")
    submit = SubmitField("Valider")


@require("admin")
@aiohttp_jinja2.template("edit-payment.html")
async def edit_payment(request):
    payment_id = int(request.match_info["id"])

    payment_choices = [
        ("payed_by_check", "Par chèque"),
        ("payed_in_cash", "En espèces"),
    ]

    if request.method == "POST":
        form = PaymentForm(await request.post(), meta=await generate_csrf_meta(request))
        form.mode.choices = payment_choices

        if form.validate():
            data = remove_special_data(await request.post())
            mode = data["mode"]
            reference = data["reference"]

            # update payment mode and reference
            async with request.app["db-pool"].acquire() as conn:
                await conn.execute(
                    "UPDATE payment SET mode = $1, reference = $2, payed_at = NOW() "
                    "WHERE id = $3",
                    mode, reference, payment_id
                )
            return HTTPFound(request.app.router["list_payment"].url_for())
        else:
            flash(request, ("danger", "Ce formulaire comporte des erreurs."))
            return {"form": form, "id": payment_id}
    elif request.method == "GET":
        form = PaymentForm(meta=await generate_csrf_meta(request))
        form.mode.choices = payment_choices
        return {"form": form, "id": payment_id}
    else:
        raise HTTPMethodNotAllowed()


@require("client")
@aiohttp_jinja2.template("show-payment.html")
async def show_payment(request):
    payment_id = int(request.match_info["id"])
    login = await authorized_userid(request)

    async with request.app["db-pool"].acquire() as conn:
        q = (
            "SELECT DISTINCT p.id, p.total, p.mode, p.reference, p.payed_at "
            "FROM order_ AS o "
            "INNER JOIN client AS c ON o.client_id = c.id "
            "LEFT JOIN payment AS p ON o.payment_id = p.id "
            "WHERE o.payment_id = $1 AND c.login = $2"
        )
        payment = await conn.fetchrow(q, payment_id, login)
        if not payment:
            flash(request, ("warning", "Votre requête ne peut être satisfaite."))
            return HTTPFound(request.app.router["list_order"].url_for())

        # retrieve all orders of the client
        q = (
            "SELECT b.date AS batch_date, o.total AS order_total, "
            "       p.name AS product_name, opa.quantity "
            "FROM order_product_association AS opa "
            "INNER JOIN product AS p ON opa.product_id = p.id "
            "INNER JOIN order_ AS o ON opa.order_id = o.id "
            "INNER JOIN batch AS b ON o.batch_id = b.id "
            "WHERE o.payment_id = $1 "
            "ORDER BY o.id, p.id"
        )
        payment_details = await conn.fetch(q, payment_id)

    return {"payment": payment, "payment_details": payment_details}
