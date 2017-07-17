from aiohttp_jinja2 import get_env
from aiosmtplib import SMTP
from email.message import Message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer


def get_id_from_token(token, secret_key):
    s = Serializer(secret_key)
    data = s.loads(token)
    return data["confirm"]


def generate_confirmation_token(id_, secret_key, expiration=3600):
    s = Serializer(secret_key, expiration)
    return s.dumps({"confirm": id_}).decode("ascii")


async def send_confirmation_email(app, client):
    config = app["config"]["application"]

    token = generate_confirmation_token(client.id, config["secret_key"])
    url = "{}/confirm/{}/".format(config["url"], token)

    env = get_env(app)
    template = env.get_template("auth/confirmation-message.txt")
    text_part = template.render(url=url)
    text_message = MIMEText(text_part, "plain")
    template = env.get_template("auth/confirmation-message.html")
    html_part = template.render(url=url)
    html_message = MIMEText(html_part, "html")

    message = MIMEMultipart("alternative")
    message["subject"] = "Confirm your account"
    message["to"] = client.email_address
    message["from"] = config["from"]
    message.attach(text_message)
    message.attach(html_message)

    # https://stackoverflow.com/questions/10147455/how-to-send-an-email-with-gmail-as-provider-using-python
    smtp = SMTP(hostname=config["smtp_url"], port=config["smtp_port"], use_tls=False)
    await smtp.connect()
    await smtp.ehlo()
    await smtp.starttls()
    await smtp.login(config["smtp_username"], config["smtp_password"])
    await smtp.send_message(message)
    smtp.close()
