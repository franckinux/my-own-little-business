from decimal import Decimal
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
from aiohttp_jinja2 import get_env
import aiohttp_jinja2
from aiohttp_security import authorized_userid
from aiohttp_session_flash import flash
from wtforms import DateTimeField
from wtforms import DecimalField
from wtforms import SelectField
from wtforms import StringField
from wtforms import SubmitField
from wtforms.validators import Required

from molb.auth import require
from molb.views.csrf_form import CsrfForm
from molb.views.utils import generate_csrf_meta
from molb.views.utils import remove_special_data


class InvoiceForm(CsrfForm):
    date = DateTimeField("Date", validators=[Required()])
    submit = SubmitField("Valider")


@require("admin")
@aiohttp_jinja2.template("invoice.html")
async def invoice(request):
    if request.method == "POST":
        form = InvoiceForm(await request.post(), meta=await generate_csrf_meta(request))

        # just for csrf !
        if not form.validate():
            flash(request, ("danger", "Le formulaire comporte des erreurs."))
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
                        "La date doit être postérieure au dernier appel de fonds."
                    )
                )
                return {"form": form}

            # look for clients' orders that are anterior to the invoice date
            q = (
                "SELECT DISTINCT c.id "
                "FROM order_ AS o "
                "INNER JOIN client AS c ON o.client_id = c.id "
                "WHERE o.date <= $1 AND o.payment_id IS NULL AND NOT o.disabled"
            )
            clients = await conn.fetch(q, invoice_date)

            # update billing informations
            for client in clients:
                client_id = client["id"]

                # use the wallet to pay client orders
                await pay_client_orders(request, conn, client_id, invoice_date)

                # compute total amount of client orders
                q = (
                    "SELECT SUM(o.total) AS total "
                    "FROM order_ AS o "
                    "WHERE o.date <= $1 AND o.client_id = $2 AND "
                    "      o.payment_id IS NULL AND NOT o.disabled"
                )
                total = await conn.fetchval(q, invoice_date, client_id)

                # retrieve all client's orders
                q = (
                    "SELECT o.date AS order_date, o.total AS order_total, "
                    "       p.name AS product_name, opa.quantity "
                    "FROM order_product_association AS opa "
                    "INNER JOIN product AS p ON opa.product_id = p.id "
                    "INNER JOIN order_ AS o ON opa.order_id = o.id "
                    "WHERE o.date <= $1 AND o.client_id = $2 AND "
                    "      o.payment_id IS NULL AND NOT o.disabled "
                    "ORDER BY o.date, p.name"
                )
                payment_details = await conn.fetch(q, invoice_date, client_id)

                q = "SELECT CAST(id AS TEXT), first_name, email_address, wallet FROM client WHERE id = $1"
                client = await conn.fetchrow(q, client_id)

                await send_invoice(
                    request, client, total, payment_details, invoice_date
                )

            # update last invoice date
            q = "UPDATE storage SET last_invoice_date = $1"
            await conn.execute(q, invoice_date)

        return {"form": form}

    elif request.method == "GET":
        form = InvoiceForm(meta=await generate_csrf_meta(request))
        return {"form": form}
    else:
        raise HTTPMethodNotAllowed()


async def send_invoice(request, client, total, payment_details, invoice_date):
    config = request.app["config"]

    env = get_env(request.app)
    template = env.get_template("invoice-details.txt")
    text_part = template.render(
        total=total, client=client,
        payment_details=payment_details, invoice_date=invoice_date
    )
    text_message = MIMEText(text_part, "plain")
    template = env.get_template("invoice-details.html")
    html_part = template.render(
        total=total, client=client,
        payment_details=payment_details, invoice_date=invoice_date
    )
    html_message = MIMEText(html_part, "html")

    message = MIMEMultipart("alternative")
    message["subject"] = "[{}] Votre appel de fonds du {}".format(
        config["application"]["site_name"], invoice_date.strftime("%d-%m-%Y")
    )
    message["to"] = client["email_address"]
    message["from"] = config["application"]["from"]
    message.attach(text_message)
    message.attach(html_message)
    await request.app["mailer"].send_message(message)


@require("client")
@aiohttp_jinja2.template("list-payment.html")
async def list_payment(request):
    login = await authorized_userid(request)

    async with request.app["db-pool"].acquire() as conn:
        client = await conn.fetchrow(
            "SELECT id, wallet FROM client WHERE login = $1", login
        )
        client_id = client["id"]

        q = (
            "SELECT amount, date, mode, reference "
            "FROM payment "
            "WHERE client_id = $1 "
            "ORDER BY date desc "
            "LIMIT 15"
        )
        payments = await conn.fetch(q, client_id)

    return {"payments": payments, "wallet": client["wallet"]}


class PaymentForm(CsrfForm):
    amount = DecimalField("Montant", validators=[Required()])
    mode = SelectField("Mode de paiement")
    reference = StringField("Référence")
    submit = SubmitField("Valider")


async def pay_client_orders(request, conn, client_id, last_invoice_date):
    # get the client's non payed orders in chronological order
    # not older than the last invoice date
    q = (
        "SELECT id, total "
        "FROM order_ "
        "WHERE client_id = $1 AND payment_id IS NULL AND NOT disabled AND date <= $2 "
        "ORDER BY date"
    )
    orders = await conn.fetch(q, client_id, last_invoice_date)

    one_payed = False
    for order in orders:
        total = order["total"]
        order_id = order["id"]

        # get client's wallet
        q = (
            "SELECT wallet FROM client WHERE id = $1"
        )
        wallet = await conn.fetchval(q, client_id)

        async with conn.transaction():
            try:
                if total <= wallet:
                    # create the payment
                    q = (
                        "INSERT INTO payment "
                        "   (amount, mode, reference, client_id) "
                        "VALUES ($1, $2, $3, $4) "
                        "RETURNING id"
                    )
                    payment_id = await conn.fetchval(
                        q,
                        -total, "order", str(order_id), client_id
                    )

                    # update the client's wallet
                    q = "UPDATE client SET wallet = wallet - $1 WHERE id = $2"
                    await conn.execute(q, total, client_id)

                    # update the order
                    q = "UPDATE order_ SET payment_id = $1 " "WHERE id = $2"
                    await conn.execute(q, payment_id, order_id)

                    one_payed = True
            except:
                return -1

    if one_payed:
        return 1
    else:
        return 0


@require("admin")
@aiohttp_jinja2.template("create-payment.html")
async def create_payment(request):
    client_id = int(request.match_info["id"])

    payment_choices = [
        ("payed_by_paypal", "Par Paypal"),
        ("payed_by_check", "Par chèque"),
        ("payed_in_cash", "En espèces"),
    ]

    if request.method == "POST":
        form = PaymentForm(await request.post(), meta=await generate_csrf_meta(request))
        form.mode.choices = payment_choices

        if form.validate():
            data = remove_special_data(await request.post())
            amount = Decimal(data["amount"])
            if amount > 0:
                operation = "crédité"
            else:
                operation = "débité"

            async with request.app["db-pool"].acquire() as conn:
                async with conn.transaction():
                    try:
                        # create the payment
                        q = (
                            "INSERT INTO payment (amount, mode, reference, client_id) "
                            "VALUES ($1, $2, $3, $4)"
                        )
                        await conn.execute(
                            q, amount, data["mode"], data["reference"], client_id
                        )

                        # update the client's wallet
                        q = (
                            "UPDATE client SET wallet = wallet + $1 WHERE id = $2"
                        )
                        await conn.execute(q, amount, client_id)

                        flash(
                            request,
                            (
                                "success",
                                "Le porte-monnaie a été {}.".format(operation)
                            )
                        )
                    except:
                        flash(
                              request,
                              (
                                  "danger",
                                  "Le porte-monnaie n'a pas été {}.".format(operation)
                              )
                        )
                        return {"form": form, "client_id": str(client_id)}

                # get last invoice date
                q = "SELECT last_invoice_date FROM storage"
                last_invoice_date = await conn.fetchval(q)

                ret = await pay_client_orders(request, conn, client_id, last_invoice_date)
                if ret == -1:
                    flash(request, ("danger", "Des commandes n'ont pu être payées."))
                elif ret == 0:
                    flash(request, ("info", "Aucune commande n'a été payée."))
                elif ret == 1:
                    flash(request, ("success", "Au moins une commande a été payée."))
                return HTTPFound(request.app.router["list_client"].url_for())
        else:
            flash(request, ("danger", "Le formulaire comporte des erreurs."))
            return {"form": form, "client_id": str(client_id)}
    elif request.method == "GET":
        form = PaymentForm(meta=await generate_csrf_meta(request))
        form.mode.choices = payment_choices
        return {"form": form, "client_id": str(client_id)}
    else:
        raise HTTPMethodNotAllowed()
