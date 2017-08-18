from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
import aiohttp_jinja2
from aiohttp_security import authorized_userid
from aiohttp_session_flash import flash
from asyncpg.exceptions import UniqueViolationError
from passlib.hash import sha256_crypt
from wtforms import PasswordField
from wtforms import SelectField
from wtforms import StringField
from wtforms import SubmitField
from wtforms.validators import EqualTo
from wtforms.validators import Regexp

from auth import require
from views.csrf_form import CsrfForm
from views.utils import generate_csrf_meta
from views.utils import remove_special_data
from views.utils import settings


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
async def profile(request):
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
