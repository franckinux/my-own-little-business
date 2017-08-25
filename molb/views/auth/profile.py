from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
import aiohttp_jinja2
from aiohttp_security import authorized_userid
from aiohttp_security import forget
from aiohttp_session_flash import flash
from asyncpg.exceptions import UniqueViolationError
from passlib.hash import sha256_crypt
from wtforms import PasswordField
from wtforms import SelectField
from wtforms import StringField
from wtforms import SubmitField
from wtforms.validators import EqualTo
from wtforms.validators import Regexp

from molb.auth import require
from molb.views.csrf_form import CsrfForm
from molb.views.utils import generate_csrf_meta
from molb.views.utils import remove_special_data
from molb.views.utils import settings


class ProfileForm(CsrfForm):
    password = PasswordField("Mot de passe", validators=[
        EqualTo("password2", message="Les mots de passe doivent être identiques"),
    ])
    password2 = PasswordField("Répétition du mot de passe")
    first_name = StringField("Prénom")
    last_name = StringField("Nom")
    phone_number = StringField("Numéro de téléphone", validators=[
        Regexp("^(0|\+33)[1-9]([-. ]?[0-9]{2}){4}$", 0)
    ])
    repository_id = SelectField("Point de livraison", coerce=int)
    submit = SubmitField("Soumettre")


@require("client")
@aiohttp_jinja2.template("auth/profile.html")
async def edit_profile(request):
    async with request.app["db-pool"].acquire() as conn:
        rows = await conn.fetch("SELECT id, name FROM repository WHERE opened")
        repository_choices = [(row["id"], row["name"]) for row in rows]

        login = await authorized_userid(request)
        data = dict(await conn.fetchrow("SELECT * FROM client WHERE login = $1", login))
        del data["password_hash"]
        if request.method == "POST":
            form = ProfileForm(
                await request.post(),
                data=data,
                meta=await generate_csrf_meta(request)
            )
            form.repository_id.choices = repository_choices
            if form.validate():
                data = remove_special_data(form.data.items())
                del data["password2"]
                password = data.pop("password")
                if password:
                    if len(password) < 6:
                        flash(request, ("warning", "Le mot de passe est trop court"))
                        return {"form": form}
                    data["password_hash"] = sha256_crypt.hash(password)
                q = "UPDATE client SET {} WHERE login = ${}".format(
                    settings(data), len(data) + 1
                )
                try:
                    await conn.execute(q, *data.values(), login)
                except UniqueViolationError:
                    flash(request, ("warning", "Votre profil ne peut être modifié"))
                else:
                    flash(request, ("success", "Votre profil a bien été modifié"))
                    return HTTPFound(request.app.router["home"].url_for())
            else:
                flash(request, ("danger", "Le formulaire comporte des erreurs"))
            return {"form": form}
        elif request.method == "GET":
            form = ProfileForm(data=data, meta=await generate_csrf_meta(request))
            form.repository_id.choices = repository_choices
            return {"form": form}
        else:
            raise HTTPMethodNotAllowed()


@require("client")
async def delete_profile(request):
    login = await authorized_userid(request)

    async with request.app["db-pool"].acquire() as conn:
        client = await conn.fetchrow(
            "SELECT id, super_user FROM client WHERE login = $1", login
        )
        client_id = client["id"]

        if client["super_user"]:
            flash(
                request,
                (
                    "warning",
                    "Un administrateur ne peut pas supprimer son profil."
                )
            )
            return HTTPFound(request.app.router["home"].url_for())

        # check if there are unpayed orders from the client
        q = (
            "SELECT COUNT(*) "
            "FROM order_ AS o "
            "INNER JOIN client AS c ON o.client_id = c.id "
            "LEFT JOIN payment AS p ON o.payment_id = p.id "
            "WHERE (o.payment_id IS NULL OR p.mode = 'not_payed') AND c.id = $1"
        )
        payment_count = await conn.fetchval(q, client_id)
        if payment_count != 0:
            flash(
                request,
                (
                    "warning",
                    (
                        "Vous ne pouvez pas supprimer vote profil : "
                        "vous avez des commandes non payées."
                    )
                )
            )
            return HTTPFound(request.app.router["home"].url_for())

        try:
            async with conn.transaction():
                # delete associations between orders and products
                q = "SELECT id FROM order_ WHERE client_id = $1"
                orders = await conn.fetch(q, client_id)
                order_ids = [order["id"] for order in orders]

                q = "DELETE FROM order_product_association WHERE order_id = any($1::int[])"
                await conn.execute(q, order_ids)

                # fetch payment ids
                q = (
                    "SELECT DISTINCT payment_id FROM order_ "
                    "WHERE payment_id IS NOT NULL AND client_id = $1"
                )
                payments = await conn.fetch(q, client_id)
                payment_ids = [payment["payment_id"] for payment in payments]

                # delete orders
                q = "DELETE FROM order_ WHERE client_id = $1"
                await conn.execute(q, client_id)

                # delete payments
                q = "DELETE FROM payment WHERE id = any($1::int[])"
                await conn.execute(q, payment_ids)

                # delete client
                q = "DELETE FROM client WHERE id = $1"
                await conn.execute(q, client_id)
        except:
            flash( request, ("warning", ("Votre profil ne peut être détruit")))
        else:
            response = HTTPFound(request.app.router["login"].url_for())
            await forget(request, response)
            flash( request, ("success", ("Votre profil a été détruit")))
            return response

        return HTTPFound(request.app.router["home"].url_for())
