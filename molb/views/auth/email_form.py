from wtforms import StringField
from wtforms import SubmitField
from wtforms.validators import Email
from wtforms.validators import Length
from wtforms.validators import Required

from molb.main import _
from molb.views.csrf_form import CsrfForm


class EmailForm(CsrfForm):
    email_address = StringField(_("Adresse email"), validators=[
        Required(),
        Length(min=5, max=64),
        Email()
    ])
    submit = SubmitField(_("Valider"))
