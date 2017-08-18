from wtforms import Form
from wtforms.csrf.session import SessionCSRF
from datetime import timedelta

class CsrfForm(Form):
    class Meta:
        csrf = True
        csrf_class = SessionCSRF
        csrf_time_limit = timedelta(minutes=10)
