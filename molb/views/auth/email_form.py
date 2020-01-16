from wtforms import StringField
from wtforms import SubmitField
from wtforms.validators import Email
from wtforms.validators import Length
from wtforms.validators import Required

from molb.views.csrf_form import CsrfForm
from molb.views.utils import _l


class EmailForm(CsrfForm):
    email_address = StringField(_l("Adresse email"), validators=[
        Required(),
        Length(min=5, max=64),
        Email()
    ])
    submit = SubmitField(_l("Valider"))
