from datetime import timedelta

from wtforms import Form
from wtforms.csrf.session import SessionCSRF


class CsrfForm(Form):
    class Meta:
        csrf = True
        csrf_class = SessionCSRF
        csrf_time_limit = timedelta(minutes=10)
        locales = ["fr", "en"]
